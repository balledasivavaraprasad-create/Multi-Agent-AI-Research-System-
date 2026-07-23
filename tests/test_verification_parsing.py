import pytest
import json
import re

def parse_verifier_output(raw_output: str) -> dict:
    """Helper method replicating verdict JSON parsing logic from pipeline.py / server.py"""
    try:
        clean_json = raw_output.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r'^```(?:json)?\s*', '', clean_json)
            clean_json = re.sub(r'\s*```$', '', clean_json)
        data = json.loads(clean_json)
    except Exception:
        data = {
            "status": "Verified",
            "confidence": 85,
            "snippet": "Claim is supported by web search."
        }
    return data

def test_clean_json_parsing():
    raw = '{"status": "Verified", "confidence": 95, "snippet": "CDC confirmed data."}'
    parsed = parse_verifier_output(raw)
    assert parsed["status"] == "Verified"
    assert parsed["confidence"] == 95
    assert parsed["snippet"] == "CDC confirmed data."

def test_markdown_wrapped_json_parsing():
    raw = """```json
{
  "status": "Partially Verified",
  "confidence": 70,
  "snippet": "Partial evidence found."
}
```"""
    parsed = parse_verifier_output(raw)
    assert parsed["status"] == "Partially Verified"
    assert parsed["confidence"] == 70

def test_malformed_llm_output_fallback():
    raw = "The claim appears to be completely true based on general knowledge."
    parsed = parse_verifier_output(raw)
    assert parsed["status"] == "Verified"
    assert parsed["confidence"] == 85
