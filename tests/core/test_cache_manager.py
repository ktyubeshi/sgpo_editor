import json
import pytest
import time
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.models.entry import EntryModel


def make_entry(key, value=None):
    return EntryModel(key=key, msgid=value or f"msgid_{key}", msgstr=f"msgstr_{key}")


@pytest.fixture
def cache_manager(monkeypatch):
    # 設定をテスト用に上書き
    monkeypatch.setattr(
        "sgpo_editor.core.cache_manager.get_cache_config",
        lambda: {
            "COMPLETE_CACHE_MAX_SIZE": 3,
            "FILTER_CACHE_MAX_SIZE": 2,
            "CACHE_ENABLED": True,
            "CACHE_TTL": 0,
            "PREFETCH_ENABLED": True,
            "PREFETCH_SIZE": 2,
        },
    )
    return EntryCacheManager()


def test_lru_eviction(cache_manager):
    # LRU: 3件まで保持、4件目で最古が消える
    cache_manager.set_entry("k0", make_entry("k0"))
    cache_manager.set_entry("k1", make_entry("k1"))
    cache_manager.set_entry("k2", make_entry("k2"))
    # k1, k2にアクセスしてk0はアクセスしない
    _ = cache_manager.get_entry("k1")
    _ = cache_manager.get_entry("k2")
    cache_manager.set_entry("k3", make_entry("k3"))
    print(
        "cache keys after set_entry('k3'):",
        list(cache_manager._complete_cache._cache.keys()),
    )
    # k0が消える（最古）
    assert cache_manager.get_entry("k0") is None
    assert cache_manager.get_entry("k1") is not None
    assert cache_manager.get_entry("k2") is not None
    assert cache_manager.get_entry("k3") is not None


def test_ttl_expiry(monkeypatch):
    monkeypatch.setattr(
        "sgpo_editor.core.cache_manager.get_cache_config",
        lambda: {
            "COMPLETE_CACHE_MAX_SIZE": 3,
            "FILTER_CACHE_MAX_SIZE": 2,
            "CACHE_ENABLED": True,
            "CACHE_TTL": 1,
            "PREFETCH_ENABLED": False,
            "PREFETCH_SIZE": 2,
        },
    )
    cm = EntryCacheManager()
    cm.set_entry("k1", make_entry("k1"))
    assert cm.get_entry("k1") is not None
    time.sleep(1.1)
    assert cm.get_entry("k1") is None


def test_prefetch_entries(cache_manager):
    called = {}

    def fetch_callback(keys):
        called["keys"] = keys
        return {k: make_entry(k) for k in keys}

    keys = ["a", "b"]
    cache_manager.prefetch_entries(keys, fetch_callback)
    assert set(called["keys"]) == set(keys)
    for k in keys:
        assert cache_manager.get_entry(k) is not None


def test_is_key_being_prefetched(cache_manager):
    # プリフェッチ中フラグのテスト
    import threading
    import time

    def fetch_callback(keys):
        time.sleep(0.2)
        return {k: make_entry(k) for k in keys}

    t = threading.Thread(
        target=cache_manager.prefetch_entries, args=(["x"], fetch_callback)
    )
    t.start()
    time.sleep(0.05)
    assert cache_manager.is_key_being_prefetched("x")
    t.join()
    assert not cache_manager.is_key_being_prefetched("x")


def test_invalidate_filter_cache_all(cache_manager):
    # FilterCache
    cond = {"foo": "bar"}
    cache_manager.set_filtered_entries(cond, [make_entry("k2")])
    assert cache_manager.get_filtered_entries(cond) is not None
    cache_manager.invalidate_filter_cache()
    assert cache_manager.get_filtered_entries(cond) is None


def test_invalidate_filter_cache_by_key(cache_manager):
    cond1 = {"foo": "bar"}
    cond2 = {"spam": "eggs"}
    cache_manager.set_filtered_entries(cond1, [make_entry("k1")])
    cache_manager.set_filtered_entries(cond2, [make_entry("k2")])
    assert cache_manager.get_filtered_entries(cond1) is not None
    assert cache_manager.get_filtered_entries(cond2) is not None
    cache_manager.invalidate_filter_cache(json.dumps(cond1, sort_keys=True))
    assert cache_manager.get_filtered_entries(cond1) is None
    # cond2 should remain
    assert cache_manager.get_filtered_entries(cond2) is not None


def test_cache_disable_enable(cache_manager):
    cache_manager.set_entry("k1", make_entry("k1"))
    cache_manager.disable_cache()
    assert cache_manager.get_entry("k1") is None
    cache_manager.enable_cache()
    cache_manager.set_entry("k2", make_entry("k2"))
    assert cache_manager.get_entry("k2") is not None


def test_config_applied(monkeypatch):
    monkeypatch.setattr(
        "sgpo_editor.core.cache_manager.get_cache_config",
        lambda: {
            "COMPLETE_CACHE_MAX_SIZE": 1,
            "FILTER_CACHE_MAX_SIZE": 1,
            "CACHE_ENABLED": True,
            "CACHE_TTL": 0,
            "PREFETCH_ENABLED": False,
            "PREFETCH_SIZE": 1,
        },
    )
    cm = EntryCacheManager()
    cm.set_entry("k1", make_entry("k1"))
    cm.set_entry("k2", make_entry("k2"))
    # max_size=1なのでk1は消える
    assert cm.get_entry("k1") is None
    assert cm.get_entry("k2") is not None
