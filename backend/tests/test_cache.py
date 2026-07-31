import time

from app.cache import _MemoryCache, cache_get_json, cache_set_json, invalidate_public_cache


def test_memory_cache_get_set_roundtrip():
    cache = _MemoryCache()
    cache.set("k1", "v1", ttl=60)
    assert cache.get("k1") == "v1"


def test_memory_cache_expires_after_ttl():
    cache = _MemoryCache()
    cache.set("k1", "v1", ttl=1)
    assert cache.get("k1") == "v1"
    time.sleep(1.2)
    assert cache.get("k1") is None


def test_memory_cache_delete_prefix_only_affects_matching_keys():
    cache = _MemoryCache()
    cache.set("public:1:app", "a", ttl=60)
    cache.set("public:1:items", "b", ttl=60)
    cache.set("public:2:app", "c", ttl=60)

    cache.delete_prefix("public:1:")

    assert cache.get("public:1:app") is None
    assert cache.get("public:1:items") is None
    assert cache.get("public:2:app") == "c"


def test_cache_get_set_json_roundtrip():
    cache_set_json("test:json:key", {"a": 1, "b": [1, 2, 3]})
    assert cache_get_json("test:json:key") == {"a": 1, "b": [1, 2, 3]}


def test_cache_get_json_returns_none_for_missing_key():
    assert cache_get_json("test:json:missing") is None


def test_invalidate_public_cache_only_clears_given_app():
    cache_set_json("public:10:app", {"name": "App 10"})
    cache_set_json("public:11:app", {"name": "App 11"})

    invalidate_public_cache(10)

    assert cache_get_json("public:10:app") is None
    assert cache_get_json("public:11:app") == {"name": "App 11"}
