"""Unit tests for Intent Classifier."""
import pytest
from app.routing.intent_router import classify_intent, QueryIntent


def test_intent_policy_list():
    assert classify_intent("What are all the HR policies?") == QueryIntent.POLICY_LIST
    assert classify_intent("give me all policy names") == QueryIntent.POLICY_LIST
    assert classify_intent("what are the 16 HR policies?") == QueryIntent.POLICY_LIST


def test_intent_doc_generation():
    assert classify_intent("give this in a pdf file that i can download it") == QueryIntent.DOCUMENT_GENERATION
    assert classify_intent("download this answer as pdf") == QueryIntent.DOCUMENT_GENERATION


def test_intent_out_of_domain():
    assert classify_intent("how can i make a chatbot like you?") == QueryIntent.OUT_OF_DOMAIN
    assert classify_intent("what is the weather today?") == QueryIntent.OUT_OF_DOMAIN
    assert classify_intent("who won yesterday's match?") == QueryIntent.OUT_OF_DOMAIN


def test_intent_greeting():
    assert classify_intent("hello") == QueryIntent.GREETING
    assert classify_intent("good morning") == QueryIntent.GREETING


def test_intent_casual_chat():
    assert classify_intent("how are you?") == QueryIntent.CASUAL_CHAT
    assert classify_intent("i am bored") == QueryIntent.CASUAL_CHAT
    assert classify_intent("thanks") == QueryIntent.CASUAL_CHAT


def test_intent_follow_up():
    history = [
        {"role": "user", "content": "How can I apply for leave?"},
        {"role": "assistant", "answer": None}
    ]
    assert classify_intent("give me detailed information for it", history=history) == QueryIntent.FOLLOW_UP
