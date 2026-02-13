from src.modules.ai_cache import TradeAICache


def test_ai_cache_roundtrip_and_key_contract(tmp_path):
    cache_path = tmp_path / "cache.json"
    cache = TradeAICache(cache_path=str(cache_path))

    key = cache.build_cache_key("cba_v1", "abc123hash", "A:p1__B:p2")
    assert key == "cba_v1|abc123hash|A:p1__B:p2"

    assert cache.get(key) is None
    cache.set(key, {"text": "hello"})
    assert cache.get(key) == {"text": "hello"}

    cache2 = TradeAICache(cache_path=str(cache_path))
    assert cache2.get(key) == {"text": "hello"}
