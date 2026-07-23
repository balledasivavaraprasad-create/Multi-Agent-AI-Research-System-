import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents import claim_fidelity_prompt

def test_claim_fidelity_prompt_formatting():
    formatted = claim_fidelity_prompt.invoke({
        "claims": "1. AI reduces research latency by 50%.",
        "source_text": "Study indicates automated research tools reduce latency significantly."
    })
    messages = formatted.to_messages()
    assert len(messages) == 2
    assert "claim fidelity auditor" in messages[0].content.lower()
    assert "AI reduces research latency" in messages[1].content
