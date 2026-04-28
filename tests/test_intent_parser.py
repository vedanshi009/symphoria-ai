# tests/test_intent_parser.py
from unittest import result

from src.intent_parser import parse_intent 

def test_lofi_relaxed_intent():
    result = parse_intent("I want something chill and lofi to study to")

    assert isinstance(result["mood_context"], list)
    assert any(m in result["mood_context"] for m in ["chill", "relaxed"])

def test_energy_range_is_tuple():
    result = parse_intent("play something calm")
    lo, hi = result["target_energy_range"]
    assert lo < hi
    assert 0.0 <= lo <= 1.0
    assert 0.0 <= hi <= 1.0