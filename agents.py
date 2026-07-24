# Copyright (c) 2026 Siva. All rights reserved.
# This software and associated documentation files are the proprietary property of Siva.
# Unauthorized copying, distribution, or modification is strictly prohibited.

import os
import sys
from dotenv import load_dotenv

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError as e:
    print(f"\n❌ Error importing dependencies: {str(e)}")
    print("Please ensure you are running in the virtual environment.")
    print("Run: source .venv/bin/activate (on macOS/Linux) or .venv\\Scripts\\activate (on Windows)")
    print("Then install requirements: pip install -r requirements.txt\n")
    sys.exit(1)

try:
    from langchain.agents import create_agent
except ImportError:
    try:
        from langgraph.prebuilt import create_react_agent as create_agent
    except ImportError:
        def create_agent(model, tools, **kwargs):
            try:
                from langgraph.prebuilt import create_react_agent
                return create_react_agent(model, tools, **kwargs)
            except ImportError:
                raise ImportError(
                    "Could not import either 'create_agent' from 'langchain.agents' "
                    "or 'create_react_agent' from 'langgraph.prebuilt'. "
                    "Please update your packages: pip install -U langchain langgraph"
                )

from tools import web_search, scrape_url

load_dotenv()

def get_llm_models_pool():
    google_keys = []
    for k in ["GOOGLE_API_KEY", "GOOGLE_API_KEY_2", "GOOGLE_API_KEY_3", "GOOGLE_API_KEY_4"]:
        val = os.getenv(k)
        if val and val.strip() and val.strip() != "placeholder_key":
            google_keys.append(val.strip())
            
    if not google_keys:
        google_keys = [os.getenv("GOOGLE_API_KEY", "placeholder_key")]

    models_to_try = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-pro-latest",
    ]
    
    pool = []
    for g_key in google_keys:
        for m_name in models_to_try:
            try:
                m = ChatGoogleGenerativeAI(
                    model=m_name,
                    google_api_key=g_key,
                    temperature=0,
                    max_retries=0,
                    timeout=30,
                )
                pool.append(m)
            except Exception:
                pass
                
    return pool


llm_pool = get_llm_models_pool()
llm = llm_pool[0] if llm_pool else ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY", "placeholder_key"))

def invoke_llm_chain_with_fallback(prompt_template, inputs, metrics=None):
    prompt_val = prompt_template.invoke(inputs)
    pool = get_llm_models_pool()
    
    last_error = None
    for model_inst in pool:
        try:
            response = model_inst.invoke(prompt_val)
            if hasattr(response, 'usage_metadata') and response.usage_metadata and metrics is not None:
                in_t = response.usage_metadata.get('input_tokens', 0)
                out_t = response.usage_metadata.get('output_tokens', 0)
                metrics['input_tokens'] += in_t
                metrics['output_tokens'] += out_t
            content = response.content
            if isinstance(content, list):
                parts = [p['text'] if isinstance(p, dict) and 'text' in p else str(p) for p in content]
                return "".join(parts)
            return str(content)
        except Exception as e:
            err_str = str(e)
            model_name = getattr(model_inst, 'model', 'gemini')
            print(f"⚠️ Model [{model_name}] hit rate limit or API error: {err_str[:120]}. Falling back to next model...")
            last_error = e
            time.sleep(1.0)
            
    raise RuntimeError(f"All LLM models in fallback pool exhausted: {str(last_error)}")




def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search]
    )

def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url]
    )

writer_prompt = ChatPromptTemplate.from_messages([
    ("system","You are an expert research writer. You have the ability to write clear, structured and insightful reports"),
    ("human", """Write a detailed research report on the topic below
     Topic : {topic}

     Research Gathered :
     {research}

     Structure of the report as :

     - Introduction
     - Key Findings (minimum 3 well-explained points)
     - Conclusion
     - Sources (list all URLs found in the research)
     
     Be detailed, factual and professional.""")
])

writer_chain = writer_prompt | llm | StrOutputParser()

critic_prompt = ChatPromptTemplate.from_messages([
    ("system","You are a sharp and constructive research critic. Be brutally honest and specific"),
    ("human","""Review the research report below and evaluate it strictly.
     
     Report: {report}

     Respond in this exact format :

     Score : X/10

     Strengths:
     - ...
     - ...
     - ...

     Areas To Imporove :
     - ...
     - ...
     - ...

     one line verdict :

     ..."""),
])

critic_chain = critic_prompt | llm | StrOutputParser()


planner_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a research strategist. Generate 5-8 focused research questions that structure inquiry into the topic comprehensively."),
    ("human", """Topic: {topic}

Generate focused research questions that will structure a comprehensive research project. Format:

1. [Question 1]
2. [Question 2]
[...]

Each question should be specific, measurable, and cover different aspects of the topic.""")
])
planner_chain = planner_prompt | llm | StrOutputParser()

fact_checker_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a rigorous fact-checker. Identify unsupported claims, verify statistics, check dates, and assess claim reliability."),
    ("human", """Review this research content for factual accuracy:

{content}

Provide:
1. List of verified claims (with confidence 0-100%)
2. Unverified or questionable claims
3. Statistical accuracy assessment
4. Overall reliability score (0-100%)

Be specific and cite what makes claims reliable or unreliable.""")
])
fact_checker_chain = fact_checker_prompt | llm | StrOutputParser()

contrarian_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a contrarian researcher. Challenge assumptions, find contradictions, and present alternative viewpoints."),
    ("human", """Based on this research analysis about {topic}:

{analysis}

Provide:
1. Key assumptions made (list them)
2. Contradicting evidence or perspectives
3. Alternative interpretations
4. Weaknesses in the reasoning
5. What might be missing

Be specific and constructive.""")
])
contrarian_chain = contrarian_prompt | llm | StrOutputParser()

citation_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a citation expert. Format all sources properly and create a professional reference list."),
    ("human", """Create a formal reference list from these sources:

{sources_data}

Format as:
[1] Full Title - URL - Source Type - Quality Assessment
[2] ...

Also provide:
- Total unique sources
- Primary vs secondary breakdown
- Source quality distribution""")
])
citation_chain = citation_prompt | llm | StrOutputParser()

multi_reader_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert multi-source analyst. Synthesize insights from multiple sources, identify consensus and conflicts."),
    ("human", """Analyze these multiple sources about "{topic}":

{multiple_sources}

Provide:
1. Common themes across sources
2. Unique insights per source
3. Points of agreement and conflict
4. Consensus level (0-100%)
5. Source reliability ranking

Link insights to specific sources.""")
])
multi_reader_chain = multi_reader_prompt | llm | StrOutputParser()

confidence_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a research quality assessor. Calculate confidence based on multiple factors."),
    ("human", """Calculate research confidence for this project:

Topic: {topic}

Factors:
- Number of sources: {num_sources}/7
- Source quality average: {quality_avg}/10
- Fact-check score: {fact_check}/100
- Source agreement level: {agreement}/100
- Data freshness: {freshness}/100

Provide:
1. Confidence score (0-10)
2. Breakdown of contributing factors
3. Reliability assessment
4. Recommendations for improvement

Formula: (sources*0.25 + quality*0.25 + facts*0.20 + agreement*0.15 + freshness*0.10) / 10""")
])
confidence_chain = confidence_prompt | llm | StrOutputParser()


revision_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a report revision specialist. Improve the report based on critical feedback to achieve quality standards."),
    ("human", """Original Report:
{original_report}

Critic Feedback:
{criticism}

Current Score: {current_score}/10
Target Score: 8.0+

Revise the report to address the feedback while maintaining factual integrity. Focus on:
1. Addressing specific weaknesses mentioned
2. Strengthening evidence-based claims
3. Improving structure and clarity
4. Adding missing analysis
5. Ensuring professional tone

Provide the revised report.""")
])
revision_chain = revision_prompt | llm | StrOutputParser()
claim_extractor_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an elite research analyst. Extract exactly 3 to 5 key factual claims from the provided report that require independent verification. Respond in a clean, numbered list of claims, with absolutely no introduction or explanation."),
    ("human", "{report}")
])
claim_extractor_chain = claim_extractor_prompt | llm | StrOutputParser()

claim_fidelity_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a claim fidelity auditor. Evaluate whether the extracted claims accurately and neutrally represent the underlying source text without distortion, exaggeration, or strawman framing.\nFor each claim, state if it is faithful (Yes/No) and provide a refined neutral version if needed."),
    ("human", "Claims to Audit:\n{claims}\n\nSource Research Text:\n{source_text}")
])
claim_fidelity_chain = claim_fidelity_prompt | llm | StrOutputParser()

fact_verifier_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an unbiased fact-checker. Verify the claim below against the provided search evidence.\nClaim: {claim}\n\nEvidence:\n{evidence}\n\nEvaluate the claim based on the evidence. Respond in a clean JSON format (with no markdown code block formatting) containing exactly these three fields:\n- status: 'Verified' | 'Not Verified' | 'Partially Verified'\n- confidence: a number from 0 to 100\n- snippet: a short, specific supporting text snippet from the evidence"),
    ("human", "Verify this claim.")
])
fact_verifier_chain = fact_verifier_prompt | llm | StrOutputParser()

grounding_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a professional research editor. Ground the provided research report with inline citations using numbers like [1], [2], etc., corresponding to the verified evidence.\n\nReport:\n{report}\n\nVerified Evidence:\n{verification_results}\n\nRewrite the report to integrate the inline citations naturally. At the very end of the report, add a 'Citations & Sources' section listing each numbered citation, the source URL, and the exact supporting evidence snippet in the format:\n[1] Source Name (URL)\nEvidence: \"exact snippet\""),
    ("human", "Ground this report.")
])
grounding_chain = grounding_prompt | llm | StrOutputParser()

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


