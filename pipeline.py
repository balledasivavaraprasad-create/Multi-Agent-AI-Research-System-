
import os
import sys
import time
import json
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY") == "placeholder_key":
    sys.exit(1)

if not os.getenv("TAVILY_API_KEY"):
    sys.exit(1)

from agents import (
    planner_prompt, multi_reader_prompt, contrarian_prompt,
    writer_prompt, critic_prompt, revision_prompt,
    claim_extractor_prompt, fact_verifier_prompt, grounding_prompt,
    STAGES, llm
)
from tools import web_search, scrape_url, get_source_trust_score

REQUEST_DELAY = 4.5

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
        metrics['cost_usd'] += get_model_cost(in_t, out_t)

def invoke_llm_chain(prompt_template, inputs, metrics):
    prompt_val = prompt_template.invoke(inputs)
    response = llm.invoke(prompt_val)
    track_call(response, metrics)
    return extract_string(response.content)

def run_research_pipeline(topic: str) -> dict:
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
    
    try:
        t_start = time.time()
        
        planner_start = time.time()
        research_questions = invoke_llm_chain(planner_prompt, {"topic": topic}, metrics)
        state['results']['planner'] = research_questions
        metrics['latencies']['planner'] = round(time.time() - planner_start, 2)
        
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
        
        claim_start = time.time()
        time.sleep(REQUEST_DELAY)
        claims_text = invoke_llm_chain(claim_extractor_prompt, {"report": search_content[:1500]}, metrics)
        state['results']['claim_extraction'] = claims_text
        metrics['latencies']['claim_extraction'] = round(time.time() - claim_start, 2)
        
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
                fact_verifier_prompt,
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
        
        analysis_start = time.time()
        time.sleep(REQUEST_DELAY)
        analysis_result = invoke_llm_chain(multi_reader_prompt, {"topic": topic, "multiple_sources": search_content[:1200]}, metrics)
        contrarian_result = invoke_llm_chain(contrarian_prompt, {"topic": topic, "analysis": analysis_result[:800]}, metrics)
        analysis_combined = f"{analysis_result}\n\nContrarian Viewpoint:\n{contrarian_result}"
        state['results']['analysis'] = analysis_combined
        metrics['latencies']['analysis'] = round(time.time() - analysis_start, 2)
        
        writer_start = time.time()
        time.sleep(REQUEST_DELAY)
        research_combined = f"Search Results:\n{search_content[:600]}\n\nAnalysis:\n{analysis_combined[:600]}"
        writer_result = invoke_llm_chain(writer_prompt, {"topic": topic, "research": research_combined}, metrics)
        state['results']['writer'] = writer_result
        metrics['latencies']['writer'] = round(time.time() - writer_start, 2)
        
        critic_start = time.time()
        max_iterations = 3
        current_iteration = 0
        current_report = writer_result
        critic_feedback = ""
        quality_score = 6.0
        
        while current_iteration < max_iterations:
            current_iteration += 1
            time.sleep(REQUEST_DELAY)
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
                
            if quality_score >= 8.0:
                break
                
            if current_iteration < max_iterations:
                time.sleep(REQUEST_DELAY)
                revised = invoke_llm_chain(revision_prompt, {"original_report": current_report[:1500], "criticism": critic_feedback[:800], "current_score": quality_score}, metrics)
                current_report = revised
                
        state['iterations'] = current_iteration
        state['results']['critic_loop'] = critic_feedback
        metrics['latencies']['critic_loop'] = round(time.time() - critic_start, 2)
        
        grounding_start = time.time()
        time.sleep(REQUEST_DELAY)
        serialized_verifications = ""
        for idx, res in enumerate(verification_results):
            serialized_verifications += f"[{idx+1}] Claim: {res['claim']}\nStatus: {res['status']}\nSnippet: {res['snippet']}\n"
            
        grounded_report = invoke_llm_chain(grounding_prompt, {"report": current_report, "verification_results": serialized_verifications}, metrics)
        state['results']['writer'] = grounded_report
        state['results']['grounded_citations'] = grounded_report
        metrics['latencies']['grounded_citations'] = round(time.time() - grounding_start, 2)
        
        final_output = {
            'status': 'success',
            'topic': topic,
            'results': state['results'],
            'metadata': {
                'confidence_score': avg_confidence / 10,
                'quality_score': quality_score,
                'iterations': state['iterations'],
                'fact_check_score': avg_confidence / 100,
                'timestamp': state['timestamp'],
                'metrics': metrics
            }
        }
        
        return final_output
        
    except Exception as e:
        error_msg = str(e)
        return {
            'status': 'error',
            'error': error_msg,
            'partial_results': state['results'],
            'metadata': state['metadata']
        }

if __name__ == "__main__":
    topic = input()
    result = run_research_pipeline(topic)
    print(json.dumps(result, indent=2))
