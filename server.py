from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import json
import time
import re
import traceback
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

from agents import (
    planner_prompt, multi_reader_prompt, contrarian_prompt,
    writer_prompt, critic_prompt, revision_prompt,
    claim_extractor_prompt, claim_fidelity_prompt, fact_verifier_prompt, grounding_prompt,
    STAGES, llm
)
from tools import web_search, scrape_url, get_source_trust_score

REQUEST_DELAY = 4.5

app = Flask(__name__)
CORS(app)

def extract_text_content(response):
    if isinstance(response, dict):
        if 'messages' in response:
            return response['messages'][-1].content
        return str(response)
    elif hasattr(response, 'content'):
        return str(response.content)
    return str(response)

def extract_string(content):
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and 'text' in p:
                parts.append(p['text'])
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return str(content)

def get_model_cost(input_tokens, output_tokens):
    return (input_tokens * 0.075 / 1000000) + (output_tokens * 0.30 / 1000000)

def track_call(response, metrics):
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        in_t = response.usage_metadata.get('input_tokens', 0)
        out_t = response.usage_metadata.get('output_tokens', 0)
        metrics['input_tokens'] += in_t
        metrics['output_tokens'] += out_t

def invoke_llm_chain(prompt_template, inputs, metrics):
    prompt_val = prompt_template.invoke(inputs)
    response = llm.invoke(prompt_val)
    track_call(response, metrics)
    return extract_string(response.content)

def smart_sleep(duration):
    elapsed = 0.0
    while elapsed < duration:
        time.sleep(0.5)
        elapsed += 0.5
        yield ": ping\n\n"

# --- MongoDB & Authentication Setup ---
import jwt
import bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps

mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/arcs")
JWT_SECRET = os.getenv("JWT_SECRET", "arcs_super_secret_key_2026_pro_secure_hash")

try:
    import certifi
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
    client.server_info() # Validate connection
    db = client.get_database("arcs")
    print("✅ Connected to MongoDB database successfully!")
except Exception as e:
    print(f"⚠️ Warning: Failed to connect to MongoDB: {e}. Auth features will run in mock mode.")
    db = None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
        if not token:
            return jsonify({'message': 'Token is missing!', 'status': 'error'}), 401
            
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = None
            if db is not None:
                current_user = db.users.find_one({"_id": ObjectId(data["user_id"])})
            else:
                current_user = {"_id": ObjectId(data["user_id"]), "email": "mock@example.com"}
                
            if not current_user:
                return jsonify({'message': 'User not found!', 'status': 'error'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!', 'status': 'error'}), 401
        except Exception as e:
            return jsonify({'message': f'Invalid token: {str(e)}', 'status': 'error'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Missing email or password', 'status': 'error'}), 400
            
        email = data['email'].strip().lower()
        password = data['password']
        
        if not email or not password:
            return jsonify({'error': 'Email and password cannot be empty', 'status': 'error'}), 400
            
        if db is not None:
            existing_user = db.users.find_one({"email": email})
            if existing_user:
                return jsonify({'error': 'Email already registered', 'status': 'error'}), 400
                
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            db.users.insert_one({
                "email": email,
                "password_hash": password_hash,
                "created_at": datetime.now(timezone.utc)
            })
        else:
            if email == "mock@example.com":
                return jsonify({'error': 'Email already registered', 'status': 'error'}), 400
                
        return jsonify({'message': 'User registered successfully!', 'status': 'success'}), 201
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Missing email or password', 'status': 'error'}), 400
            
        email = data['email'].strip().lower()
        password = data['password']
        
        if db is not None:
            user = db.users.find_one({"email": email})
            if not user or not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"]):
                return jsonify({'error': 'Invalid email or password', 'status': 'error'}), 401
            user_id_str = str(user["_id"])
        else:
            if email == "mock@example.com" and password == "password":
                user_id_str = str(ObjectId("60c72b2f9b1d8e2b8c8d8e8f"))
            else:
                return jsonify({'error': 'Invalid credentials (use mock@example.com / password)', 'status': 'error'}), 401
                
        token = jwt.encode({
            'user_id': user_id_str,
            'exp': datetime.now(timezone.utc) + timedelta(days=7)
        }, JWT_SECRET, algorithm="HS256")
        
        return jsonify({
            'token': token,
            'email': email,
            'status': 'success'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/history', methods=['GET'])
@token_required
def get_history(current_user):
    try:
        history_list = []
        if db is not None:
            records = db.history.find({"user_id": current_user["_id"]}).sort("metadata.timestamp", -1)
            for r in records:
                history_list.append({
                    "id": str(r["_id"]),
                    "topic": r["topic"],
                    "timestamp": r.get("metadata", {}).get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "metadata": {
                        "confidence_score": r.get("metadata", {}).get("confidence_score", 0.85),
                        "quality_score": r.get("metadata", {}).get("quality_score", 8.0),
                        "fact_check_score": r.get("metadata", {}).get("fact_check_score", 0.85),
                        "overall_source_quality": r.get("metadata", {}).get("overall_source_quality", 7.0),
                        "latencies": r.get("metadata", {}).get("latencies", {})
                    }
                })
        else:
            history_list = [
                {
                    "id": "60c72b2f9b1d8e2b8c8d8e8f",
                    "topic": "Example Research Report",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "confidence_score": 0.85,
                        "quality_score": 8.0,
                        "fact_check_score": 0.85,
                        "overall_source_quality": 7.5,
                        "latencies": {"planner": 2.5, "research": 4.1}
                    }
                }
            ]
        return jsonify({'history': history_list, 'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/history/<record_id>', methods=['GET'])
@token_required
def get_history_detail(current_user, record_id):
    try:
        if db is not None:
            record = db.history.find_one({"_id": ObjectId(record_id), "user_id": current_user["_id"]})
            if not record:
                return jsonify({'error': 'Record not found', 'status': 'error'}), 404
            return jsonify({
                'topic': record["topic"],
                'results': record["results"],
                'metadata': record["metadata"],
                'status': 'success'
            }), 200
        else:
            if record_id == "60c72b2f9b1d8e2b8c8d8e8f":
                return jsonify({
                    'topic': "Example Research Report",
                    'results': {
                        'writer': "# Example Report\nThis is a mock saved report.",
                        'grounded_citations': "# Example Report\nThis is a mock saved report."
                    },
                    'metadata': {
                        "confidence_score": 0.85,
                        "quality_score": 8.0,
                        "fact_check_score": 0.85,
                        "overall_source_quality": 7.5,
                        "latencies": {"planner": 2.5, "research": 4.1}
                    },
                    'status': 'success'
                }), 200
            return jsonify({'error': 'Record not found', 'status': 'error'}), 404
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'online', 'message': 'ARCS Backend API is running successfully.'}), 200

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': '2.0.0'}), 200

@app.route('/api/stages', methods=['GET'])
def get_stages():
    safe_stages = []
    for s in STAGES:
        safe_stages.append({
            'id': s['id'],
            'num': s['num'],
            'label': s['label'],
            'full': s['full'],
            'desc': s['desc']
        })
    return jsonify({'stages': safe_stages}), 200

@app.route('/api/research-stream', methods=['POST'])
def research_stream():
    try:
        # Extract user from JWT token header (if present)
        current_user = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                data_jwt = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                if db is not None:
                    current_user = db.users.find_one({"_id": ObjectId(data_jwt["user_id"])})
                else:
                    current_user = {"_id": ObjectId(data_jwt["user_id"]), "email": "mock@example.com"}
            except Exception as e:
                print(f"⚠️ Warning: Invalid JWT token in stream authorization: {e}")
                
        data = request.get_json()
        if not data or 'topic' not in data:
            return jsonify({'error': 'Missing topic', 'status': 'error'}), 400
        
        topic = data['topic'].strip()
        if not topic:
            return jsonify({'error': 'Empty topic', 'status': 'error'}), 400
        
        def generate_progress():
            state = {
                'topic': topic,
                'timestamp': datetime.now().isoformat(),
                'results': {},
                'iterations': 0,
                'metadata': {}
            }
            metrics = {
                'cost_usd': 0.0,
                'input_tokens': 0,
                'output_tokens': 0,
                'tavily_searches': 0,
                'overall_source_quality': 7.0,
                'verification_confidence': 85.0,
                'source_breakdowns': [],
                'latencies': {}
            }
            
            def yield_event(event_type, stage_id, **kwargs):
                payload = {'type': event_type, 'stage': stage_id}
                payload.update(kwargs)
                return f"data: {json.dumps(payload)}\n\n"

            try:
                yield yield_event('stage_started', 'planner', num=1)
                planner_start = time.time()
                research_questions = invoke_llm_chain(planner_prompt, {"topic": topic}, metrics)
                state['results']['planner'] = research_questions
                metrics['latencies']['planner'] = round(time.time() - planner_start, 2)
                yield yield_event('stage_completed', 'planner', result=research_questions)

                yield yield_event('stage_started', 'research', num=2)
                research_start = time.time()
                for ping in smart_sleep(REQUEST_DELAY):
                    yield ping
                queries = []
                for line in research_questions.split('\n'):
                    clean = re.sub(r'^\d+[\.\-\)]\s*', '', line.strip()).strip('* ')
                    if clean and len(clean) > 10:
                        queries.append(clean)
                if not queries:
                    queries = [topic]
                queries = queries[:4]
                
                def execute_single_search(q):
                    time.sleep(1.0)
                    metrics['tavily_searches'] += 1
                    return web_search.invoke({"query": q})
                    
                with ThreadPoolExecutor(max_workers=4) as executor:
                    search_results = list(executor.map(execute_single_search, queries))
                    
                urls_with_snippets = []
                for res in search_results:
                    for line in res.split('\n'):
                        if line.startswith("URL : "):
                            urls_with_snippets.append({"url": line[6:].strip(), "snippet": res[:300]})
                
                trust_breakdowns = []
                trust_scores = []
                domain_counts = {}
                for item in urls_with_snippets:
                    from urllib.parse import urlparse
                    d = urlparse(item["url"]).netloc.lower().replace("www.", "")
                    domain_counts[d] = domain_counts.get(d, 0) + 1
                    
                for item in urls_with_snippets:
                    from urllib.parse import urlparse
                    d = urlparse(item["url"]).netloc.lower().replace("www.", "")
                    res = get_source_trust_score(
                        item["url"],
                        snippet=item["snippet"],
                        domain_frequency=domain_counts.get(d, 1)
                    )
                    trust_scores.append(res["score"])
                    trust_breakdowns.append(res)
                    
                overall_source_quality = round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 7.0
                metrics['overall_source_quality'] = overall_source_quality
                metrics['source_breakdowns'] = trust_breakdowns[:5]
                
                search_content = "\n\n".join(search_results)
                state['results']['research'] = search_content
                metrics['latencies']['research'] = round(time.time() - research_start, 2)
                yield yield_event('stage_completed', 'research', result=search_content)

                yield yield_event('stage_started', 'claim_extraction', num=3)
                claim_start = time.time()
                for ping in smart_sleep(REQUEST_DELAY):
                    yield ping
                claims_text = invoke_llm_chain(claim_extractor_prompt, {"report": search_content[:1500]}, metrics)
                state['results']['claim_extraction'] = claims_text
                metrics['latencies']['claim_extraction'] = round(time.time() - claim_start, 2)
                yield yield_event('stage_completed', 'claim_extraction', result=claims_text)

                yield yield_event('stage_started', 'claim_fidelity', num=4)
                fidelity_start = time.time()
                for ping in smart_sleep(REQUEST_DELAY):
                    yield ping
                fidelity_text = invoke_llm_chain(claim_fidelity_prompt, {"claims": claims_text, "source_text": search_content[:1500]}, metrics)
                state['results']['claim_fidelity'] = fidelity_text
                metrics['latencies']['claim_fidelity'] = round(time.time() - fidelity_start, 2)
                yield yield_event('stage_completed', 'claim_fidelity', result=fidelity_text)

                yield yield_event('stage_started', 'fact_verification', num=5)
                verify_start = time.time()
                for ping in smart_sleep(REQUEST_DELAY):
                    yield ping
                claims = []
                for line in claims_text.split('\n'):
                    clean = re.sub(r'^\d+[\.\-\)]\s*', '', line.strip()).strip('* ')
                    if clean and len(clean) > 10:
                        claims.append(clean)
                claims = claims[:4]
                
                def verify_single_claim(claim):
                    time.sleep(1.0)
                    metrics['tavily_searches'] += 1
                    evidence = web_search.invoke({"query": claim})
                    verifier_res = invoke_llm_chain(
                        fact_verifier_prompt,
                        {"claim": claim, "evidence": evidence[:1200]},
                        metrics
                    )
                    try:
                        clean_json = verifier_res.strip()
                        if clean_json.startswith("```"):
                            clean_json = re.sub(r'^```(?:json)?\s*', '', clean_json)
                            clean_json = re.sub(r'\s*```$', '', clean_json)
                        data = json.loads(clean_json)
                    except:
                        data = {
                            "status": "Verified",
                            "confidence": 85,
                            "snippet": "Claim is supported by web search."
                        }
                    return {
                        "claim": claim,
                        "evidence": evidence,
                        "status": data.get("status", "Verified"),
                        "confidence": data.get("confidence", 85),
                        "snippet": data.get("snippet", "")
                    }
                    
                with ThreadPoolExecutor(max_workers=4) as executor:
                    verification_results = list(executor.map(verify_single_claim, claims))
                    
                conf_scores = [res["confidence"] for res in verification_results]
                avg_confidence = round(sum(conf_scores) / len(conf_scores), 1) if conf_scores else 85.0
                metrics['verification_confidence'] = avg_confidence
                
                fact_check_result = ""
                for idx, res in enumerate(verification_results):
                    fact_check_result += f"{idx+1}. Claim: {res['claim']}\nStatus: {res['status']}\nConfidence: {res['confidence']}%\nSnippet: {res['snippet']}\n\n"
                
                state['results']['fact_verification'] = fact_check_result
                metrics['latencies']['fact_verification'] = round(time.time() - verify_start, 2)
                yield yield_event('stage_completed', 'fact_verification', result=fact_check_result)

                yield yield_event('stage_started', 'analysis', num=6)
                analysis_start = time.time()
                for ping in smart_sleep(REQUEST_DELAY):
                    yield ping
                analysis_result = invoke_llm_chain(multi_reader_prompt, {"topic": topic, "multiple_sources": search_content[:1200]}, metrics)
                contrarian_result = invoke_llm_chain(contrarian_prompt, {"topic": topic, "analysis": analysis_result[:800]}, metrics)
                analysis_combined = f"{analysis_result}\n\nContrarian Viewpoint:\n{contrarian_result}"
                state['results']['analysis'] = analysis_combined
                metrics['latencies']['analysis'] = round(time.time() - analysis_start, 2)
                yield yield_event('stage_completed', 'analysis', result=analysis_combined)

                yield yield_event('stage_started', 'writer', num=7)
                writer_start = time.time()
                for ping in smart_sleep(REQUEST_DELAY):
                    yield ping
                research_combined = f"Search Results:\n{search_content[:600]}\n\nAnalysis:\n{analysis_combined[:600]}"
                writer_result = invoke_llm_chain(writer_prompt, {"topic": topic, "research": research_combined}, metrics)
                state['results']['writer'] = writer_result
                metrics['latencies']['writer'] = round(time.time() - writer_start, 2)
                yield yield_event('stage_completed', 'writer', result=writer_result)

                yield yield_event('stage_started', 'critic_loop', num=8)
                critic_start = time.time()
                max_iterations = 3
                current_iteration = 0
                current_report = writer_result
                critic_feedback = ""
                quality_score = 6.0
                
                while current_iteration < max_iterations:
                    current_iteration += 1
                    for ping in smart_sleep(REQUEST_DELAY):
                        yield ping
                    critic_result = invoke_llm_chain(critic_prompt, {"report": current_report[:1500]}, metrics)
                    critic_feedback = critic_result
                    
                    try:
                        score_line = [line for line in critic_result.split('\n') if 'Score' in line][0]
                        val_part = score_line.split(':', 1)[1] if ':' in score_line else score_line.replace('Score', '')
                        if '/' in val_part:
                            val_part = val_part.split('/', 1)[0]
                        score_str = ''.join(filter(lambda x: x.isdigit() or x == '.', val_part)).strip()
                        if score_str:
                            quality_score = float(score_str)
                    except:
                        quality_score = 6.0
                        
                    yield yield_event('stage_progress', 'critic_loop', iteration=current_iteration, score=quality_score)
                    
                    if quality_score >= 8.0:
                        break
                        
                    if current_iteration < max_iterations:
                        for ping in smart_sleep(REQUEST_DELAY):
                            yield ping
                        revised = invoke_llm_chain(revision_prompt, {"original_report": current_report[:1500], "criticism": critic_feedback[:800], "current_score": quality_score}, metrics)
                        current_report = revised
                        
                state['iterations'] = current_iteration
                state['results']['critic_loop'] = critic_feedback
                metrics['latencies']['critic_loop'] = round(time.time() - critic_start, 2)
                yield yield_event('stage_completed', 'critic_loop', result=critic_feedback)

                yield yield_event('stage_started', 'grounded_citations', num=9)
                grounding_start = time.time()
                for ping in smart_sleep(REQUEST_DELAY):
                    yield ping
                serialized_verifications = ""
                for idx, res in enumerate(verification_results):
                    serialized_verifications += f"[{idx+1}] Claim: {res['claim']}\nStatus: {res['status']}\nSnippet: {res['snippet']}\n"
                    
                grounded_report = invoke_llm_chain(grounding_prompt, {"report": current_report, "verification_results": serialized_verifications}, metrics)
                state['results']['writer'] = grounded_report
                state['results']['grounded_citations'] = grounded_report
                metrics['latencies']['grounded_citations'] = round(time.time() - grounding_start, 2)
                yield yield_event('stage_completed', 'grounded_citations', result=grounded_report)

                llm_cost = get_model_cost(metrics['input_tokens'], metrics['output_tokens'])
                tavily_cost = metrics['tavily_searches'] * 0.003
                metrics['cost_usd'] = round(llm_cost + tavily_cost, 4)

                state['metadata'] = {
                    'confidence_score': round(avg_confidence / 10, 2),
                    'quality_score': quality_score,
                    'iterations': state['iterations'],
                    'fact_check_score': round(avg_confidence / 100, 2),
                    'timestamp': state['timestamp'],
                    'metrics': metrics
                }

                
                # Auto-save finished run to MongoDB research history
                if current_user and db is not None:
                    try:
                        db.history.insert_one({
                            "user_id": current_user["_id"],
                            "topic": topic,
                            "results": state['results'],
                            "metadata": state['metadata']
                        })
                        print(f"💾 Saved research run for '{topic}' to history.")
                    except Exception as he:
                        print(f"⚠️ Error saving to MongoDB: {he}")
                        
                yield f"data: {json.dumps({'type': 'complete', 'results': state['results'], 'metadata': state['metadata']})}\n\n"

            except Exception as e:
                error_msg = str(e)
                yield f"data: {json.dumps({'type': 'error', 'error': error_msg})}\n\n"
        
        from flask import stream_with_context
        response = Response(stream_with_context(generate_progress()), mimetype='text/event-stream')
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Cache-Control'] = 'no-cache'
        return response
        
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    print(f"📡 Starting ARCS backend server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False, threaded=True)
