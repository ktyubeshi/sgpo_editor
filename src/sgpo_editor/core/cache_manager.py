"""エントリキャッシュ管理モジュール

このモジュールは、POエントリのキャッシュを管理するためのクラスを提供します。
キャッシュの保存、取得、無効化などの機能を一元管理し、ViewerPOFileクラスの責務を軽減します。

キャッシュシステムの概要:
1. 完全なエントリキャッシュ: データベースから取得した完全なEntryModelオブジェクトを保持
2. 基本情報キャッシュ: 表示に必要な最小限の情報のみを持つEntryModelオブジェクトを保持
3. フィルタ結果キャッシュ: 特定のフィルタ条件に対する結果リストを保持

これらのキャッシュは、ViewerPOFileクラスとDatabaseAccessorクラスと連携して動作し、
データベースアクセスを最小限に抑えることでパフォーマンスを向上させます。
"""

import logging
from typing import Optional, Union

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import EntryModelMap, EntryModelList

logger = logging.getLogger(__name__)


class EntryCacheManager:
    """POエントリのキャッシュを管理するクラス
    
    このクラスは、POエントリの各種キャッシュを管理し、キャッシュの一貫性を保つための
    機能を提供します。主に以下の3種類のキャッシュを管理します：
    
    1. complete_entry_cache: 完全なEntryModelオブジェクトのキャッシュ
       - 用途: エントリの詳細情報が必要な場合（編集時など）に使用
       - キー: エントリのキー（通常は位置を表す文字列）
       - 値: 完全なEntryModelオブジェクト（すべてのフィールドを含む）
    
    2. entry_basic_info_cache: 基本情報のみのEntryModelオブジェクトのキャッシュ
       - 用途: エントリのリスト表示など、基本情報のみが必要な場合に使用
       - キー: エントリのキー
       - 値: 基本情報のみを含むEntryModelオブジェクト（msgid, msgstr, fuzzy, obsoleteなど）
    
    3. filtered_entries_cache: フィルタリング結果のキャッシュ
       - 用途: 同じフィルタ条件での再検索を高速化
       - キー: フィルタ条件を表す文字列（_filtered_entries_cache_key）
       - 値: フィルタ条件に一致するEntryModelオブジェクトのリスト
    
    キャッシュの連携方法:
    - ViewerPOFileクラスはget_entry_by_keyなどのメソッドでキャッシュを参照
    - エントリが更新されると、update_entry_in_cacheメソッドで関連するすべてのキャッシュを更新
    - フィルタ条件が変更されると、set_force_filter_updateメソッドでフィルタキャッシュを無効化
    - ファイル読み込み時などは、clear_all_cacheメソッドですべてのキャッシュをクリア
    """
    
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
    
    def set_cache_enabled(self, enabled: bool = True) -> None:
        """キャッシュの有効/無効を設定する
        
        Args:
            enabled: キャッシュを有効にする場合はTrue、無効にする場合はFalse
        """
        logger.debug(f"EntryCacheManager.set_cache_enabled: キャッシュ有効化={enabled}")
        self._cache_enabled = enabled
        if not enabled:
            self.clear_all_cache()
    
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
        logger.debug(f"EntryCacheManager.set_force_filter_update: 強制更新フラグ={force_update}")
        self._force_filter_update = force_update
        
        # フィルタキャッシュをリセット
        if force_update:
            logger.debug("EntryCacheManager.set_force_filter_update: フィルタキャッシュをリセット")
            self._filtered_entries_cache = []
            self._filtered_entries_cache_key = ""
    
    def is_force_filter_update(self) -> bool:
        """フィルタ更新フラグの状態を返す
        
        Returns:
            フィルタを強制更新する場合はTrue、しない場合はFalse
        """
        return self._force_filter_update
    
    def reset_force_filter_update(self) -> None:
        """フィルタ更新フラグをリセットする
        
        フィルタリング処理が完了した後に呼び出され、フラグをFalseに戻します。
        """
        logger.debug("EntryCacheManager.reset_force_filter_update: フィルタ更新フラグをリセット")
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
        
        return self._complete_entry_cache.get(key)
    
    def get_basic_info_entry(self, key: str) -> Optional[EntryModel]:
        """基本情報のみのエントリをキャッシュから取得する
        
        Args:
            key: エントリのキー
            
        Returns:
            キャッシュにある場合はEntryModelオブジェクト、ない場合はNone
        """
        if not self._cache_enabled:
            return None
        
        return self._entry_basic_info_cache.get(key)
    
    def cache_complete_entry(self, key: str, entry: EntryModel) -> None:
        """完全なエントリをキャッシュに保存する
        
        Args:
            key: エントリのキー
            entry: キャッシュするEntryModelオブジェクト
        """
        if not self._cache_enabled:
            return
        
        logger.debug(f"EntryCacheManager.cache_complete_entry: キー={key}のエントリをキャッシュ")
        self._complete_entry_cache[key] = entry
    
    def cache_basic_info_entry(self, key: str, entry: EntryModel) -> None:
        """基本情報のみのエントリをキャッシュに保存する
        
        Args:
            key: エントリのキー
            entry: キャッシュするEntryModelオブジェクト
        """
        if not self._cache_enabled:
            return
        
        logger.debug(f"EntryCacheManager.cache_basic_info_entry: キー={key}の基本情報をキャッシュ")
        self._entry_basic_info_cache[key] = entry
    
    def remove_entry_from_cache(self, key: str) -> None:
        """指定されたキーのエントリをすべてのキャッシュから削除する
        
        Args:
            key: 削除するエントリのキー
        """
        logger.debug(f"EntryCacheManager.remove_entry_from_cache: キー={key}のエントリをキャッシュから削除")
        if key in self._complete_entry_cache:
            del self._complete_entry_cache[key]
        
        if key in self._entry_basic_info_cache:
            del self._entry_basic_info_cache[key]
        
        # フィルタ結果キャッシュも無効化
        self.set_force_filter_update(True)
    
    def update_entry_in_cache(self, key: str, entry: EntryModel) -> None:
        """エントリの更新をキャッシュに反映する
        
        Args:
            key: 更新するエントリのキー
            entry: 更新後のEntryModelオブジェクト
        """
        if not self._cache_enabled:
            return
        
        logger.debug(f"EntryCacheManager.update_entry_in_cache: キー={key}のエントリをキャッシュ更新")
        
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
    
    def cache_filtered_entries(self, entries: EntryModelList, cache_key: str) -> None:
        """フィルタリング結果をキャッシュに保存する
        
        Args:
            entries: フィルタリング結果のエントリリスト
            cache_key: フィルタ条件を表すキャッシュキー
        """
        if not self._cache_enabled:
            return
        
        logger.debug(f"EntryCacheManager.cache_filtered_entries: {len(entries)}件のフィルタ結果をキャッシュ")
        self._filtered_entries_cache = entries
        self._filtered_entries_cache_key = cache_key
    
    def get_filtered_entries_cache(self, cache_key: str) -> Optional[EntryModelList]:
        """フィルタリング結果をキャッシュから取得する
        
        Args:
            cache_key: フィルタ条件を表すキャッシュキー
            
        Returns:
            キャッシュにある場合はエントリリスト、ない場合はNone
        """
        if not self._cache_enabled or self._force_filter_update:
            return None
        
        if not self._filtered_entries_cache or self._filtered_entries_cache_key != cache_key:
            return None
        
        logger.debug(f"EntryCacheManager.get_filtered_entries_cache: キャッシュから{len(self._filtered_entries_cache)}件のフィルタ結果を返却")
        return self._filtered_entries_cache
    
    def prefetch_entries(self, keys: List[str], fetch_callback) -> None:
        """指定されたキーのエントリをプリフェッチする
        
        Args:
            keys: プリフェッチするエントリのキーリスト
            fetch_callback: キャッシュにないエントリを取得するためのコールバック関数
        """
        if not self._cache_enabled or not keys:
            return
        
        # キャッシュにないキーを特定
        missing_keys = [key for key in keys if key not in self._complete_entry_cache]
        if not missing_keys:
            return
        
        logger.debug(f"EntryCacheManager.prefetch_entries: {len(missing_keys)}件のエントリをプリフェッチ")
        
        # コールバックを使用してエントリを取得
        entries = fetch_callback(missing_keys)
        
        # キャッシュに保存
        for key, entry in entries.items():
            self.cache_complete_entry(key, entry)
