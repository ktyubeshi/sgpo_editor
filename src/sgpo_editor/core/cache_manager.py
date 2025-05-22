"""エントリキャッシュ管理モジュール

このモジュールは、POエントリのキャッシュを管理するためのクラスを提供します。
キャッシュの保存、取得、無効化などの機能を一元管理し、ViewerPOFileクラスの責務を軽減します。

キャッシュシステムの概要:
1. 完全なエントリキャッシュ: データベースから取得した完全なEntryModelオブジェクトを保持
2. 基本情報キャッシュ: 表示に必要な最小限の情報のみを持つEntryModelオブジェクトを保持
3. フィルタ結果キャッシュ: 特定のフィルタ条件に対する結果リストを保持

これらのキャッシュは、ViewerPOFileクラスとDatabaseAccessorクラスと連携して動作し、
データベースアクセスを最小限に抑えることでパフォーマンスを向上させます。

最適化機能:
1. 使用頻度ベースのキャッシュ保持: 頻繁にアクセスされるエントリを優先的に保持
2. キャッシュサイズの自動調整: メモリ使用量に基づいてキャッシュサイズを動的に調整
3. 非同期プリフェッチ: バックグラウンドでの先読みによるUI応答性の向上
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from collections import Counter, OrderedDict
from typing import Callable, Dict, List, Optional, Set, cast

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import (
    EntryModelMap, 
    EntryModelList, 
    CachePerformance, 
    FilterConditions,
    CacheEfficiency
)

logger = logging.getLogger(__name__)

def get_cache_config() -> Dict[str, any]:
    return {
        "COMPLETE_CACHE_MAX_SIZE": 1000,
        "FILTER_CACHE_MAX_SIZE": 1000,
        "CACHE_ENABLED": True,
        "CACHE_TTL": 0,
        "PREFETCH_ENABLED": True,
        "PREFETCH_SIZE": 50,
    }

class _LRUCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self._cache = OrderedDict()
    def set(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)
    def get(self, key):
        val = self._cache.get(key)
        if val is not None:
            self._cache.move_to_end(key)
        return val
    def delete(self, key):
        self._cache.pop(key, None)
    def clear(self):
        self._cache.clear()

class EntryCacheManager:
    """POエントリのキャッシュを管理するクラス

    このクラスは、POエントリの各種キャッシュを管理し、キャッシュの一貫性を保つための
    機能を提供します。主に以下の3種類のキャッシュを管理します：

    1. complete_entry_cache: 完全なEntryModelオブジェクトのキャッシュ
       - 用途: エントリの詳細情報が必要な場合（編集時など）に使用
       - キー: エントリのキー（通常は位置を表す文字列）
       - 値: 完全なEntryModelオブジェクト（すべてのフィールドを含む）

    2. entry_basic_info_cache: 基本情報のみのEntryModelオブジェクトのキャッシュ
       - 用途: エントリリスト表示など、基本情報のみが必要な場合に使用
       - キー: エントリのキー
       - 値: 基本情報のみを含むEntryModelオブジェクト（msgid, msgstr, fuzzy, obsoleteなど）

    3. filtered_entries_cache: フィルタ結果のキャッシュ
       - 用途: 同じフィルタ条件での再検索を高速化
       - キー: フィルタ条件を表す文字列（_filtered_entries_cache_key）
       - 値: フィルタ条件に一致するEntryModelオブジェクトのリスト

    キャッシュの連携方法:
    - ViewerPOFileクラスはget_entry_by_keyなどのメソッドでキャッシュを参照
    - エントリが更新されると、update_entry_in_cacheメソッドで関連するすべてのキャッシュを更新
    - フィルタ条件が変更されると、set_force_filter_updateメソッドでフィルタキャッシュを無効化
    - ファイル読み込み時などは、clear_all_cacheメソッドですべてのキャッシュをクリア

    最適化機能:
    - 使用頻度ベースのキャッシュ保持: アクセス頻度の高いエントリを優先的に保持
    - キャッシュサイズの自動調整: メモリ使用量に基づいてキャッシュサイズを動的に調整
    - 非同期プリフェッチ: バックグラウンドでの先読みによるUI応答性の向上
    """

    DEFAULT_MAX_CACHE_SIZE = 10000
    DEFAULT_LRU_SIZE = 1000
    PREFETCH_BATCH_SIZE = 50

    def __init__(self):
        """キャッシュマネージャの初期化

        3種類のキャッシュとそれらの状態を管理するフラグを初期化します。
        """
        # 完全なEntryModelオブジェクトのキャッシュ（key→EntryModelのマップ）
        # 用途: エントリの詳細表示や編集時に使用
        self._complete_entry_cache: EntryModelMap = {}

        # 基本情報のみのキャッシュ（key→基本情報EntryModelのマップ）
        # 用途: エントリリスト表示など、基本情報のみが必要な場合に使用
        self._entry_basic_info_cache: EntryModelMap = {}

        # フィルタ結果のキャッシュ（フィルタ条件に合致するエントリのリスト）
        # 用途: 同じフィルタ条件での再検索を高速化
        self._filtered_entries_cache: EntryModelList = []

        # フィルタキャッシュのキー（フィルタ条件を表す文字列）
        # 用途: 現在のフィルタ条件を識別し、キャッシュヒットを判定
        self._filtered_entries_cache_key: str = ""

        # キャッシュ有効フラグ（Falseの場合は常にデータベースから取得）
        # 用途: デバッグ時やメモリ使用量を抑えたい場合にキャッシュを無効化
        self._cache_enabled: bool = True

        # フィルタ更新フラグ（Trueの場合はフィルタ結果を強制的に再計算）
        # 用途: エントリ更新後など、キャッシュが古くなった場合に強制更新
        self._force_filter_update: bool = False

        # パフォーマンス計測用のカウンター
        self._complete_cache_hits: int = 0
        self._complete_cache_misses: int = 0
        self._basic_cache_hits: int = 0
        self._basic_cache_misses: int = 0
        self._filter_cache_hits: int = 0
        self._filter_cache_misses: int = 0

        # 時間計測用の変数
        self._last_performance_log_time: float = time.time()

        # ログ間隔（秒）- デフォルトは60秒
        self._performance_log_interval: int = 60

        self._access_counter: Counter = Counter()  # キーごとのアクセス回数
        self._last_access_time: Dict[str, float] = {}  # キーごとの最終アクセス時間
        
        self._max_cache_size: int = self.DEFAULT_MAX_CACHE_SIZE
        self._lru_size: int = self.DEFAULT_LRU_SIZE
        
        self._prefetch_lock = threading.RLock()
        self._prefetch_queue: Set[str] = set()
        self._prefetch_in_progress: bool = False
        # プリフェッチ中のキーを追跡するセット
        self._keys_being_prefetched: Set[str] = set()
        
        self._row_key_map: Dict[int, str] = {}
        # 逆引き用マップを追加
        self._key_row_map: Dict[str, int] = {}

        # キャッシュ設定
        config = get_cache_config()
        self._cache_enabled = config["CACHE_ENABLED"]
        self._cache_ttl = config["CACHE_TTL"]
        self._max_cache_size = config["COMPLETE_CACHE_MAX_SIZE"]
        self._prefetch_enabled = config["PREFETCH_ENABLED"]
        self._prefetch_batch_size = config["PREFETCH_SIZE"]

        # LRU キャッシュとタイムスタンプ
        self._complete_cache = _LRUCache(self._max_cache_size)
        self._entry_timestamps: Dict[str, float] = {}

        # フィルタキャッシュ
        self._filter_cache = _LRUCache(config["FILTER_CACHE_MAX_SIZE"])  # ToDo Phase 1: LRUCacheに更新

        logger.debug("EntryCacheManager: 初期化完了")

    def clear_all_cache(self) -> None:
        """すべてのキャッシュをクリアする

        すべてのキャッシュを無効化し、フィルタ結果もクリアします。
        ファイルの再読み込みや大きな変更があった場合に呼び出されます。
        """
        logger.debug("EntryCacheManager.clear_all_cache: すべてのキャッシュをクリア")
        self._complete_entry_cache.clear()
        self._entry_basic_info_cache.clear()
        self._filtered_entries_cache = []
        self._filtered_entries_cache_key = ""
        self._force_filter_update = True  # 次回のフィルタ処理で強制的に更新

        # パフォーマンスカウンターもリセット
        self._reset_performance_counters()

    def _reset_performance_counters(self) -> None:
        """パフォーマンス計測用カウンターをリセットする"""
        self._complete_cache_hits = 0
        self._complete_cache_misses = 0
        self._basic_cache_hits = 0
        self._basic_cache_misses = 0
        self._filter_cache_hits = 0
        self._filter_cache_misses = 0
        self._last_performance_log_time = time.time()

    def set_performance_log_interval(self, seconds: int) -> None:
        """パフォーマンスログの出力間隔を設定する

        Args:
            seconds: ログ出力間隔（秒）
        """
        self._performance_log_interval = max(1, seconds)  # 最小1秒
        logger.debug(
            f"パフォーマンスログ間隔を{self._performance_log_interval}秒に設定"
        )

    def _check_and_log_performance(self) -> None:
        """パフォーマンス指標をチェックし、必要に応じてログに出力する"""
        current_time = time.time()
        if (
            current_time - self._last_performance_log_time
            >= self._performance_log_interval
        ):
            self._log_cache_performance()
            self._last_performance_log_time = current_time

    def _log_cache_performance(self) -> None:
        """キャッシュのパフォーマンス指標をログに出力する"""
        # 完全キャッシュのヒット率
        complete_total = self._complete_cache_hits + self._complete_cache_misses
        complete_hit_rate = (
            0.0
            if complete_total == 0
            else (self._complete_cache_hits / complete_total * 100)
        )

        # 基本情報キャッシュのヒット率
        basic_total = self._basic_cache_hits + self._basic_cache_misses
        basic_hit_rate = (
            0.0 if basic_total == 0 else (self._basic_cache_hits / basic_total * 100)
        )

        # フィルタキャッシュのヒット率
        filter_total = self._filter_cache_hits + self._filter_cache_misses
        filter_hit_rate = (
            0.0 if filter_total == 0 else (self._filter_cache_hits / filter_total * 100)
        )

        # キャッシュサイズ
        complete_size = len(self._complete_entry_cache)
        basic_size = len(self._entry_basic_info_cache)

        logger.info(
            f"キャッシュパフォーマンス指標:\n"
            f"  完全キャッシュ: {complete_hit_rate:.1f}% ヒット ({self._complete_cache_hits}/{complete_total}), サイズ: {complete_size}\n"
            f"  基本情報キャッシュ: {basic_hit_rate:.1f}% ヒット ({self._basic_cache_hits}/{basic_total}), サイズ: {basic_size}\n"
            f"  フィルタキャッシュ: {filter_hit_rate:.1f}% ヒット ({self._filter_cache_hits}/{filter_total})"
        )

    def get_cache_performance(self) -> CachePerformance:
        """キャッシュのパフォーマンス指標を取得する

        Returns:
            CachePerformance: キャッシュパフォーマンス指標を含む辞書
        """
        # 完全キャッシュのヒット率
        complete_total = self._complete_cache_hits + self._complete_cache_misses
        complete_hit_rate = (
            0.0
            if complete_total == 0
            else (self._complete_cache_hits / complete_total * 100)
        )

        # 基本情報キャッシュのヒット率
        basic_total = self._basic_cache_hits + self._basic_cache_misses
        basic_hit_rate = (
            0.0 if basic_total == 0 else (self._basic_cache_hits / basic_total * 100)
        )

        # フィルタキャッシュのヒット率
        filter_total = self._filter_cache_hits + self._filter_cache_misses
        filter_hit_rate = (
            0.0 if filter_total == 0 else (self._filter_cache_hits / filter_total * 100)
        )

        return cast(CachePerformance, {
            "complete_cache": {
                "hits": self._complete_cache_hits,
                "misses": self._complete_cache_misses,
                "hit_rate": complete_hit_rate,
                "size": len(self._complete_entry_cache),
            },
            "basic_cache": {
                "hits": self._basic_cache_hits,
                "misses": self._basic_cache_misses,
                "hit_rate": basic_hit_rate,
                "size": len(self._entry_basic_info_cache),
            },
            "filter_cache": {
                "hits": self._filter_cache_hits,
                "misses": self._filter_cache_misses,
                "hit_rate": filter_hit_rate,
                "size": len(self._filtered_entries_cache),
            },
            "cache_enabled": self._cache_enabled,
            "force_filter_update": self._force_filter_update,
        })

    def clear_cache(self) -> None:
        """キャッシュをクリアする (互換性のため残している)

        clear_all_cacheの別名として提供します。
        """
        self.clear_all_cache()

    def clear_basic_info_cache(self) -> None:
        """基本情報キャッシュのみをクリアする

        完全なエントリキャッシュとフィルタキャッシュはそのままで、
        基本情報キャッシュのみをクリアします。
        """
        logger.debug(
            "EntryCacheManager.clear_basic_info_cache: 基本情報キャッシュをクリア"
        )
        self._entry_basic_info_cache.clear()

    def invalidate_filter_cache(self, filter_key: Optional[str] = None) -> None:
        """フィルタキャッシュを無効化する

        Args:
            filter_key: 無効化するフィルタキー。指定しない場合はすべて削除する。
        """
        if filter_key is not None:
            logger.debug(f"invalidate_filter_cache: delete key={filter_key}")
            self._filter_cache.delete(filter_key)
        else:
            logger.debug("invalidate_filter_cache: clear all filter cache")
            self._filter_cache.clear()

    def invalidate_entry(self, key: str) -> None:
        """特定のエントリのキャッシュを無効化する

        指定されたキーに対応するエントリを、完全なエントリキャッシュと
        基本情報キャッシュから削除します。フィルタキャッシュは次回の
        フィルタリング時に更新されるようフラグを設定します。

        Args:
            key: 無効化するエントリのキー
        """
        logger.debug(
            f"EntryCacheManager.invalidate_entry: キー={key}のエントリを無効化"
        )

        # 完全なエントリキャッシュから削除
        if key in self._complete_entry_cache:
            del self._complete_entry_cache[key]

        # 基本情報キャッシュから削除
        if key in self._entry_basic_info_cache:
            del self._entry_basic_info_cache[key]

        # フィルタキャッシュ更新フラグを設定
        self._force_filter_update = True

    def set_cache_enabled(self, enabled: bool = True) -> None:
        """キャッシュの有効/無効を設定する

        Args:
            enabled: キャッシュを有効にする場合はTrue、無効にする場合はFalse
        """
        logger.debug(f"EntryCacheManager.set_cache_enabled: キャッシュ有効化={enabled}")
        self._cache_enabled = enabled
        if not enabled:
            self.clear_all_cache()
            
    def enable_cache(self, enabled: bool = True) -> None:
        """キャッシュの有効/無効を設定する (set_cache_enabledのエイリアス)

        Args:
            enabled: キャッシュを有効にする場合はTrue、無効にする場合はFalse
        """
        self.set_cache_enabled(enabled)

    def is_cache_enabled(self) -> bool:
        """キャッシュが有効かどうかを返す

        Returns:
            キャッシュが有効な場合はTrue、無効な場合はFalse
        """
        return self._cache_enabled

    def set_force_filter_update(self, force_update: bool = True) -> None:
        """フィルタ更新フラグを設定する

        このフラグがTrueの場合、次回のget_filtered_entriesの呼び出し時に
        キャッシュを無視して強制的にフィルタリングを再実行します。

        Args:
            force_update: 強制更新するかどうか
        """
        logger.debug(
            f"EntryCacheManager.set_force_filter_update: 強制更新フラグ={force_update}"
        )
        self._force_filter_update = force_update

        # フィルタキャッシュをリセット
        if force_update:
            logger.debug(
                "EntryCacheManager.set_force_filter_update: フィルタキャッシュをリセット"
            )
            self._filtered_entries_cache = []
            self._filtered_entries_cache_key = ""

    def is_force_filter_update(self) -> bool:
        """フィルタ更新フラグの状態を取得する

        Returns:
            bool: フィルタ更新フラグがTrueの場合はTrue、それ以外はFalse
        """
        return self._force_filter_update

    def get_force_filter_update(self) -> bool:
        """フィルタ更新フラグの状態を取得する

        Returns:
            bool: フィルタ更新フラグがTrueの場合はTrue、それ以外はFalse
        """
        return self._force_filter_update

    def reset_force_filter_update(self) -> None:
        """フィルタ更新フラグをリセットする

        フィルタリング処理が完了した後に呼び出され、フラグをFalseに戻します。
        """
        logger.debug(
            "EntryCacheManager.reset_force_filter_update: フィルタ更新フラグをリセット"
        )
        self._force_filter_update = False

    def get_complete_entry(self, key: str) -> Optional[EntryModel]:
        """完全なエントリをキャッシュから取得する

        Args:
            key: エントリのキー

        Returns:
            キャッシュにある場合はEntryModelオブジェクト、ない場合はNone
        """
        if not self._cache_enabled:
            return None

        entry = self._complete_entry_cache.get(key)
        if entry:
            # キャッシュヒット
            self._complete_cache_hits += 1
            self._check_and_log_performance()
            self._update_access_stats(key)
            return entry
        else:
            # キャッシュミス
            self._complete_cache_misses += 1
            return None
            
    def has_entry_in_cache(self, key: str) -> bool:
        """完全なエントリキャッシュにエントリが存在するかを確認する

        Args:
            key: エントリのキー

        Returns:
            キャッシュに存在する場合はTrue、存在しない場合はFalse
        """
        if not self._cache_enabled:
            return False
        return key in self._complete_entry_cache

    def get_basic_info_entry(self, key: str) -> Optional[EntryModel]:
        """基本情報のみのエントリをキャッシュから取得する

        Args:
            key: エントリのキー

        Returns:
            キャッシュにある場合はEntryModelオブジェクト、ない場合はNone
        """
        if not self._cache_enabled:
            return None

        entry = self._entry_basic_info_cache.get(key)
        if entry:
            # キャッシュヒット
            self._basic_cache_hits += 1
            self._check_and_log_performance()
            self._update_access_stats(key)
            return entry
        else:
            # キャッシュミス
            self._basic_cache_misses += 1
            return None
            
    def has_basic_info_in_cache(self, key: str) -> bool:
        """基本情報キャッシュにエントリが存在するかを確認する

        Args:
            key: エントリのキー

        Returns:
            キャッシュに存在する場合はTrue、存在しない場合はFalse
        """
        if not self._cache_enabled:
            return False
        return key in self._entry_basic_info_cache
        
    def get_basic_info_from_cache(self, key: str) -> Optional[EntryModel]:
        """基本情報キャッシュからエントリを取得する (get_basic_info_entryのエイリアス)

        Args:
            key: エントリのキー

        Returns:
            キャッシュにある場合はEntryModelオブジェクト、ない場合はNone
        """
        return self.get_basic_info_entry(key)

    def cache_complete_entry(self, key: str, entry: EntryModel) -> None:
        """完全なエントリをキャッシュに保存する

        Args:
            key: エントリのキー
            entry: キャッシュするEntryModelオブジェクト
        """
        if not self._cache_enabled:
            return

        logger.debug(
            f"EntryCacheManager.cache_complete_entry: キー={key}のエントリをキャッシュ"
        )
        self._complete_entry_cache[key] = entry
        
    def add_entry_to_cache(self, key: str, entry: EntryModel) -> None:
        """完全なエントリをキャッシュに保存する (cache_complete_entryのエイリアス)

        Args:
            key: エントリのキー
            entry: キャッシュするEntryModelオブジェクト
        """
        self.cache_complete_entry(key, entry)

    def cache_basic_info_entry(self, key: str, entry: EntryModel) -> None:
        """基本情報のみのエントリをキャッシュに保存する

        Args:
            key: エントリのキー
            entry: キャッシュするEntryModelオブジェクト
        """
        if not self._cache_enabled:
            return

        logger.debug(
            f"EntryCacheManager.cache_basic_info_entry: キー={key}の基本情報をキャッシュ"
        )
        self._entry_basic_info_cache[key] = entry
        
    def add_basic_info_to_cache(self, key: str, entry: EntryModel) -> None:
        """基本情報のみのエントリをキャッシュに保存する (cache_basic_info_entryのエイリアス)

        Args:
            key: エントリのキー
            entry: キャッシュするEntryModelオブジェクト
        """
        self.cache_basic_info_entry(key, entry)

    def bulk_cache_entries(
        self, entries: EntryModelList, complete: bool = False
    ) -> None:
        """複数のエントリを一括でキャッシュする

        大量のエントリを効率的にキャッシュするために使用します。

        Args:
            entries: キャッシュするEntryModelオブジェクトのリスト
            complete: 完全なエントリとしてキャッシュするかどうか（Falseの場合は基本情報のみ）
        """
        if not self._cache_enabled or not entries:
            return

        logger.debug(
            f"EntryCacheManager.bulk_cache_entries: {len(entries)}件のエントリを一括キャッシュ"
        )

        for entry in entries:
            if complete:
                self._complete_entry_cache[entry.key] = entry
            else:
                self._entry_basic_info_cache[entry.key] = entry

    def update_entry_in_cache(self, key: str, entry: EntryModel) -> None:
        """エントリの更新をキャッシュに反映する

        Args:
            key: 更新するエントリのキー
            entry: 更新後のEntryModelオブジェクト
        """
        if not self._cache_enabled:
            return

        logger.debug(
            f"EntryCacheManager.update_entry_in_cache: キー={key}のエントリをキャッシュ更新"
        )

        # 完全なエントリキャッシュを更新
        self._complete_entry_cache[key] = entry

        # 基本情報キャッシュも更新
        if key in self._entry_basic_info_cache:
            basic_info = EntryModel(
                key=entry.key,
                msgid=entry.msgid,
                msgstr=entry.msgstr,
                fuzzy="fuzzy" in entry.flags,
                obsolete=entry.obsolete,
                position=entry.position,
                flags=entry.flags,
            )
            self._entry_basic_info_cache[key] = basic_info

        # フィルタ結果キャッシュを無効化
        self.set_force_filter_update(True)

    def _generate_filter_cache_key(self, conditions: FilterConditions) -> str:
        """フィルタ条件からキャッシュキーを生成する

        フィルタ条件の辞書からユニークなキャッシュキーを生成します。
        このキーはフィルタ結果のキャッシュに使用されます。

        最適化ポイント:
        - 条件辞書の正規化による一貫したキー生成
        - MD5ハッシュによる短いキー長と効率的な比較
        - JSON形式の使用による複雑な条件の正確な表現

        Args:
            conditions: フィルタ条件の辞書

        Returns:
            str: 生成されたキャッシュキー
        """
        # 辞書を正規化（キーでソート）
        conditions_sorted = {}

        # 文字列と基本型のみを含む辞書に変換
        for key, value in conditions.items():
            # 関数やクラスインスタンスなど、JSONに変換できない型は除外
            if isinstance(value, (str, int, float, bool, type(None))):
                conditions_sorted[key] = value
            elif isinstance(value, dict):
                # 入れ子の辞書も正規化
                conditions_sorted[key] = {
                    k: v
                    for k, v in value.items()
                    if isinstance(v, (str, int, float, bool, type(None)))
                }
            elif isinstance(value, (list, tuple)):
                # リストは単純なJSONに変換できる要素のみを含む新しいリストに変換
                conditions_sorted[key] = [
                    v
                    for v in value
                    if isinstance(v, (str, int, float, bool, type(None)))
                ]

        # 正規化した条件をJSON形式に変換してハッシュ化
        conditions_str = json.dumps(conditions_sorted, sort_keys=True)
        return hashlib.md5(conditions_str.encode()).hexdigest()

    def get_filtered_entries_cache(
        self, filter_conditions: FilterConditions
    ) -> Optional[EntryModelList]:
        """フィルタ条件に合致するフィルタ結果キャッシュを取得する

        Args:
            filter_conditions: フィルタ条件の辞書

        Returns:
            フィルタ結果のキャッシュ、存在しない場合はNone
        """
        if not self._cache_enabled:
            return None

        # 強制更新フラグがある場合はキャッシュを無視
        if self._force_filter_update:
            self._filter_cache_misses += 1
            return None

        # フィルタ条件からキャッシュキーを生成
        cache_key = self._generate_filter_cache_key(filter_conditions)

        # 現在のキャッシュキーと一致すれば、キャッシュを返す
        if (
            cache_key == self._filtered_entries_cache_key
            and self._filtered_entries_cache
        ):
            logger.debug(
                f"EntryCacheManager.get_filtered_entries_cache: キャッシュヒット key={cache_key}"
            )
            self._filter_cache_hits += 1
            self._check_and_log_performance()
            return self._filtered_entries_cache

        self._filter_cache_misses += 1
        return None

    def cache_filtered_entries(
        self, filter_conditions: FilterConditions, entries: EntryModelList
    ) -> None:
        """フィルタリング結果をキャッシュする

        Args:
            filter_conditions: フィルタ条件
            entries: フィルタリング結果のエントリリスト
        """
        if not self._cache_enabled:
            logger.debug("キャッシュが無効化されているため、フィルタリング結果をキャッシュしません")
            return

        # キャッシュキーを生成
        cache_key = self._generate_filter_cache_key(filter_conditions)
        
        # キャッシュを更新
        self._filtered_entries_cache = entries
        self._filtered_entries_cache_key = cache_key
        self._force_filter_update = False
        
        logger.debug(
            f"EntryCacheManager.cache_filtered_entries: フィルタ結果をキャッシュしました ({len(entries)}件)"
        )
        
    def set_filter_cache(self, entries: EntryModelList) -> None:
        """フィルタリング結果を直接キャッシュする

        こちらは簡易バージョンで、キャッシュキーは使用せず、エントリリストのみをキャッシュします。
        キャッシュの一貫性を確保するため、通常は cache_filtered_entries メソッドの使用を推奨します。

        Args:
            entries: フィルタリング結果のエントリリスト
        """
        if not self._cache_enabled:
            logger.debug("キャッシュが無効化されているため、フィルタリング結果をキャッシュしません")
            return
            
        # キャッシュを更新
        self._filtered_entries_cache = entries
        self._force_filter_update = False
        
        logger.debug(
            f"EntryCacheManager.set_filter_cache: フィルタ結果をキャッシュしました ({len(entries)}件)"
        )

    def get_filter_cache(self) -> Optional[EntryModelList]:
        """キャッシュされたフィルタリング結果を取得する

        Returns:
            Optional[EntryModelList]: キャッシュされたフィルタリング結果、もしくはNone
        """
        if not self._cache_enabled:
            logger.debug("キャッシュが無効化されているため、null を返します")
            return None
            
        if self._force_filter_update:
            logger.debug("強制更新フラグが立っているため、null を返します")
            return None
            
        if not self._filtered_entries_cache:
            logger.debug("フィルタキャッシュが空のため、null を返します")
            return None
            
        # キャッシュヒットのカウントを増加
        self._filter_cache_hits += 1
        self._check_and_log_performance()
        
        logger.debug(f"EntryCacheManager.get_filter_cache: キャッシュヒット ({len(self._filtered_entries_cache)}件)")
        return self._filtered_entries_cache

    def get_filtered_ids(self, filter_key: str) -> Optional[List[str]]:
        """フィルタ条件に合致するエントリIDのキャッシュを取得する

        ToDo Phase 1: フィルタ条件に合致するエントリIDのキャッシュを取得する
        """
        ids = self._filter_cache.get(filter_key)
        if ids is not None:
            logger.debug(
                f"get_filtered_ids: hit for key={filter_key} ({len(ids)} ids)"
            )
        else:
            logger.debug(f"get_filtered_ids: miss for key={filter_key}")
        return ids

    def cache_filtered_ids(self, filter_key: str, entry_ids: List[str]) -> None:
        """フィルタ条件に合致するエントリIDをキャッシュする

        ToDo Phase 1: フィルタ条件に合致するエントリIDをキャッシュする
        """
        logger.debug(
            f"cache_filtered_ids: store {len(entry_ids)} ids for key={filter_key}"
        )
        self._filter_cache.set(filter_key, entry_ids)

    def evaluate_cache_efficiency(self) -> CacheEfficiency:
        """キャッシュ効率の評価情報を取得する

        現在のキャッシュ状態と効率に関する情報を返します。
        これはキャッシュ戦略の最適化やデバッグに役立ちます。

        Returns:
            CacheEfficiency: キャッシュ効率情報の辞書
        """
        info = {
            "complete_entry_cache_size": len(self._complete_entry_cache),
            "basic_info_cache_size": len(self._entry_basic_info_cache),
            "filtered_entries_cache_size": len(self._filtered_entries_cache),
            "cache_enabled": self._cache_enabled,
            "force_filter_update": self._force_filter_update,
        }

        if hasattr(self, "_row_key_map"):
            info["row_key_map_size"] = len(self._row_key_map)

        # メモリ使用量の概算（将来的に実装）

        return cast(CacheEfficiency, info)

    # UI層との連携機能

    def add_row_key_mapping(self, row: int, key: str) -> None:
        """行インデックスとエントリキーのマッピングを追加または更新する

        UI層からのアクセスを効率化するために、テーブルの行インデックスと
        エントリキーのマッピングを管理します。これにより、UI層（TableManager,
        EventHandler）の独自キャッシュを排除し、キャッシュ管理を一元化できます。

        Args:
            row: テーブルの行インデックス
            key: エントリキー
        """
        if not self._cache_enabled:
            return
        logger.debug(f"EntryCacheManager.add_row_key_mapping: row={row}, key={key}")
        self._row_key_map[row] = key
        # 逆引きマップも更新
        self._key_row_map[key] = row

    def get_key_for_row(self, row: int) -> Optional[str]:
        """指定された行インデックスに対応するエントリキーを取得する

        Args:
            row: テーブルの行インデックス

        Returns:
            エントリキー、存在しない場合はNone
        """
        if not self._cache_enabled:
            return None
        return self._row_key_map.get(row)

    def clear_row_key_mappings(self) -> None:
        """行インデックスとエントリキーのマッピングをクリアする"""
        logger.debug("EntryCacheManager.clear_row_key_mappings: マッピングをクリア")
        if hasattr(self, "_row_key_map"):
            self._row_key_map.clear()
        # 逆引きマップもクリア
        self._key_row_map.clear()

    def find_row_by_key(self, key: str) -> int:
        """指定されたエントリキーに対応する行インデックスを取得する

        Args:
            key: エントリキー

        Returns:
            行インデックス、存在しない場合は-1
        """
        if not self._cache_enabled:
            return -1
            
        row = self._key_row_map.get(key, -1)
        logger.debug(f"EntryCacheManager.find_row_by_key: key={key}, found_row={row}")
        return row

    def update_entry_in_ui_cache(self, entry: EntryModel) -> None:
        """完全エントリキャッシュ内のエントリを更新する

        エントリが更新された場合、UI層での表示に使われるキャッシュも更新します。
        これはTableManagerとEventHandlerの独自キャッシュを廃止し、
        中央キャッシュに一元化するための機能です。

        Args:
            entry: 更新するエントリモデル
        """
        logger.debug(f"EntryCacheManager.update_entry_in_ui_cache: key={entry.key}")
        # 完全なエントリキャッシュを更新
        self.cache_complete_entry(entry.key, entry)

        # UI表示用イベント通知（将来的にオブザーバーパターンで拡張可能）
        self.notify_entry_updated(entry.key)

    def notify_entry_updated(self, key: str) -> None:
        """エントリ更新通知

        このメソッドは将来的にオブザーバーパターンに拡張可能です。
        現在は内部処理のみ行います。

        Args:
            key: 更新されたエントリのキー
        """
        logger.debug(f"EntryCacheManager.notify_entry_updated: key={key}")
        # 将来的にはオブザーバーに通知する実装に拡張可能

    def set_max_cache_size(self, size: int) -> None:
        """キャッシュの最大サイズを設定する

        Args:
            size: キャッシュの最大エントリ数
        """
        self._max_cache_size = max(100, size)  # 最小サイズは100
        logger.debug(f"キャッシュ最大サイズを{self._max_cache_size}に設定")
        self._trim_cache_if_needed()

    def set_lru_size(self, size: int) -> None:
        """LRUキャッシュサイズを設定する

        Args:
            size: 保持する最近使用されたエントリの数
        """
        self._lru_size = max(10, size)  # 最小サイズは10
        logger.debug(f"LRUキャッシュサイズを{self._lru_size}に設定")

    def _trim_cache_if_needed(self) -> None:
        """必要に応じてキャッシュサイズを調整する

        キャッシュサイズが上限を超えた場合、使用頻度の低いエントリを削除します。
        ただし、最近使用されたエントリ（LRUキャッシュ）は保持します。
        """
        if len(self._complete_entry_cache) > self._max_cache_size:
            logger.debug(
                f"キャッシュサイズ調整: {len(self._complete_entry_cache)}→{self._max_cache_size}"
            )
            
            entries_to_remove = len(self._complete_entry_cache) - self._max_cache_size
            
            protected_keys = set()
            if self._last_access_time:
                recent_keys = sorted(
                    self._last_access_time.keys(),
                    key=lambda k: self._last_access_time.get(k, 0),
                    reverse=True
                )[:self._lru_size]
                protected_keys.update(recent_keys)
            
            if self._access_counter:
                candidates = [
                    k for k in self._complete_entry_cache.keys()
                    if k not in protected_keys
                ]
                candidates.sort(key=lambda k: self._access_counter.get(k, 0))
                
                keys_to_remove = candidates[:entries_to_remove]
                
                for key in keys_to_remove:
                    if key in self._complete_entry_cache:
                        del self._complete_entry_cache[key]
                    if key in self._entry_basic_info_cache:
                        del self._entry_basic_info_cache[key]
                    if key in self._access_counter:
                        del self._access_counter[key]
                    if key in self._last_access_time:
                        del self._last_access_time[key]
                
                logger.debug(f"キャッシュから{len(keys_to_remove)}件のエントリを削除")

    def _update_access_stats(self, key: str) -> None:
        """エントリのアクセス統計を更新する

        Args:
            key: アクセスされたエントリのキー
        """
        self._access_counter[key] += 1
        self._last_access_time[key] = time.time()

    def prefetch_visible_entries(self, visible_keys: List[str], fetch_callback=None) -> None:
        """表示中のエントリをプリフェッチする

        テーブルに表示されている（または表示されそうな）エントリを
        事前にキャッシュに読み込みます。これにより、スクロール時の
        エントリ表示をスムーズにします。

        Args:
            visible_keys: 表示中または表示予定のエントリキーのリスト
            fetch_callback: キーのリストを受け取り、EntryModelのリストを返すコールバック関数
                           形式: callback([key1, key2, ...]) -> [entry1, entry2, ...]
        """
        if not self._cache_enabled or not visible_keys:
            return
            
        logger.debug(
            f"EntryCacheManager.prefetch_visible_entries: {len(visible_keys)}件"
        )
        
        keys_to_actually_prefetch: Set[str] = set()
        with self._prefetch_lock:
            # キャッシュになく、かつプリフェッチ中でもないキーを抽出
            keys_to_consider = {
                key for key in visible_keys 
                if key not in self._complete_entry_cache and 
                   key not in self._keys_being_prefetched
            }
            
            if not keys_to_consider:
                logger.debug("EntryCacheManager: プリフェッチ対象の新しいキーはありません。")
                return
                
            # プリフェッチキューに追加し、処理中セットにも追加
            # 既存のキューに入っているものも考慮（本来は不要だが念のため）
            new_keys_for_queue = keys_to_consider - self._prefetch_queue
            if new_keys_for_queue:
                self._prefetch_queue.update(new_keys_for_queue)
                self._keys_being_prefetched.update(new_keys_for_queue)
                keys_to_actually_prefetch = new_keys_for_queue # 実際に新たに追加されたキー
            else:
                logger.debug("EntryCacheManager: 考慮対象キーはすべて既にキューにありました。")
                return # 新しくキューに追加するものがなければ何もしない

        logger.debug(
            f"EntryCacheManager: プリフェッチキューに{len(keys_to_actually_prefetch)}件追加。 \
            キュー合計: {len(self._prefetch_queue)}件, 処理中合計: {len(self._keys_being_prefetched)}件"
        )

        # プリフェッチ処理が実行中でなければ開始
        with self._prefetch_lock:
            if not self._prefetch_in_progress:
                self._prefetch_in_progress = True
                logger.debug("EntryCacheManager: 非同期プリフェッチ処理を開始します。")
                # asyncioを使ってバックグラウンドで実行
                import asyncio
                asyncio.run_coroutine_threadsafe(
                    self._async_prefetch(fetch_callback),
                    asyncio.get_event_loop() # 現在のスレッドのイベントループを取得
                )
            else:
                logger.debug("EntryCacheManager: プリフェッチ処理は既に実行中です。")

    async def _async_prefetch(self, fetch_callback=None) -> None:
        """非同期でプリフェッチを実行する内部メソッド"""
        try:
            while True:
                batch_keys = []
                with self._prefetch_lock:
                    if not self._prefetch_queue:
                        self._prefetch_in_progress = False
                        break
                        
                    batch_keys = list(self._prefetch_queue)[:self.PREFETCH_BATCH_SIZE]
                    self._prefetch_queue = self._prefetch_queue - set(batch_keys)
                
                if not batch_keys:
                    continue
                    
                logger.debug(f"EntryCacheManager: プリフェッチバッチ処理開始: {len(batch_keys)}件")
                keys_processed_in_batch = set(batch_keys) # このバッチで処理しようとしたキーを記録
                
                try:
                    # fetch_callbackを呼び出してデータを取得
                    fetched_entries = await fetch_callback(batch_keys)
                    if fetched_entries:
                        for entry in fetched_entries:
                            if entry and hasattr(entry, 'key'):
                                self.cache_complete_entry(entry.key, entry)
                                self._update_access_stats(entry.key)
                        logger.debug(f"プリフェッチ完了: {len(fetched_entries)}件のエントリをキャッシュに追加")
                    else:
                        logger.debug("EntryCacheManager: 存在しないエントリをキャッシュ (空データ): {key}")
                        # self.cache_complete_entry(key, EntryModel(key=key)) # 空モデルは入れない方が良いかも
                except Exception as e:
                    logger.error(f"EntryCacheManager: プリフェッチ中のfetch_callbackでエラー: {e}", exc_info=True)
                finally:
                    # バッチ処理が完了（成功・失敗問わず）したら、処理中セットからキーを削除
                    with self._prefetch_lock:
                        self._keys_being_prefetched -= keys_processed_in_batch
                        logger.debug(f"EntryCacheManager: プリフェッチ処理中セットから{len(keys_processed_in_batch)}件削除。残り処理中: {len(self._keys_being_prefetched)}件")
                
                self._trim_cache_if_needed()
                
                # 少し待機して他の処理にCPUを譲る
                await asyncio.sleep(0.01)

            # プリフェッチ完了
            with self._prefetch_lock:
                self._prefetch_in_progress = False
                logger.debug("EntryCacheManager: 非同期プリフェッチ処理が完了しました。")
                # 念のため、完了時に処理中セットをクリア（キューが空なら）
                if not self._prefetch_queue:
                    remaining_count = len(self._keys_being_prefetched)
                    if remaining_count > 0:
                        logger.warning(f"プリフェッチ完了時に処理中セットにキーが残っています: {remaining_count}件。クリアします。")
                        self._keys_being_prefetched.clear()

        except Exception as e:
            logger.error(f"プリフェッチ処理でエラーが発生: {e}")
            with self._prefetch_lock:
                self._prefetch_in_progress = False

    def is_key_being_prefetched(self, key: str) -> bool:
        """指定されたキーが現在プリフェッチ処理中かどうかを確認する"""
        with self._prefetch_lock:
            return key in self._keys_being_prefetched

    def set_entry(self, key: str, entry: EntryModel) -> None:
        if not self._cache_enabled:
            return
        self._complete_cache.set(key, entry)
        self._entry_timestamps[key] = time.time()

    def get_entry(self, key: str) -> Optional[EntryModel]:
        if not self._cache_enabled:
            return None
        if self._cache_ttl > 0:
            ts = self._entry_timestamps.get(key)
            if ts is not None and time.time() - ts > self._cache_ttl:
                self.invalidate_entry(key)
                return None
        return self._complete_cache.get(key)

    def set_filtered_entries(self, cond: FilterConditions, entries: EntryModelList) -> None:
        key = json.dumps(cond, sort_keys=True)
        self._filter_cache.set(key, entries)

    def get_filtered_entries(self, cond: FilterConditions) -> Optional[EntryModelList]:
        return self._filter_cache.get(json.dumps(cond, sort_keys=True))

    def disable_cache(self) -> None:
        self._cache_enabled = False

    def prefetch_entries(self, keys: List[str], fetch_callback: Callable[[List[str]], Dict[str, EntryModel]]) -> None:
        if not self._prefetch_enabled:
            return
        for k in keys:
            self._keys_being_prefetched.add(k)
        try:
            results = fetch_callback(keys)
            for k, e in results.items():
                self.set_entry(k, e)
        finally:
            for k in keys:
                self._keys_being_prefetched.discard(k)
