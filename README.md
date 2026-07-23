# ARCS — Siva's Advanced Research & Curation System

A multi-agent research pipeline with fact verification, multi-factor source scoring, and an interactive web interface, created and maintained by **Siva**. This system orchestrates specialized agents in a 9-stage workflow to conduct structured research, verify claim fidelity, cross-corroborate evidence, and compose grounded reports with inline citations.

## System Architecture & Features

### 1. Parallel Multi-Query Planning
- **Planner Agent**: Generates 5–8 distinct, targeted research questions for the topic.
- **Parallel Search Execution**: Executes web searches for queries concurrently using Python `ThreadPoolExecutor`, reducing pipeline latency.

### 2. Claim Fidelity & Verification Rigor
- **Claim Extractor Agent**: Pulls 3–5 core factual statements from gathered research.
- **Claim Fidelity Check**: Runs an independent claim-fidelity evaluation to ensure extracted claims accurately and neutrally represent underlying source text without distortion.
- **Evidence Verification Agent**: Searches and parses evidence for each claim in parallel. Returns structured JSON verdicts containing: verification status (`Verified`, `Partially Verified`, `Not Verified`), verification confidence, and matching source snippets.

### 3. Multi-Factor Source Trust Scoring
Calculates a multi-factor transparent trust score (0–10) with detailed breakdowns exposed in the dashboard:
- **Domain Tier (40%)**: Primary government (`.gov`), academic institutions (`.edu`), scientific repositories (`arxiv.org`, `ieee.org`), and major news agencies.
- **Recency Decay (20%)**: Evaluates article publication dates, decaying scores for articles >2 years old.
- **Cross-Corroboration (20%)**: Boosts confidence when independent domains report matching factual claims.
- **Primary Citation Check (20%)**: Outbound reference heuristics evaluating links to `.gov`, `.edu`, `arxiv.org`, or `doi.org`.

### 4. Google Gemini Multi-Model & Key-Rotation Failover
To reliably support 50–100+ research runs per day without hitting daily token limits (RPD) or rate limits (RPM), `agents.py` dynamically builds a multi-tier fallback chain across 5 Google Gemini model variants and rotates across multiple Google API keys (`GOOGLE_API_KEY`, `GOOGLE_API_KEY_2`, `GOOGLE_API_KEY_3`, `GOOGLE_API_KEY_4`):
- **Model Fallback Tiers**: `gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-2.0-flash-lite` → `gemini-1.5-flash` → `gemini-1.5-flash-8b`.
- **Automatic Key Rotation**: Switches to auxiliary API keys seamlessly if a primary key encounters rate limits or quota boundaries.



### 5. Citation Grounding
- **Grounding Agent**: Injects inline numbered references (`[1]`, `[2]`) into the report and outputs a `Citations & Sources` bibliography matching URLs with validated snippets.

### 6. Observability Dashboard & Cost Control
- Displays overall **Source Quality**, **Fact-Check Accuracy**, and **Estimated USD Cost** per run.
- Profiles latencies across all 9 pipeline stages:
  1. `Planner`: Planning queries
  2. `Research`: Parallel searching
  3. `Claim Extraction`: Extracting facts
  4. `Claim Fidelity Check`: Neutrality audit
  5. `Fact Verification`: Parallel verification
  6. `Analysis & Synthesis`: Synthesizing insights
  7. `Writing`: Composing draft
  8. `Quality Loop`: Iterative critic refinement
  9. `Grounded Citations`: Grounding citations

### 7. MongoDB User Auth & Research History
- **JWT Auth & Password Security**: Secure user registration and login endpoints utilizing `bcrypt` password hashing and stateless JSON Web Tokens (JWT).
- **Persistent Research History**: Automatically saves completed research runs to MongoDB.
- **Mock Auth Fallback**: Automatic mock database mode if MongoDB is not connected, ensuring local/production servers start up cleanly.

---

## Cost Controls & Rate Limits

- **Per-Run Cost Estimator**: Tracks exact input/output tokens and Tavily search API calls ($0.003/search). Calculates total estimated run cost ($X.XX) displayed directly in the dashboard.
- **Hard Safety Caps**:
  - Max 4 parallel search queries per run
  - Max 4 claims extracted and verified per run
  - Max 3 critic loop revision iterations

---

## Project Structure

```
Multi-Agent-System/
├── frontend/               # React (Vite) Frontend Web App
│   ├── src/
│   │   ├── App.jsx         # UI, circular progress, dashboard & print/copy
│   │   └── index.css       # Styling and typography
│   └── package.json
├── tests/                  # Unit and integration test suite
│   ├── test_source_scoring.py
│   ├── test_verification_parsing.py
│   ├── test_claim_fidelity.py
│   └── test_pipeline_integration.py
├── agents.py               # Gemini & Cross-Vendor prompt chains and fallbacks
├── tools.py                # Tavily search wrapper, scraper, and multi-factor source scoring
├── pipeline.py             # Local pipeline execution CLI & cost tracking
├── server.py               # Flask backend SSE streaming server
├── Dockerfile              # Docker container setup
├── requirements.txt        # Python backend dependencies (includes pytest)
└── .env                    # Environment keys
```

---

## Testing

Run the unit and integration test suite via `pytest`:

```bash
pytest tests/
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
   GROQ_API_KEY=gsk_your_groq_key             # Optional: Cross-vendor failover
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

---

## License

All Rights Reserved — For Demonstration and Portfolio Purposes.  
Copyright © 2026 Siva.

This software and associated documentation files are provided for demonstration purposes. Contact the repository owner for permissions or reuse.

