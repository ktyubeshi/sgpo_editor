"""
新キャッシュ層（EntryCacheManager, CompleteEntryCache, FilterCache）
設計仕様: 2_2_dbcash_architecture.md に準拠
"""

import threading
from typing import Optional, List, Dict, Any, Set
from collections import OrderedDict
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import (
    EntryModelMap, EntryModelList, FilterConditions
)
import logging
import time
import hashlib
from sgpo_editor.config import get_cache_config

logger = logging.getLogger(__name__)

class CompleteEntryCache:
    """
    完全なEntryModelオブジェクトのLRUキャッシュ
    - key: str → EntryModel
    - LRU+上限
    """
    def __init__(self, max_size: int):
        self._cache: OrderedDict[str, EntryModel] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[EntryModel]:
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                self._cache.move_to_end(key)
            return entry

    def set(self, key: str, entry: EntryModel) -> None:
        with self._lock:
            self._cache[key] = entry
            self._cache.move_to_end(key)
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._cache

class FilterCache:
    """
    フィルタ結果のLRUキャッシュ
    - hash(filter_conditions) → List[EntryModel]
    - LRU+上限
    """
    def __init__(self, max_size: int):
        self._cache: OrderedDict[str, EntryModelList] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()

    def _make_key(self, filter_conditions: FilterConditions) -> str:
        # フィルタ条件のハッシュ化
        return hashlib.sha256(str(filter_conditions).encode()).hexdigest()

    def get(self, filter_conditions: FilterConditions) -> Optional[EntryModelList]:
        key = self._make_key(filter_conditions)
        with self._lock:
            result = self._cache.get(key)
            if result is not None:
                self._cache.move_to_end(key)
            return result

    def set(self, filter_conditions: FilterConditions, entries: EntryModelList) -> None:
        key = self._make_key(filter_conditions)
        with self._lock:
            self._cache[key] = entries
            self._cache.move_to_end(key)
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

class EntryCacheManager:
    def get_filter_cache(self):
        """
        フィルタキャッシュの内容を取得（テスト用・デバッグ用）
        Returns:
            dict: フィルタキャッシュの内容
        """
        return self._filter_cache._cache if hasattr(self, '_filter_cache') else {}
    """
    キャッシュ層の統括管理クラス
    - CompleteEntryCache, FilterCache, プリフェッチ, 無効化ロジック等を統合
    - API: get/set/delete/exists/clear/initialize ほか
    """
    def __init__(self):
        config = get_cache_config()
        self._complete_cache = CompleteEntryCache(config['COMPLETE_CACHE_MAX_SIZE'])
        self._filter_cache = FilterCache(config['FILTER_CACHE_MAX_SIZE'])
        self._lock = threading.RLock()
        self._cache_enabled = config.get('CACHE_ENABLED', True)
        self._ttl = config.get('CACHE_TTL', 0)  # 0=無制限
        self._last_cleared = time.time()

    def get_entry(self, key: str) -> Optional[EntryModel]:
        if not self._cache_enabled:
            return None
        return self._complete_cache.get(key)

    def set_entry(self, key: str, entry: EntryModel) -> None:
        if not self._cache_enabled:
            return
        self._complete_cache.set(key, entry)

    def delete_entry(self, key: str) -> None:
        self._complete_cache.delete(key)

    def clear_all(self) -> None:
        self._complete_cache.clear()
        self._filter_cache.clear()
        self._last_cleared = time.time()

    def get_filtered_entries(self, filter_conditions: FilterConditions) -> Optional[EntryModelList]:
        if not self._cache_enabled:
            return None
        return self._filter_cache.get(filter_conditions)

    def set_filtered_entries(self, filter_conditions: FilterConditions, entries: EntryModelList) -> None:
        if not self._cache_enabled:
            return
        self._filter_cache.set(filter_conditions, entries)

    def clear_filter_cache(self) -> None:
        self._filter_cache.clear()

    def exists_entry(self, key: str) -> bool:
        return self._complete_cache.exists(key)

    def initialize(self) -> None:
        self.clear_all()
        self._cache_enabled = True

    def disable_cache(self) -> None:
        self._cache_enabled = False
        self.clear_all()

    def enable_cache(self) -> None:
        self._cache_enabled = True

    # TTL, プリフェッチ、無効化通知などの詳細ロジックは後続で追加

# 設定取得関数例（config.py 側で実装されている前提）
def get_cache_config() -> Dict[str, Any]:
    # 本来は config.py から取得
    return {
        'COMPLETE_CACHE_MAX_SIZE': 10000,
        'FILTER_CACHE_MAX_SIZE': 100,
        'CACHE_ENABLED': True,
        'CACHE_TTL': 0,
    }
