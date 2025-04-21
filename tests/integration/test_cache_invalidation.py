import pytest
from unittest.mock import MagicMock

from src.sgpo_editor.models.database import InMemoryEntryStore
from src.sgpo_editor.core.database_accessor import DatabaseAccessor
from src.sgpo_editor.core.cache_manager import EntryCacheManager


@pytest.fixture
def setup_db_and_cache():
    # インメモリDBとアクセサ、キャッシュマネージャをセットアップ
    db = InMemoryEntryStore()
    accessor = DatabaseAccessor(db)
    cache_manager = EntryCacheManager()
    return db, accessor, cache_manager


def test_db_update_triggers_cache_invalidation(setup_db_and_cache):
    db, accessor, cache_manager = setup_db_and_cache

    # invalidate_entry, invalidate_filter_cacheをモック
    cache_manager.invalidate_entry = MagicMock()
    cache_manager.invalidate_filter_cache = MagicMock()

    # update hookをキャッシュマネージャのinvalidate_xxxに接続
    def update_hook(type, db_name, table_name, rowid):
        if table_name == "entries":
            cache_manager.invalidate_entry(rowid)
            cache_manager.invalidate_filter_cache()

    db.set_update_hook(update_hook)

    # エントリ追加
    entry = {"key": "test1", "msgid": "msg1", "msgstr": "str1"}
    db.add_entry(entry)
    # INSERTでinvalidate_entry/invalidate_filter_cacheが呼ばれるか
    assert cache_manager.invalidate_entry.called
    assert cache_manager.invalidate_filter_cache.called
    cache_manager.invalidate_entry.reset_mock()
    cache_manager.invalidate_filter_cache.reset_mock()

    # エントリ更新
    db.update_entry("test1", {"msgstr": "updated"})
    assert cache_manager.invalidate_entry.called
    assert cache_manager.invalidate_filter_cache.called
    cache_manager.invalidate_entry.reset_mock()
    cache_manager.invalidate_filter_cache.reset_mock()

    # エントリ削除
    db.delete_entry("test1")
    assert cache_manager.invalidate_entry.called
    assert cache_manager.invalidate_filter_cache.called
