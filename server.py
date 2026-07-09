
# Copyright (c) 2026 Siva. All rights reserved.
# This software and associated documentation files are the proprietary property of Siva.
# Unauthorized copying, distribution, or modification is strictly prohibited.

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import json
import time
import traceback
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Verify that required API keys are configured
groq_api_key = os.getenv("GROQ_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

if not groq_api_key or groq_api_key == "placeholder_key":
    print("\n⚠️ WARNING: GROQ_API_KEY is missing or using placeholder! Agents will fail to execute.")
    print("Please configure your GROQ_API_KEY in the '.env' file.\n")

if not tavily_api_key:
    print("\n⚠️ WARNING: TAVILY_API_KEY is missing! Search tools will fail to execute.")
    print("Please configure your TAVILY_API_KEY in the '.env' file.\n")

from agents import (
    build_search_agent, build_reader_agent,
    planner_chain, fact_checker_chain, contrarian_chain,
    citation_chain, multi_reader_chain, confidence_chain,
    writer_chain, critic_chain, revision_chain,
    STAGES, STAGE_CONFIGS
)

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

@app.route('/', methods=['GET'])
def index():
    return jsonify({'status': 'online', 'message': 'ARCS Backend API is running successfully. Connect via Vercel frontend!'}), 200

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
        data = request.get_json()
        if not data or 'topic' not in data:
            return jsonify({'error': 'Missing required field: topic', 'status': 'error'}), 400
        
        topic = data['topic'].strip()
        if not topic:
            return jsonify({'error': 'Topic cannot be empty', 'status': 'error'}), 400
        
        def generate_progress():
            state = {'topic': topic, 'timestamp': datetime.now().isoformat(), 'results': {}, 'iterations': 0, 'metadata': {}}
            
            def yield_event(event_type, stage_id, **kwargs):
                payload = {'type': event_type, 'stage': stage_id}
                payload.update(kwargs)
                return f"data: {json.dumps(payload)}\n\n"

            try:
                yield yield_event('stage_started', 'planner', num=1)
                research_questions = planner_chain.invoke({"topic": topic})
                state['results']['planner'] = research_questions
                yield yield_event('stage_completed', 'planner', result=research_questions)

                yield yield_event('stage_started', 'research', num=2)
                time.sleep(1.5)
                search_agent = build_search_agent()
                search_result = search_agent.invoke({
                    "messages": [("user", f"Find recent, reliable sources about {topic}. Provide top 5-7 sources with details. Research Questions:\n{research_questions[:300]}")]
                })
                search_content = extract_text_content(search_result)
                state['results']['research'] = search_content
                yield yield_event('stage_completed', 'research', result=search_content)

                yield yield_event('stage_started', 'factcheck', num=3)
                time.sleep(1.5)
                fact_check_result = fact_checker_chain.invoke({"content": search_content[:1200]})
                state['results']['factcheck'] = fact_check_result
                try:
                    if 'reliability score' in fact_check_result.lower():
                        score_part = fact_check_result[fact_check_result.lower().find('reliability score'):]
                        score_val = ''.join(filter(str.isdigit, score_part.split('\n')[0]))
                        if score_val: state['metadata']['fact_check_score'] = int(score_val[:2]) / 100
                except: state['metadata']['fact_check_score'] = 0.85
                yield yield_event('stage_completed', 'factcheck', result=fact_check_result)

                yield yield_event('stage_started', 'analysis', num=4)
                time.sleep(1.5)
                analysis_result = multi_reader_chain.invoke({"topic": topic, "multiple_sources": search_content[:1200]})
                state['results']['analysis'] = analysis_result
                yield yield_event('stage_completed', 'analysis', result=analysis_result)

                yield yield_event('stage_started', 'contrarian', num=5)
                time.sleep(1.5)
                contrarian_result = contrarian_chain.invoke({"topic": topic, "analysis": analysis_result[:800]})
                state['results']['contrarian'] = contrarian_result
                yield yield_event('stage_completed', 'contrarian', result=contrarian_result)

                yield yield_event('stage_started', 'writer', num=6)
                time.sleep(1.5)
                research_combined = f"Search Results:\n{search_content[:600]}\n\nAnalysis:\n{analysis_result[:600]}\n\nAlternative Perspectives:\n{contrarian_result[:300]}"
                writer_result = writer_chain.invoke({"topic": topic, "research": research_combined})
                state['results']['writer'] = writer_result
                yield yield_event('stage_completed', 'writer', result=writer_result)

                yield yield_event('stage_started', 'critic_loop', num=7)
                max_iterations = 3
                current_iteration = 0
                current_report = writer_result
                critic_feedback = ""
                quality_score = 0
                
                while current_iteration < max_iterations:
                    current_iteration += 1
                    time.sleep(1.5)
                    critic_result = critic_chain.invoke({"report": current_report[:1500]})
                    critic_feedback = critic_result
                    try:
                        score_line = [line for line in critic_result.split('\n') if 'Score' in line][0]
                        val_part = score_line.split(':', 1)[1] if ':' in score_line else score_line.replace('Score', '')
                        if '/' in val_part:
                            val_part = val_part.split('/', 1)[0]
                        score_str = ''.join(filter(lambda x: x.isdigit() or x == '.', val_part)).strip()
                        if score_str: quality_score = float(score_str)
                    except: quality_score = 6.0
                    
                    if quality_score >= 8.0:
                        break
                    if current_iteration < max_iterations:
                        time.sleep(1.5)
                        current_report = revision_chain.invoke({
                            "original_report": current_report[:1500],
                            "criticism": critic_feedback[:800],
                            "current_score": quality_score,
                        })

                state['iterations'] = current_iteration
                state['results']['final_report'] = current_report
                state['results']['critic_loop'] = critic_feedback
                yield yield_event('stage_completed', 'critic_loop', result=critic_feedback)

                yield yield_event('stage_started', 'confidence', num=8)
                time.sleep(1.5)
                citation_result = citation_chain.invoke({"sources_data": f"{search_content[:800]}"})
                state['results']['citations'] = citation_result
                try:
                    confidence = ((5 / 7) * 0.25 + (7.5 / 10) * 0.25 + (state['metadata'].get('fact_check_score', 0.85)) * 0.20 + (85 / 100) * 0.15 + (90 / 100) * 0.10) * 10
                except: confidence = 7.5
                state['metadata']['confidence_score'] = round(confidence, 1)
                yield yield_event('stage_completed', 'confidence', result=citation_result)

                yield f"data: {json.dumps({'type': 'complete', 'results': state['results'], 'metadata': state['metadata']})}\n\n"

            except Exception as e:
                print(f"Pipeline error: {str(e)}")
                print(traceback.format_exc())
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
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
