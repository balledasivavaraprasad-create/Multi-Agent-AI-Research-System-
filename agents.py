# Copyright (c) 2026 Siva. All rights reserved.
# This software and associated documentation files are the proprietary property of Siva.
# Unauthorized copying, distribution, or modification is strictly prohibited.

import os
import sys
from dotenv import load_dotenv

# Try importing LangChain modules, providing clean errors if not installed
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

google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key or google_api_key.strip() == "":
    print("\n⚠️ WARNING: GOOGLE_API_KEY is not set or is empty in your environment variables.")
    print("Please copy .env.example to .env and configure your GOOGLE_API_KEY.")
    print("Using 'placeholder_key' fallback to prevent import crashes.\n")
    google_api_key = "placeholder_key"

# Initialize Google Gemini model with automatic fallbacks to bypass daily request limits on free keys
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=google_api_key,
    temperature=0,
    max_retries=2,
    timeout=60,
).with_fallbacks([
    ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=google_api_key,
        temperature=0,
        max_retries=2,
        timeout=60,
    ),
    ChatGoogleGenerativeAI(
        model="gemini-flash-lite-latest",
        google_api_key=google_api_key,
        temperature=0,
        max_retries=2,
        timeout=60,
    )
])

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
        'full': 'Multi-Source Research',
        'desc': 'Gathering top-ranked sources comprehensively',
        'chain': None,
    },
    {
        'id': 'factcheck',
        'num': '03',
        'label': 'Verification',
        'full': 'Fact Checker Agent',
        'desc': 'Validating claims, statistics, and sources',
        'chain': fact_checker_chain,
    },
    {
        'id': 'analysis',
        'num': '04',
        'label': 'Analysis',
        'full': 'Multi-Source Analysis',
        'desc': 'Extracting insights with source mapping',
        'chain': multi_reader_chain,
    },
    {
        'id': 'contrarian',
        'num': '05',
        'label': 'Perspective',
        'full': 'Contrarian Agent',
        'desc': 'Challenging assumptions and finding gaps',
        'chain': contrarian_chain,
    },
    {
        'id': 'writer',
        'num': '06',
        'label': 'Writing',
        'full': 'Writer Agent',
        'desc': 'Composing report with citations',
        'chain': writer_chain,
    },
    {
        'id': 'critic_loop',
        'num': '07',
        'label': 'Quality Loop',
        'full': 'Critic & Revision',
        'desc': 'Iterative refinement (max 3 iterations)',
        'chain': critic_chain,
    },
    {
        'id': 'confidence',
        'num': '08',
        'label': 'Confidence',
        'full': 'Citations & Score',
        'desc': 'Generate references and quality score',
        'chain': confidence_chain,
    }
]

STAGE_CONFIGS = {stage['id']: stage for stage in STAGES}

