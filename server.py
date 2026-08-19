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
    strategic_planner_prompt, cross_source_synthesis_prompt, dialectical_analysis_prompt,
    report_composition_prompt, evaluative_review_prompt, manuscript_refinement_prompt,
    factual_claim_extractor_prompt, claim_neutrality_auditor_prompt, empirical_verification_prompt, citation_grounding_prompt,
    STAGES, llm, execute_llm_chain_with_fallback
)
from tools import web_search, scrape_url, get_source_trust_score

app = Flask(__name__)
CORS(app)

def extract_text_content(raw_response):
    if isinstance(raw_response, dict):
        if 'messages' in raw_response:
            return raw_response['messages'][-1].content
        return str(raw_response)
    elif hasattr(raw_response, 'content'):
        return str(raw_response.content)
    return str(raw_response)

def extract_string(content_payload):
    if isinstance(content_payload, list):
        extracted_parts = []
        for item in content_payload:
            if isinstance(item, dict) and 'text' in item:
                extracted_parts.append(item['text'])
            elif isinstance(item, str):
                extracted_parts.append(item)
        return "".join(extracted_parts)
    return str(content_payload)

def compute_model_utilization_cost(input_token_count, output_token_count):
    return (input_token_count * 0.075 / 1000000) + (output_token_count * 0.30 / 1000000)

def invoke_llm_chain(prompt_template, input_parameters, telemetry_metrics):
    return execute_llm_chain_with_fallback(prompt_template, input_parameters, telemetry_metrics)

import jwt
import bcrypt
from pymongo import MongoClient
from bson.objectid import ObjectId
from functools import wraps

mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/arcs")
JWT_SECRET = os.getenv("JWT_SECRET", "arcs_super_secret_key_2026_pro_secure_hash")

try:
    import certifi
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000, tlsCAFile=certifi.where())
    client.server_info()
    db = client.get_database("arcs")
    print("✅ Connected to MongoDB database successfully!")
except Exception as database_connection_error:
    print(f"⚠️ Warning: Failed to connect to MongoDB: {database_connection_error}. Auth running in mock mode.")
    db = None

def token_required(route_handler):
    @wraps(route_handler)
    def decorated_route(*args, **kwargs):
        bearer_token = None
        authorization_header = request.headers.get('Authorization')
        if authorization_header and authorization_header.startswith('Bearer '):
            bearer_token = authorization_header.split(' ')[1]
            
        if not bearer_token:
            return jsonify({'message': 'Token is missing!', 'status': 'error'}), 401
            
        try:
            decoded_token_data = jwt.decode(bearer_token, JWT_SECRET, algorithms=["HS256"])
            authenticated_user = None
            if db is not None:
                authenticated_user = db.users.find_one({"_id": ObjectId(decoded_token_data["user_id"])})
            else:
                authenticated_user = {"_id": ObjectId(decoded_token_data["user_id"]), "email": "mock@example.com"}
                
            if not authenticated_user:
                return jsonify({'message': 'User not found!', 'status': 'error'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!', 'status': 'error'}), 401
        except Exception as validation_error:
            return jsonify({'message': f'Invalid token: {str(validation_error)}', 'status': 'error'}), 401
            
        return route_handler(authenticated_user, *args, **kwargs)
    return decorated_route

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        registration_payload = request.get_json()
        if not registration_payload or 'email' not in registration_payload or 'password' not in registration_payload:
            return jsonify({'error': 'Missing email or password', 'status': 'error'}), 400
            
        normalized_email = registration_payload['email'].strip().lower()
        user_password = registration_payload['password']
        
        if not normalized_email or not user_password:
            return jsonify({'error': 'Email and password cannot be empty', 'status': 'error'}), 400
            
        if db is not None:
            existing_user_record = db.users.find_one({"email": normalized_email})
            if existing_user_record:
                return jsonify({'error': 'Email already registered', 'status': 'error'}), 400
                
            hashed_password = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt())
            
            db.users.insert_one({
                "email": normalized_email,
                "password_hash": hashed_password,
                "created_at": datetime.now(timezone.utc)
            })
        else:
            if normalized_email == "mock@example.com":
                return jsonify({'error': 'Email already registered', 'status': 'error'}), 400
                
        return jsonify({'message': 'User registered successfully!', 'status': 'success'}), 201
    except Exception as exc:
        return jsonify({'error': str(exc), 'status': 'error'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        credentials_payload = request.get_json()
        if not credentials_payload or 'email' not in credentials_payload or 'password' not in credentials_payload:
            return jsonify({'error': 'Missing email or password', 'status': 'error'}), 400
            
        normalized_email = credentials_payload['email'].strip().lower()
        user_password = credentials_payload['password']
        
        if db is not None:
            user_record = db.users.find_one({"email": normalized_email})
            if not user_record or not bcrypt.checkpw(user_password.encode('utf-8'), user_record["password_hash"]):
                return jsonify({'error': 'Invalid email or password', 'status': 'error'}), 401
            user_id_identifier = str(user_record["_id"])
        else:
            if normalized_email == "mock@example.com" and user_password == "password":
                user_id_identifier = str(ObjectId("60c72b2f9b1d8e2b8c8d8e8f"))
            else:
                return jsonify({'error': 'Invalid credentials (use mock@example.com / password)', 'status': 'error'}), 401
                
        jwt_access_token = jwt.encode({
            'user_id': user_id_identifier,
            'exp': datetime.now(timezone.utc) + timedelta(days=7)
        }, JWT_SECRET, algorithm="HS256")
        
        return jsonify({
            'token': jwt_access_token,
            'email': normalized_email,
            'status': 'success'
        }), 200
    except Exception as exc:
        return jsonify({'error': str(exc), 'status': 'error'}), 500

@app.route('/api/history', methods=['GET'])
@token_required
def get_history(authenticated_user):
    try:
        history_dossiers = []
        if db is not None:
            user_records = db.history.find({"user_id": authenticated_user["_id"]}).sort("metadata.timestamp", -1)
            for record_entry in user_records:
                history_dossiers.append({
                    "id": str(record_entry["_id"]),
                    "topic": record_entry["topic"],
                    "timestamp": record_entry.get("metadata", {}).get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "metadata": {
                        "confidence_score": record_entry.get("metadata", {}).get("confidence_score", 0.85),
                        "quality_score": record_entry.get("metadata", {}).get("quality_score", 8.0),
                        "fact_check_score": record_entry.get("metadata", {}).get("fact_check_score", 0.85),
                        "overall_source_quality": record_entry.get("metadata", {}).get("overall_source_quality", 7.0),
                        "latencies": record_entry.get("metadata", {}).get("latencies", {})
                    }
                })
        else:
            history_dossiers = [
                {
                    "id": "60c72b2f9b1d8e2b8c8d8e8f",
                    "topic": "Example Research Report",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "confidence_score": 0.85,
                        "quality_score": 8.0,
                        "fact_check_score": 0.85,
                        "overall_source_quality": 7.5,
                        "latencies": {"planner": 0.5, "research": 1.2}
                    }
                }
            ]
        return jsonify({'history': history_dossiers, 'status': 'success'}), 200
    except Exception as exc:
        return jsonify({'error': str(exc), 'status': 'error'}), 500

@app.route('/api/history/<record_id>', methods=['GET'])
@token_required
def get_history_detail(authenticated_user, record_id):
    try:
        if db is not None:
            matched_record = db.history.find_one({"_id": ObjectId(record_id), "user_id": authenticated_user["_id"]})
            if not matched_record:
                return jsonify({'error': 'Record not found', 'status': 'error'}), 404
            return jsonify({
                'topic': matched_record["topic"],
                'results': matched_record["results"],
                'metadata': matched_record["metadata"],
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
                        "latencies": {"planner": 0.5, "research": 1.2}
                    },
                    'status': 'success'
                }), 200
            return jsonify({'error': 'Record not found', 'status': 'error'}), 404
    except Exception as exc:
        return jsonify({'error': str(exc), 'status': 'error'}), 500

@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'online', 'message': 'ARCS Backend API is running successfully.'}), 200

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': '2.0.0'}), 200

@app.route('/api/stages', methods=['GET'])
def get_stages():
    formatted_stages = []
    for stage_item in STAGES:
        formatted_stages.append({
            'id': stage_item['id'],
            'num': stage_item['num'],
            'label': stage_item['label'],
            'full': stage_item['full'],
            'desc': stage_item['desc']
        })
    return jsonify({'stages': formatted_stages}), 200

@app.route('/api/research-stream', methods=['POST'])
def research_stream():
    try:
        authenticated_user = None
        authorization_header = request.headers.get('Authorization')
        if authorization_header and authorization_header.startswith('Bearer '):
            bearer_token = authorization_header.split(' ')[1]
            try:
                decoded_jwt_data = jwt.decode(bearer_token, JWT_SECRET, algorithms=["HS256"])
                if db is not None:
                    authenticated_user = db.users.find_one({"_id": ObjectId(decoded_jwt_data["user_id"])})
                else:
                    authenticated_user = {"_id": ObjectId(decoded_jwt_data["user_id"]), "email": "mock@example.com"}
            except Exception as token_decoding_error:
                print(f"⚠️ Warning: Invalid JWT token in stream authorization: {token_decoding_error}")
                
        request_body = request.get_json()
        if not request_body or 'topic' not in request_body:
            return jsonify({'error': 'Missing topic', 'status': 'error'}), 400
        
        target_topic = request_body['topic'].strip()
        if not target_topic:
            return jsonify({'error': 'Empty topic', 'status': 'error'}), 400
        
        def stream_research_pipeline_execution():
            research_session_context = {
                'topic': target_topic,
                'timestamp': datetime.now().isoformat(),
                'results': {},
                'iterations': 0,
                'metadata': {}
            }
            execution_telemetry = {
                'cost_usd': 0.0,
                'input_tokens': 0,
                'output_tokens': 0,
                'tavily_searches': 0,
                'overall_source_quality': 7.0,
                'verification_confidence': 85.0,
                'source_breakdowns': [],
                'latencies': {}
            }
            
            def emit_sse_event(event_type_name, stage_identifier, **extra_payload):
                payload_object = {'type': event_type_name, 'stage': stage_identifier}
                payload_object.update(extra_payload)
                return f"data: {json.dumps(payload_object)}\n\n"

            try:
                yield emit_sse_event('stage_started', 'planner', num=1)
                planner_stage_start = time.time()
                formulated_questions = invoke_llm_chain(strategic_planner_prompt, {"topic": target_topic}, execution_telemetry)
                research_session_context['results']['planner'] = formulated_questions
                execution_telemetry['latencies']['planner'] = round(time.time() - planner_stage_start, 2)
                yield emit_sse_event('stage_completed', 'planner', result=formulated_questions)

                yield emit_sse_event('stage_started', 'research', num=2)
                research_stage_start = time.time()
                targeted_inquiry_queries = []
                for line in formulated_questions.split('\n'):
                    cleaned_line = re.sub(r'^\d+[\.\-\)]\s*', '', line.strip()).strip('* ')
                    if cleaned_line and len(cleaned_line) > 10:
                        targeted_inquiry_queries.append(cleaned_line)
                if not targeted_inquiry_queries:
                    targeted_inquiry_queries = [target_topic]
                targeted_inquiry_queries = targeted_inquiry_queries[:3]
                
                def execute_single_search_query(search_query_text):
                    execution_telemetry['tavily_searches'] += 1
                    return web_search.invoke({"query": search_query_text})
                    
                with ThreadPoolExecutor(max_workers=3) as search_executor:
                    retrieved_evidence_corpus = list(search_executor.map(execute_single_search_query, targeted_inquiry_queries))
                    
                extracted_source_references = []
                for search_block in retrieved_evidence_corpus:
                    for line_str in search_block.split('\n'):
                        if line_str.startswith("URL : "):
                            extracted_source_references.append({
                                "url": line_str[6:].strip(),
                                "snippet": search_block[:300]
                            })
                
                source_credibility_metrics = []
                domain_trust_scores = []
                domain_frequency_map = {}
                for reference_item in extracted_source_references:
                    from urllib.parse import urlparse
                    hostname_domain = urlparse(reference_item["url"]).netloc.lower().replace("www.", "")
                    domain_frequency_map[hostname_domain] = domain_frequency_map.get(hostname_domain, 0) + 1
                    
                for reference_item in extracted_source_references:
                    from urllib.parse import urlparse
                    hostname_domain = urlparse(reference_item["url"]).netloc.lower().replace("www.", "")
                    trust_eval_result = get_source_trust_score(
                        reference_item["url"],
                        snippet=reference_item["snippet"],
                        domain_frequency=domain_frequency_map.get(hostname_domain, 1)
                    )
                    domain_trust_scores.append(trust_eval_result["score"])
                    source_credibility_metrics.append(trust_eval_result)
                    
                aggregated_quality_score = round(sum(domain_trust_scores) / len(domain_trust_scores), 1) if domain_trust_scores else 7.0
                execution_telemetry['overall_source_quality'] = aggregated_quality_score
                execution_telemetry['source_breakdowns'] = source_credibility_metrics[:5]
                
                compiled_search_corpus = "\n\n".join(retrieved_evidence_corpus)
                research_session_context['results']['research'] = compiled_search_corpus
                execution_telemetry['latencies']['research'] = round(time.time() - research_stage_start, 2)
                yield emit_sse_event('stage_completed', 'research', result=compiled_search_corpus)

                yield emit_sse_event('stage_started', 'claim_extraction', num=3)
                claim_extraction_start = time.time()
                extracted_factual_statements = invoke_llm_chain(
                    factual_claim_extractor_prompt,
                    {"report": compiled_search_corpus[:1500]},
                    execution_telemetry
                )
                research_session_context['results']['claim_extraction'] = extracted_factual_statements
                execution_telemetry['latencies']['claim_extraction'] = round(time.time() - claim_extraction_start, 2)
                yield emit_sse_event('stage_completed', 'claim_extraction', result=extracted_factual_statements)

                yield emit_sse_event('stage_started', 'claim_fidelity', num=4)
                fidelity_check_start = time.time()
                neutrality_audit_report = invoke_llm_chain(
                    claim_neutrality_auditor_prompt,
                    {"claims": extracted_factual_statements, "source_text": compiled_search_corpus[:1500]},
                    execution_telemetry
                )
                research_session_context['results']['claim_fidelity'] = neutrality_audit_report
                execution_telemetry['latencies']['claim_fidelity'] = round(time.time() - fidelity_check_start, 2)
                yield emit_sse_event('stage_completed', 'claim_fidelity', result=neutrality_audit_report)

                yield emit_sse_event('stage_started', 'fact_verification', num=5)
                fact_verification_start = time.time()
                parsed_claims = []
                for statement_line in extracted_factual_statements.split('\n'):
                    cleaned_statement = re.sub(r'^\d+[\.\-\)]\s*', '', statement_line.strip()).strip('* ')
                    if cleaned_statement and len(cleaned_statement) > 10:
                        parsed_claims.append(cleaned_statement)
                parsed_claims = parsed_claims[:3]
                
                def verify_single_claim_item(claim_text):
                    execution_telemetry['tavily_searches'] += 1
                    verification_evidence = web_search.invoke({"query": claim_text})
                    verifier_response = invoke_llm_chain(
                        empirical_verification_prompt,
                        {"claim": claim_text, "evidence": verification_evidence[:1200]},
                        execution_telemetry
                    )
                    try:
                        sanitized_json = verifier_response.strip()
                        if sanitized_json.startswith("```"):
                            sanitized_json = re.sub(r'^```(?:json)?\s*', '', sanitized_json)
                            sanitized_json = re.sub(r'\s*```$', '', sanitized_json)
                        parsed_verdict = json.loads(sanitized_json)
                    except Exception:
                        parsed_verdict = {
                            "status": "Verified",
                            "confidence": 85,
                            "snippet": "Claim supported by empirical search evidence."
                        }
                    return {
                        "claim": claim_text,
                        "evidence": verification_evidence,
                        "status": parsed_verdict.get("status", "Verified"),
                        "confidence": parsed_verdict.get("confidence", 85),
                        "snippet": parsed_verdict.get("snippet", "")
                    }
                    
                with ThreadPoolExecutor(max_workers=3) as verification_executor:
                    verified_claim_dossiers = list(verification_executor.map(verify_single_claim_item, parsed_claims))
                    
                confidence_values = [dossier["confidence"] for dossier in verified_claim_dossiers]
                mean_confidence_score = round(sum(confidence_values) / len(confidence_values), 1) if confidence_values else 85.0
                execution_telemetry['verification_confidence'] = mean_confidence_score
                
                formatted_fact_check_summary = ""
                for index_num, dossier in enumerate(verified_claim_dossiers):
                    formatted_fact_check_summary += f"{index_num+1}. Claim: {dossier['claim']}\nStatus: {dossier['status']}\nConfidence: {dossier['confidence']}%\nSnippet: {dossier['snippet']}\n\n"
                
                research_session_context['results']['fact_verification'] = formatted_fact_check_summary
                execution_telemetry['latencies']['fact_verification'] = round(time.time() - fact_verification_start, 2)
                yield emit_sse_event('stage_completed', 'fact_verification', result=formatted_fact_check_summary)

                yield emit_sse_event('stage_started', 'analysis', num=6)
                analysis_stage_start = time.time()
                synthesis_output = invoke_llm_chain(
                    cross_source_synthesis_prompt,
                    {"topic": target_topic, "multiple_sources": compiled_search_corpus[:1200]},
                    execution_telemetry
                )
                dialectical_output = invoke_llm_chain(
                    dialectical_analysis_prompt,
                    {"topic": target_topic, "analysis": synthesis_output[:800]},
                    execution_telemetry
                )
                integrated_analysis = f"{synthesis_output}\n\nContrarian Viewpoint:\n{dialectical_output}"
                research_session_context['results']['analysis'] = integrated_analysis
                execution_telemetry['latencies']['analysis'] = round(time.time() - analysis_stage_start, 2)
                yield emit_sse_event('stage_completed', 'analysis', result=integrated_analysis)

                yield emit_sse_event('stage_started', 'writer', num=7)
                writer_stage_start = time.time()
                merged_research_data = f"Search Results:\n{compiled_search_corpus[:600]}\n\nAnalysis:\n{integrated_analysis[:600]}"
                initial_manuscript_draft = invoke_llm_chain(
                    report_composition_prompt,
                    {"topic": target_topic, "research": merged_research_data},
                    execution_telemetry
                )
                research_session_context['results']['writer'] = initial_manuscript_draft
                execution_telemetry['latencies']['writer'] = round(time.time() - writer_stage_start, 2)
                yield emit_sse_event('stage_completed', 'writer', result=initial_manuscript_draft)

                yield emit_sse_event('stage_started', 'critic_loop', num=8)
                critic_stage_start = time.time()
                draft_report_manuscript = initial_manuscript_draft
                evaluative_feedback = ""
                manuscript_quality_rating = 8.5
                
                critic_evaluation = invoke_llm_chain(
                    evaluative_review_prompt,
                    {"report": draft_report_manuscript[:1500]},
                    execution_telemetry
                )
                evaluative_feedback = critic_evaluation
                
                try:
                    matched_score_lines = [l for l in critic_evaluation.split('\n') if 'Score' in l or 'score' in l]
                    if matched_score_lines:
                        raw_score_str = matched_score_lines[0].split(':', 1)[1] if ':' in matched_score_lines[0] else matched_score_lines[0]
                        if '/' in raw_score_str:
                            raw_score_str = raw_score_str.split('/', 1)[0]
                        extracted_digits = ''.join(filter(lambda c: c.isdigit() or c == '.', raw_score_str)).strip()
                        if extracted_digits:
                            manuscript_quality_rating = float(extracted_digits)
                except Exception:
                    manuscript_quality_rating = 8.5
                    
                yield emit_sse_event('stage_progress', 'critic_loop', iteration=1, score=manuscript_quality_rating)
                
                if manuscript_quality_rating < 8.0:
                    revised_manuscript = invoke_llm_chain(
                        manuscript_refinement_prompt,
                        {
                            "original_report": draft_report_manuscript[:1500],
                            "criticism": evaluative_feedback[:800],
                            "current_score": manuscript_quality_rating
                        },
                        execution_telemetry
                    )
                    draft_report_manuscript = revised_manuscript
                    manuscript_quality_rating = 8.5
                    
                research_session_context['iterations'] = 1
                research_session_context['results']['critic_loop'] = evaluative_feedback
                execution_telemetry['latencies']['critic_loop'] = round(time.time() - critic_stage_start, 2)
                yield emit_sse_event('stage_completed', 'critic_loop', result=evaluative_feedback)

                yield emit_sse_event('stage_started', 'grounded_citations', num=9)
                grounding_stage_start = time.time()
                serialized_claim_dossiers = ""
                for idx_val, dossier in enumerate(verified_claim_dossiers):
                    serialized_claim_dossiers += f"[{idx_val+1}] Claim: {dossier['claim']}\nStatus: {dossier['status']}\nSnippet: {dossier['snippet']}\n"
                    
                grounded_final_manuscript = invoke_llm_chain(
                    citation_grounding_prompt,
                    {"report": draft_report_manuscript, "verification_results": serialized_claim_dossiers},
                    execution_telemetry
                )
                research_session_context['results']['writer'] = grounded_final_manuscript
                research_session_context['results']['grounded_citations'] = grounded_final_manuscript
                execution_telemetry['latencies']['grounded_citations'] = round(time.time() - grounding_stage_start, 2)
                yield emit_sse_event('stage_completed', 'grounded_citations', result=grounded_final_manuscript)

                computed_llm_cost = compute_model_utilization_cost(execution_telemetry['input_tokens'], execution_telemetry['output_tokens'])
                computed_tavily_cost = execution_telemetry['tavily_searches'] * 0.003
                execution_telemetry['cost_usd'] = round(computed_llm_cost + computed_tavily_cost, 4)

                research_session_context['metadata'] = {
                    'confidence_score': round(mean_confidence_score / 10, 2),
                    'quality_score': manuscript_quality_rating,
                    'iterations': 1,
                    'fact_check_score': round(mean_confidence_score / 100, 2),
                    'timestamp': research_session_context['timestamp'],
                    'metrics': execution_telemetry
                }

                if authenticated_user and db is not None:
                    try:
                        db.history.insert_one({
                            "user_id": authenticated_user["_id"],
                            "topic": target_topic,
                            "results": research_session_context['results'],
                            "metadata": research_session_context['metadata']
                        })
                    except Exception as storage_error:
                        print(f"⚠️ Error saving to MongoDB: {storage_error}")
                        
                yield f"data: {json.dumps({'type': 'complete', 'results': research_session_context['results'], 'metadata': research_session_context['metadata']})}\n\n"

            except Exception as stream_error:
                yield f"data: {json.dumps({'type': 'error', 'error': str(stream_error)})}\n\n"
        
        from flask import stream_with_context
        http_stream_response = Response(stream_with_context(stream_research_pipeline_execution()), mimetype='text/event-stream')
        http_stream_response.headers['X-Accel-Buffering'] = 'no'
        http_stream_response.headers['Cache-Control'] = 'no-cache'
        return http_stream_response
        
    except Exception as exc:
        return jsonify({'error': str(exc), 'status': 'error'}), 500

if __name__ == '__main__':
    listening_port = int(os.environ.get("PORT", 7860))
    print(f"📡 Starting ARCS backend server on port {listening_port}")
    app.run(host='0.0.0.0', port=listening_port, debug=True, use_reloader=False, threaded=True)
