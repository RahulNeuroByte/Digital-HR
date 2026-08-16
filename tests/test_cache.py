from app.retrieval.cache import SemanticCache
from app.schemas.models import ChatAnswer, Source

def test_semantic_cache_put_get():
    cache = SemanticCache(max_entries=10)
    ans = ChatAnswer(
        answer="The notice period is 3 months.",
        detected_policy="Notice Period Policy",
        sources=[Source(policy_name="Notice Period Policy", document="Notice Period Policy.pdf", page=1)],
        grounded=True,
    )

    # Test cache insertion & lookup
    cache.put("what is the notice period?", "Notice Period Policy", ans)
    cached = cache.get("What is the notice period?", "Notice Period Policy")

    assert cached is not None
    assert cached.answer == "The notice period is 3 months."
    assert cached.total_latency_ms < 20.0

def test_semantic_cache_no_answer_not_cached():
    cache = SemanticCache(max_entries=10)
    no_ans = ChatAnswer(answer="No context", no_answer=True, grounded=False)

    cache.put("unknown query", None, no_ans)
    assert cache.get("unknown query", None) is None
