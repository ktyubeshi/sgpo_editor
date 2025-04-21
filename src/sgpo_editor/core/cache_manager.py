"""
新キャッシュ層（EntryCacheManager, CompleteEntryCache, FilterCache）
設計仕様: 2_2_dbcash_architecture.md に準拠
"""

import threading
from typing import Optional, Dict, Callable, Set
from collections import OrderedDict
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import EntryModelList, FilterConditions
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
        return self._filter_cache._cache if hasattr(self, "_filter_cache") else {}

    """
    キャッシュ層の統括管理クラス
    - CompleteEntryCache, FilterCache, プリフェッチ, 無効化ロジック等を統合
    - API: get/set/delete/exists/clear/initialize ほか
    """

    def __init__(self):
        config = get_cache_config()
        self._complete_cache = CompleteEntryCache(config["COMPLETE_CACHE_MAX_SIZE"])
        self._filter_cache = FilterCache(config["FILTER_CACHE_MAX_SIZE"])
        self._lock = threading.RLock()
        self._cache_enabled = config.get("CACHE_ENABLED", True)
        self._ttl = config.get("CACHE_TTL", 0)  # 0=無制限
        self._prefetch_enabled = config.get("PREFETCH_ENABLED", False)
        self._prefetch_size = config.get("PREFETCH_SIZE", 100)
        self._last_cleared = time.time()
        self._entry_timestamps: Dict[str, float] = {}  # TTL用
        self._prefetching_keys: Set[str] = set()  # プリフェッチ中のキー管理

    def get_entry(self, key: str) -> Optional[EntryModel]:
        if not self._cache_enabled:
            return None
        entry = self._complete_cache.get(key)
        if entry is not None and self._ttl > 0:
            ts = self._entry_timestamps.get(key)
            if ts is not None and (time.time() - ts > self._ttl):
                self.delete_entry(key)
                return None
        return entry

    def set_entry(self, key: str, entry: EntryModel) -> None:
        if not self._cache_enabled:
            return
        self._complete_cache.set(key, entry)
        if self._ttl > 0:
            self._entry_timestamps[key] = time.time()

    def delete_entry(self, key: str) -> None:
        self._complete_cache.delete(key)
        self._entry_timestamps.pop(key, None)

    def clear_all(self) -> None:
        self._complete_cache.clear()
        self._filter_cache.clear()
        self._entry_timestamps.clear()
        self._last_cleared = time.time()

    def get_filtered_entries(
        self, filter_conditions: FilterConditions
    ) -> Optional[EntryModelList]:
        if not self._cache_enabled:
            return None
        # TTLはフィルタキャッシュには未適用（必要なら拡張）
        return self._filter_cache.get(filter_conditions)

    def set_filtered_entries(
        self, filter_conditions: FilterConditions, entries: EntryModelList
    ) -> None:
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

    # --- 追加: プリフェッチAPI雛形 ---
    def prefetch_entries(
        self,
        keys: list[str],
        fetch_callback: Callable[[list[str]], Dict[str, EntryModel]],
    ) -> None:
        """
        指定したキーのエントリをDBから先読みしキャッシュする
        Args:
            keys: 先読みするエントリキーのリスト
            fetch_callback: DBからエントリを取得するコールバック関数
        """
        if not self._prefetch_enabled or not fetch_callback:
            return
        # 取得対象を上限件数に制限
        keys_to_fetch = keys[: self._prefetch_size]
        # プリフェッチフラグをセット
        for k in keys_to_fetch:
            self._prefetching_keys.add(k)
        try:
            entries_map = fetch_callback(keys_to_fetch)
            # キャッシュに設定
            for k, entry in entries_map.items():
                self.set_entry(k, entry)
        finally:
            # プリフェッチフラグをクリア
            for k in keys_to_fetch:
                self._prefetching_keys.discard(k)

    def is_key_being_prefetched(self, key: str) -> bool:
        """
        指定キーがプリフェッチ中か確認する
        """
        return key in self._prefetching_keys

    # --- 追加: DB更新時の自動無効化 ---
    def invalidate_entry(self, key: str) -> None:
        """
        指定キーのキャッシュを無効化（DB update_hook等から呼び出し）
        """
        self.delete_entry(key)

    def invalidate_filter_cache(self) -> None:
        """
        フィルタキャッシュ全体を無効化（DB更新時など）
        """
        self.clear_filter_cache()
