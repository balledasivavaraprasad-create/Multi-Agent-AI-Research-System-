---
title: AdvancedMultiAgentSystem
emoji: 🌖
colorFrom: green
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

# ARCS — Siva's Advanced Research & Curation System

A sophisticated, enterprise-grade multi-agent AI research pipeline with an elegant web interface, created and maintained by **Siva**. This system orchestrates specialized agents in an 8-stage workflow to conduct comprehensive research, perform parallel fact verification, score source quality, and compose grounded reports with inline citations.

## System Architecture & Features

### 1. Parallel Multi-Query Planning
- **Planner Agent**: Generates 5–8 distinct, targeted research questions for the topic.
- **Parallel Search execution**: Executes web searches for the queries concurrently using Python `ThreadPoolExecutor`, reducing pipeline latency.

### 2. Deep Fact Verification & Claim Extraction
- **Claim Extractor Agent**: Pulls 3–5 core factual statements from gathered research.
- **Evidence Verification Agent**: Searches and parses evidence for each claim in parallel. Returns structured JSON verdicts containing: verification status (`Verified`, `Partially Verified`, `Not Verified`), verification confidence, and matching source snippets.

### 3. Source Trust Ranking
- Rates sources based on domain credibility:
  - **10/10**: Government portals (`.gov`, `.gov.in`)
  - **9/10**: Academic platforms (`.edu`, `arxiv.org`, `ieee.org`)
  - **8/10**: Top-tier global news (Reuters, Bloomberg, BBC, NYT)
  - **7/10**: Wikipedia
  - **5/10**: Technical blogs (`medium.com`, `blogspot.com`)
  - **4/10**: General sites
- Calculates the `overall_source_quality` as the weighted average score of all consulted sources.

### 4. Perplexity-Style Citation Grounding
- **Grounding Agent**: Injects inline numbered references (`[1]`, `[2]`) into the report and outputs a `Citations & Sources` bibliography matching URLs with validated snippets.

### 5. Observability Dashboard
- Displays overall **Source Quality** and **Fact-Check Accuracy**.
- Profiles latencies across all 8 pipeline stages in a horizontal bar chart:
  1. `Planner`: Planning queries
  2. `Research`: Parallel searching
  3. `Claim Extraction`: Extracting facts
  4. `Fact Verification`: Parallel verification
  5. `Analysis & Synthesis`: Synthesizing insights
  6. `Writing`: Composing draft
  7. `Quality Loop`: Iterative critic refinement
  8. `Grounded Citations`: Grounding citations

### 6. Interactive Frontend Actions
- **Circular Progress Wheel**: Displays real-time progress percentages (0-100%) for the active agent stages.
- **Copy**: Copies the report text directly to your clipboard.
- **PDF Export**: Generates and formats a print-ready document to save as PDF.

### 7. MongoDB User Auth & Research History
- **JWT Auth & Password Security**: Secure user registration and login endpoints utilizing `bcrypt` password hashing and stateless JSON Web Tokens (JWT).
- **Persistent Research History**: Automatically saves completed research runs to MongoDB.
- **Sleek Split-Screen Sidebar**: Houses a user profile card, a query reset function, and a scrollable recent queries feed. Clicking any item instantly loads the saved results from MongoDB without re-running.
- **Mock Auth Fallback**: Automatic mock database mode if MongoDB is not connected, ensuring local/production servers start up cleanly.

---

## Project Structure

```
Multi-Agent-System/
├── frontend/               # React (Vite) Frontend Web App
│   ├── src/
│   │   ├── App.jsx         # UI, circular progress, dashboard & print/copy
│   │   └── index.css       # Clean styling and professional sans-serif typography
│   └── package.json
├── agents.py               # Core Gemini Prompt chains and Fallback configuration
├── tools.py                # Tavily search wrapper, scraper, and source trust scoring
├── pipeline.py             # Local pipeline execution CLI
├── server.py               # Flask backend SSE streaming server
├── Dockerfile              # Docker container setup
├── requirements.txt        # Python backend dependencies
└── .env                    # Environment keys (Google & Tavily API keys)
```

---

## Setup Instructions

### Backend (Python Flask Server)

1. **Install Dependencies**:
   ```bash
   cd Multi-Agent-System
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure Environment Keys**:
   Create a `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
   Add your keys:
   ```env
    GOOGLE_API_KEY=your_google_gemini_key
    TAVILY_API_KEY=your_tavily_search_key
    MONGODB_URI=mongodb://localhost:27017/arcs  # Optional: defaults to local MongoDB
    JWT_SECRET=your_jwt_secret_key             # Optional: defaults to secure default
    ```

3. **Run Backend Server**:
   ```bash
   python server.py
   ```

4. **Verify Health**:
   ```bash
   curl http://localhost:7860/api/health
   ```

---

### Frontend (React + Vite App)

1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start Dev Server**:
   ```bash
   npm run dev
   ```

3. **Production Build**:
   ```bash
   npm run build
   ```

---

## Deployment Configuration

- **Frontend Deployment**: Configured for **Vercel** with a clean Vite build script.
- **Backend Deployment**: Ready for **Hugging Face Spaces** or **Render** utilizing the configured `Dockerfile` and `render.yaml`.

---

## Technology Stack

- **Model Stack**: Google Gemini 2.5 Flash (with automatic failover to 2.0 Flash & Gemini Flash Lite).
- **Orchestration**: LangChain, Python Concurrent Futures.
- **Search & Scraping**: Tavily Client, BeautifulSoup4, Requests.
- **Frontend Framework**: React 18, Vite, Framer Motion, Lucide Icons, React Markdown.

---

## License

Proprietary — All Rights Reserved.  
Copyright © 2026 Siva.

This software and all associated documentation files are the private, proprietary property of Siva. Unauthorized copying, distribution, modification, or usage of this codebase is strictly prohibited.
