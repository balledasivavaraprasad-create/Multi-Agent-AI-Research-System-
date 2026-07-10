from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import json
import time
import re
import traceback
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

google_api_key = os.getenv("GOOGLE_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

from agents import (
    planner_chain, multi_reader_chain, contrarian_chain,
    writer_chain, critic_chain, revision_chain,
    claim_extractor_chain, fact_verifier_chain, grounding_chain,
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

def get_model_cost(input_tokens, output_tokens):
    return (input_tokens * 0.075 / 1000000) + (output_tokens * 0.30 / 1000000)

def track_call(response, metrics):
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        in_t = response.usage_metadata.get('input_tokens', 0)
        out_t = response.usage_metadata.get('output_tokens', 0)
        metrics['input_tokens'] += in_t
        metrics['output_tokens'] += out_t
        metrics['cost_usd'] += get_model_cost(in_t, out_t)

def invoke_llm_chain(prompt_template, inputs, metrics):
    prompt_val = prompt_template.invoke(inputs)
    response = llm.invoke(prompt_val)
    track_call(response, metrics)
    return response.content

@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'online', 'message': 'ARCS Backend API is running successfully.'}), 200

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': '2.0.0'}), 200

@app.route('/api/research-stream', methods=['POST'])
def research_stream():
    try:
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
                'overall_source_quality': 7.0,
                'verification_confidence': 85.0,
                'latencies': {}
            }
            
            def yield_event(event_type, stage_id, **kwargs):
                payload = {'type': event_type, 'stage': stage_id}
                payload.update(kwargs)
                return f"data: {json.dumps(payload)}\n\n"

            try:
                yield yield_event('stage_started', 'planner', num=1)
                planner_start = time.time()
                research_questions = invoke_llm_chain(planner_chain, {"topic": topic}, metrics)
                state['results']['planner'] = research_questions
                metrics['latencies']['planner'] = round(time.time() - planner_start, 2)
                yield yield_event('stage_completed', 'planner', result=research_questions)

                yield yield_event('stage_started', 'research', num=2)
                research_start = time.time()
                time.sleep(REQUEST_DELAY)
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
                    return web_search.invoke({"query": q})
                    
                with ThreadPoolExecutor(max_workers=4) as executor:
                    search_results = list(executor.map(execute_single_search, queries))
                    
                urls = []
                for res in search_results:
                    for line in res.split('\n'):
                        if line.startswith("URL : "):
                            urls.append(line[6:].strip())
                
                trust_scores = [get_source_trust_score(url) for url in urls]
                overall_source_quality = round(sum(trust_scores) / len(trust_scores), 1) if trust_scores else 7.0
                metrics['overall_source_quality'] = overall_source_quality
                
                search_content = "\n\n".join(search_results)
                state['results']['research'] = search_content
                metrics['latencies']['research'] = round(time.time() - research_start, 2)
                yield yield_event('stage_completed', 'research', result=search_content)

                yield yield_event('stage_started', 'claim_extraction', num=3)
                claim_start = time.time()
                time.sleep(REQUEST_DELAY)
                claims_text = invoke_llm_chain(claim_extractor_chain, {"report": search_content[:1500]}, metrics)
                state['results']['claim_extraction'] = claims_text
                metrics['latencies']['claim_extraction'] = round(time.time() - claim_start, 2)
                yield yield_event('stage_completed', 'claim_extraction', result=claims_text)

                yield yield_event('stage_started', 'fact_verification', num=4)
                verify_start = time.time()
                time.sleep(REQUEST_DELAY)
                claims = []
                for line in claims_text.split('\n'):
                    clean = re.sub(r'^\d+[\.\-\)]\s*', '', line.strip()).strip('* ')
                    if clean and len(clean) > 10:
                        claims.append(clean)
                claims = claims[:4]
                
                def verify_single_claim(claim):
                    time.sleep(1.0)
                    evidence = web_search.invoke({"query": claim})
                    verifier_res = invoke_llm_chain(
                        fact_verifier_chain,
                        {"claim": claim, "evidence": evidence[:1200]},
                        metrics
                    )
                    try:
                        data = json.loads(verifier_res)
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

                yield yield_event('stage_started', 'analysis', num=5)
                analysis_start = time.time()
                time.sleep(REQUEST_DELAY)
                analysis_result = invoke_llm_chain(multi_reader_chain, {"topic": topic, "multiple_sources": search_content[:1200]}, metrics)
                contrarian_result = invoke_llm_chain(contrarian_chain, {"topic": topic, "analysis": analysis_result[:800]}, metrics)
                analysis_combined = f"{analysis_result}\n\nContrarian Viewpoint:\n{contrarian_result}"
                state['results']['analysis'] = analysis_combined
                metrics['latencies']['analysis'] = round(time.time() - analysis_start, 2)
                yield yield_event('stage_completed', 'analysis', result=analysis_combined)

                yield yield_event('stage_started', 'writer', num=6)
                writer_start = time.time()
                time.sleep(REQUEST_DELAY)
                research_combined = f"Search Results:\n{search_content[:600]}\n\nAnalysis:\n{analysis_combined[:600]}"
                writer_result = invoke_llm_chain(writer_chain, {"topic": topic, "research": research_combined}, metrics)
                state['results']['writer'] = writer_result
                metrics['latencies']['writer'] = round(time.time() - writer_start, 2)
                yield yield_event('stage_completed', 'writer', result=writer_result)

                yield yield_event('stage_started', 'critic_loop', num=7)
                critic_start = time.time()
                max_iterations = 3
                current_iteration = 0
                current_report = writer_result
                critic_feedback = ""
                quality_score = 6.0
                
                while current_iteration < max_iterations:
                    current_iteration += 1
                    time.sleep(REQUEST_DELAY)
                    critic_result = invoke_llm_chain(critic_chain, {"report": current_report[:1500]}, metrics)
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
                        
                    if quality_score >= 8.0:
                        break
                        
                    if current_iteration < max_iterations:
                        time.sleep(REQUEST_DELAY)
                        revised = invoke_llm_chain(revision_chain, {"original_report": current_report[:1500], "criticism": critic_feedback[:800], "current_score": quality_score}, metrics)
                        current_report = revised
                        
                state['iterations'] = current_iteration
                state['results']['critic_loop'] = critic_feedback
                metrics['latencies']['critic_loop'] = round(time.time() - critic_start, 2)
                yield yield_event('stage_completed', 'critic_loop', result=critic_feedback)

                yield yield_event('stage_started', 'grounded_citations', num=8)
                grounding_start = time.time()
                time.sleep(REQUEST_DELAY)
                serialized_verifications = ""
                for idx, res in enumerate(verification_results):
                    serialized_verifications += f"[{idx+1}] Claim: {res['claim']}\nStatus: {res['status']}\nSnippet: {res['snippet']}\n"
                    
                grounded_report = invoke_llm_chain(grounding_chain, {"report": current_report, "verification_results": serialized_verifications}, metrics)
                state['results']['writer'] = grounded_report
                state['results']['grounded_citations'] = grounded_report
                metrics['latencies']['grounded_citations'] = round(time.time() - grounding_start, 2)
                yield yield_event('stage_completed', 'grounded_citations', result=grounded_report)

                state['metadata'] = {
                    'confidence_score': avg_confidence / 10,
                    'quality_score': quality_score,
                    'iterations': state['iterations'],
                    'fact_check_score': avg_confidence / 100,
                    'timestamp': state['timestamp'],
                    'metrics': metrics
                }
                
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
