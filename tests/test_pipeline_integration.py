import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipeline import run_research_pipeline

@patch('time.sleep')
@patch('pipeline.invoke_llm_chain')
@patch('pipeline.web_search')
def test_pipeline_execution_structure(mock_web_search, mock_invoke_llm, mock_sleep):

    # Mock LLM responses
    mock_invoke_llm.side_effect = [
        "1. What is quantum computing?\n2. What are its applications?", # planner
        "1. Quantum computers utilize qubits.", # claim extraction
        "Claim 1: Accurate (Fidelity: 90%)", # claim fidelity check
        '{"status": "Verified", "confidence": 90, "snippet": "Qubits allow parallel state processing."}', # verifier
        "Quantum computing enables exponential processing speedups.", # multi-reader analysis
        "Contrarian view: Error rates remain high.", # contrarian
        "# Quantum Computing Overview\n\nQuantum computing is an emerging field.", # writer draft
        "Score: 8.5/10\nStrengths: Clear and well-structured.", # critic
        "# Quantum Computing Overview [1]\n\nQuantum computing uses qubits.\n\nCitations:\n[1] Nature (https://nature.com)" # grounded final report
    ]

    mock_web_search.invoke.return_value = (
        "Title : Quantum Basics\n"
        "URL : https://nature.com/articles/quantum\n"
        "Snippet : Qubits allow parallel state processing in quantum mechanics.\n"
    )

    result = run_research_pipeline("Quantum Computing Advances")
    
    assert result["status"] == "success"
    assert result["topic"] == "Quantum Computing Advances"
    assert "results" in result
    assert "claim_fidelity" in result["results"]
    assert "metadata" in result
    assert "metrics" in result["metadata"]
    assert "cost_usd" in result["metadata"]["metrics"]
    assert result["metadata"]["metrics"]["cost_usd"] >= 0.0
