import os
import sys
import time
import re
from dotenv import load_dotenv

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError as err:
    print(f"\n❌ Error importing dependencies: {str(err)}")
    sys.exit(1)

try:
    from langchain.agents import create_agent
except ImportError:
    try:
        from langgraph.prebuilt import create_react_agent as create_agent
    except ImportError:
        def create_agent(model_instance, agent_tools, **kwargs):
            try:
                from langgraph.prebuilt import create_react_agent
                return create_react_agent(model_instance, agent_tools, **kwargs)
            except ImportError:
                raise ImportError(
                    "Could not import either 'create_agent' from 'langchain.agents' "
                    "or 'create_react_agent' from 'langgraph.prebuilt'."
                )

from tools import web_search, scrape_url

load_dotenv()

_CACHED_MODEL_POOL = None

def initialize_generative_model_pool():
    global _CACHED_MODEL_POOL
    if _CACHED_MODEL_POOL is not None and len(_CACHED_MODEL_POOL) > 0:
        return _CACHED_MODEL_POOL

    api_credential_keys = []
    for key_name in ["GOOGLE_API_KEY", "GOOGLE_API_KEY_2", "GOOGLE_API_KEY_3", "GOOGLE_API_KEY_4"]:
        credential = os.getenv(key_name)
        if credential and credential.strip() and credential.strip() != "placeholder_key":
            api_credential_keys.append(credential.strip())
            
    if not api_credential_keys:
        api_credential_keys = [os.getenv("GOOGLE_API_KEY", "placeholder_key")]

    candidate_model_identifiers = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-pro",
    ]
    
    active_model_pool = []
    for model_id in candidate_model_identifiers:
        for api_key in api_credential_keys:
            try:
                model_inst = ChatGoogleGenerativeAI(
                    model=model_id,
                    google_api_key=api_key,
                    temperature=0.1,
                    max_retries=1,
                    timeout=25,
                )
                active_model_pool.append(model_inst)
            except Exception:
                pass
                
    _CACHED_MODEL_POOL = active_model_pool
    return _CACHED_MODEL_POOL

get_llm_models_pool = initialize_generative_model_pool

llm_pool = initialize_generative_model_pool()
llm = llm_pool[0] if llm_pool else ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY", "placeholder_key"))

def execute_llm_chain_with_fallback(prompt_template, input_parameters, telemetry_metrics=None):
    formatted_prompt = prompt_template.invoke(input_parameters)
    available_models = initialize_generative_model_pool()
    
    last_encountered_error = None
    for target_model in available_models:
        for attempt in range(2):
            try:
                model_response = target_model.invoke(formatted_prompt)
                if hasattr(model_response, 'usage_metadata') and model_response.usage_metadata and telemetry_metrics is not None:
                    input_tokens = model_response.usage_metadata.get('input_tokens', 0)
                    output_tokens = model_response.usage_metadata.get('output_tokens', 0)
                    telemetry_metrics['input_tokens'] += input_tokens
                    telemetry_metrics['output_tokens'] += output_tokens
                response_content = model_response.content
                if isinstance(response_content, list):
                    extracted_parts = [
                        item['text'] if isinstance(item, dict) and 'text' in item else str(item)
                        for item in response_content
                    ]
                    return "".join(extracted_parts)
                return str(response_content)
            except Exception as exc:
                last_encountered_error = exc
                err_message = str(exc)
                
                retry_match = re.search(r'retry in ([0-9\.]+)s', err_message, re.IGNORECASE)
                if retry_match and attempt == 0:
                    wait_seconds = min(3.0, float(retry_match.group(1)) + 0.25)
                    time.sleep(wait_seconds)
                    continue
                elif ("429" in err_message or "RESOURCE_EXHAUSTED" in err_message or "503" in err_message or "UNAVAILABLE" in err_message) and attempt == 0:
                    time.sleep(1.5)
                    continue
                break
            
    raise RuntimeError(f"All LLM models in fallback pool exhausted: {str(last_encountered_error)}")

invoke_llm_chain_with_fallback = execute_llm_chain_with_fallback

def construct_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search]
    )

def construct_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url]
    )

report_composition_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert research writer capable of composing clear, highly structured, authoritative reports."),
    ("human", """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Executive Summary
- Key Findings (minimum 3 well-explained points)
- Comparative Analysis
- Strategic Implications
- Conclusion
- Sources (list all URLs found in research)

Be detailed, factual, objective, and professional.""")
])
writer_prompt = report_composition_prompt
writer_chain = report_composition_prompt | llm | StrOutputParser()

evaluative_review_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a rigorous, constructive research critic and quality auditor."),
    ("human", """Review the research report below and evaluate its rigor, structure, depth, and evidence quality.

Report: {report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Actionable Suggestions for Report Improvement (For User):
- ...
- ...

Key Gaps & Unanswered Angles:
- ...
- ...

Overall Verdict:
...""")
])
critic_prompt = evaluative_review_prompt
critic_chain = evaluative_review_prompt | llm | StrOutputParser()

strategic_planner_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a research strategist. Generate 4 to 5 focused research questions that structure inquiry into the topic comprehensively."),
    ("human", """Topic: {topic}

Generate focused research questions that will structure a comprehensive research project. Format:

1. [Question 1]
2. [Question 2]
[...]""")
])
planner_prompt = strategic_planner_prompt
planner_chain = strategic_planner_prompt | llm | StrOutputParser()

fact_auditor_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a rigorous fact-checker. Identify unsupported claims, verify statistics, check dates, and assess claim reliability."),
    ("human", """Review this research content for factual accuracy:

{content}

Provide:
1. List of verified claims (with confidence 0-100%)
2. Unverified or questionable claims
3. Statistical accuracy assessment
4. Overall reliability score (0-100%)""")
])
fact_checker_prompt = fact_auditor_prompt
fact_checker_chain = fact_auditor_prompt | llm | StrOutputParser()

dialectical_analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a contrarian researcher. Challenge assumptions, find contradictions, and present alternative viewpoints."),
    ("human", """Based on this research analysis about {topic}:

{analysis}

Provide:
1. Key assumptions made
2. Contradicting evidence or perspectives
3. Alternative interpretations
4. Weaknesses in reasoning""")
])
contrarian_prompt = dialectical_analysis_prompt
contrarian_chain = dialectical_analysis_prompt | llm | StrOutputParser()

source_reference_formatter_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a citation expert. Format all sources properly and create a professional reference list."),
    ("human", """Create a formal reference list from these sources:

{sources_data}

Format as:
[1] Full Title - URL - Source Type - Quality Assessment
[2] ...""")
])
citation_prompt = source_reference_formatter_prompt
citation_chain = source_reference_formatter_prompt | llm | StrOutputParser()

cross_source_synthesis_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert multi-source analyst. Synthesize insights from multiple sources, identify consensus and conflicts."),
    ("human", """Analyze these multiple sources about "{topic}":

{multiple_sources}

Provide:
1. Common themes across sources
2. Unique insights per source
3. Points of agreement and conflict
4. Consensus level (0-100%)""")
])
multi_reader_prompt = cross_source_synthesis_prompt
multi_reader_chain = cross_source_synthesis_prompt | llm | StrOutputParser()

analytical_confidence_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a research quality assessor. Calculate confidence based on multiple factors."),
    ("human", """Calculate research confidence for this project:

Topic: {topic}

Factors:
- Number of sources: {num_sources}/7
- Source quality average: {quality_avg}/10
- Fact-check score: {fact_check}/100
- Source agreement level: {agreement}/100
- Data freshness: {freshness}/100

Formula: (sources*0.25 + quality*0.25 + facts*0.20 + agreement*0.15 + freshness*0.10) / 10""")
])
confidence_prompt = analytical_confidence_prompt
confidence_chain = analytical_confidence_prompt | llm | StrOutputParser()

manuscript_refinement_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a report revision specialist. Improve the report based on critical feedback to achieve quality standards."),
    ("human", """Original Report:
{original_report}

Critic Feedback:
{criticism}

Current Score: {current_score}/10
Target Score: 8.0+

Revise the report to address the feedback while maintaining factual integrity.""")
])
revision_prompt = manuscript_refinement_prompt
revision_chain = manuscript_refinement_prompt | llm | StrOutputParser()

factual_claim_extractor_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an elite research analyst. Extract exactly 3 key factual claims from the provided report that require independent verification. Respond in a clean, numbered list of claims, with absolutely no introduction or explanation."),
    ("human", "{report}")
])
claim_extractor_prompt = factual_claim_extractor_prompt
claim_extractor_chain = factual_claim_extractor_prompt | llm | StrOutputParser()

claim_neutrality_auditor_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a claim fidelity auditor. Evaluate whether the extracted claims accurately and neutrally represent the underlying source text without distortion, exaggeration, or strawman framing.\nFor each claim, state if it is faithful (Yes/No) and provide a refined neutral version if needed."),
    ("human", "Claims to Audit:\n{claims}\n\nSource Research Text:\n{source_text}")
])
claim_fidelity_prompt = claim_neutrality_auditor_prompt
claim_fidelity_chain = claim_neutrality_auditor_prompt | llm | StrOutputParser()

empirical_verification_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an unbiased fact-checker. Verify the claim below against the provided search evidence.\nClaim: {claim}\n\nEvidence:\n{evidence}\n\nEvaluate the claim based on the evidence. Respond in a clean JSON format (with no markdown code block formatting) containing exactly these three fields:\n- status: 'Verified' | 'Not Verified' | 'Partially Verified'\n- confidence: a number from 0 to 100\n- snippet: a short, specific supporting text snippet from the evidence"),
    ("human", "Verify this claim.")
])
fact_verifier_prompt = empirical_verification_prompt
fact_verifier_chain = empirical_verification_prompt | llm | StrOutputParser()

citation_grounding_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a professional research editor. Ground the provided research report with inline citations using numbers like [1], [2], etc., corresponding to the verified evidence.\n\nReport:\n{report}\n\nVerified Evidence:\n{verification_results}\n\nRewrite the report to integrate the inline citations naturally. At the very end of the report, add a 'Citations & Sources' section listing each numbered citation, the source URL, and the exact supporting evidence snippet in the format:\n[1] Source Name (URL)\nEvidence: \"exact snippet\""),
    ("human", "Ground this report.")
])
grounding_prompt = citation_grounding_prompt
grounding_chain = citation_grounding_prompt | llm | StrOutputParser()

STAGES = [
    {
        'id': 'planner',
        'num': '01',
        'label': 'Planning',
        'full': 'Planner Agent',
        'desc': 'Structuring research into focused questions',
        'chain': planner_chain,
    },
    {
        'id': 'research',
        'num': '02',
        'label': 'Research',
        'full': 'Parallel Multi-Query Research',
        'desc': 'Gathering multi-source data parallelly',
        'chain': None,
    },
    {
        'id': 'claim_extraction',
        'num': '03',
        'label': 'Claim Extraction',
        'full': 'Claim Extractor Agent',
        'desc': 'Extracting key factual claims requiring verification',
        'chain': claim_extractor_chain,
    },
    {
        'id': 'claim_fidelity',
        'num': '04',
        'label': 'Claim Fidelity Check',
        'full': 'Claim Fidelity Agent',
        'desc': 'Auditing extracted claims against source text neutrality',
        'chain': claim_fidelity_chain,
    },
    {
        'id': 'fact_verification',
        'num': '05',
        'label': 'Fact Verification',
        'full': 'Real-Time Fact Verification',
        'desc': 'Searching evidence and verifying claims in parallel',
        'chain': fact_verifier_chain,
    },
    {
        'id': 'analysis',
        'num': '06',
        'label': 'Analysis & Synthesis',
        'full': 'Multi-Source Analysis',
        'desc': 'Extracting insights and integrating contrarian views',
        'chain': multi_reader_chain,
    },
    {
        'id': 'writer',
        'num': '07',
        'label': 'Writing',
        'full': 'Writer Agent',
        'desc': 'Composing initial research report',
        'chain': writer_chain,
    },
    {
        'id': 'critic_loop',
        'num': '08',
        'label': 'Quality Loop',
        'full': 'Critic & Revision Loop',
        'desc': 'Iterative refinement and scoring',
        'chain': critic_chain,
    },
    {
        'id': 'grounded_citations',
        'num': '09',
        'label': 'Grounded Citations',
        'full': 'Grounding & Citations Agent',
        'desc': 'Aligning evidence, inline references and footnotes',
        'chain': grounding_chain,
    }
]

STAGE_CONFIGS = {stage['id']: stage for stage in STAGES}
