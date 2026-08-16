from app.routing.policy_router import detect_policy
from app.retrieval.retriever import is_out_of_scope, resolve_conversational_context, normalize_query_intent

POLICIES = [
    "Performance Improvement Plan (PIP) Policy",
    "Notice Period Policy",
    "Leave Travel Allowance Policy",
    "India Leave Policy",
    "Shift Allowance Policy",
]


def test_exact_match():
    match = detect_policy("What is the Notice Period Policy for resignation?", POLICIES)
    assert match.matched
    assert match.policy_name == "Notice Period Policy"
    assert match.match_type == "exact"


def test_abbreviation_match():
    match = detect_policy("How long does the PIP process take?", POLICIES)
    assert match.matched
    assert match.policy_name == "Performance Improvement Plan (PIP) Policy"
    assert match.match_type == "abbreviation"


def test_no_policy_named_falls_through_to_cross_policy():
    match = detect_policy("What benefits am I eligible for?", POLICIES)
    assert not match.matched


def test_minor_typo_fuzzy_match():
    match = detect_policy("What does the Notce Period Policy say?", POLICIES)
    assert match.matched
    assert match.policy_name == "Notice Period Policy"
    assert match.match_type in {"fuzzy", "normalized"}


def test_does_not_match_unrelated_policy():
    match = detect_policy("Tell me about shift allowance", POLICIES)
    assert match.matched
    assert match.policy_name == "Shift Allowance Policy"
    assert match.policy_name != "Notice Period Policy"


def test_out_of_scope_detection():
    assert is_out_of_scope("What is the weather today?")
    assert is_out_of_scope("Write Python code for me")
    assert not is_out_of_scope("What is the leave policy?")


def test_conversational_context_resolution():
    history = [{"role": "user", "content": "What is the notice period?"}]
    resolved = resolve_conversational_context("What about probation?", history)
    assert "notice period" in resolved.lower()
    assert "probation" in resolved.lower()


def test_hinglish_normalization():
    norm = normalize_query_intent("leave kitni milti hai?")
    assert "leave policy" in norm.lower()
