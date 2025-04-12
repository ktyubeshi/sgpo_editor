"""リファクタリングされたPOファイルビューア

このモジュールは、POファイルを読み込み、表示、編集するための機能を提供します。
ViewerPOFileクラスをリファクタリングし、キャッシュ管理とデータベースアクセスの責務を分離しています。

責務ごとに分割された各クラスをインポートし、それらを継承した統合クラスを提供します。
このクラスは古いViewerPOFileクラスの完全な代替となり、以下の責務を明確に分離しています:
1. ViewerPOFileBase: 基本的な初期化とPOファイル読み込み機能
2. ViewerPOFileEntryRetriever: エントリ取得関連の機能
3. ViewerPOFileFilter: フィルタリング関連の機能
4. ViewerPOFileUpdater: エントリ更新関連の機能
5. ViewerPOFileStats: 統計情報と保存機能

継承チェーン:
ViewerPOFileBase <- ViewerPOFileEntryRetriever <- ViewerPOFileFilter <- ViewerPOFileUpdater <- ViewerPOFileStats
"""

import logging
from typing import Dict, List, Optional, Union, Set, cast
from pathlib import Path

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import EntryDict, EntryDictList, FilterSettings
from sgpo_editor.core.po_factory import POLibraryType
from sgpo_editor.core.viewer_po_file_stats import ViewerPOFileStats
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.constants import TranslationStatus

logger = logging.getLogger(__name__)


class ViewerPOFileRefactored(ViewerPOFileStats):
    """POファイルを読み込み、表示するためのリファクタリングされたクラス

    このクラスは、キャッシュ管理とデータベースアクセスの責務を分離し、
    EntryCacheManagerとDatabaseAccessorを利用して実装されています。

    責務ごとに分割された以下のクラスを継承しています：
    - ViewerPOFileBase: 基本的な初期化とPOファイル読み込み機能
    - ViewerPOFileEntryRetriever: エントリ取得関連の機能
    - ViewerPOFileFilter: フィルタリング関連の機能
    - ViewerPOFileUpdater: エントリ更新関連の機能
    - ViewerPOFileStats: 統計情報と保存機能

    このクラスは、古いViewerPOFileクラスの完全な代替として機能し、
    すべての機能を提供しながらも、コードの保守性と拡張性を高めています。
    
    依存性注入パターンによりDatabaseAccessorとEntryCacheManagerを外部から注入できるため、
    - 単体テストが容易になる（モックやスタブの使用が可能）
    - 異なるデータベース実装やキャッシュ戦略への切り替えが容易
    - 実行時の設定に応じた振る舞いの変更が可能
    になっています。
    """

    def __init__(
        self,
        library_type: Optional[POLibraryType] = POLibraryType.SGPO,
        db_accessor: Optional[DatabaseAccessor] = None,
        cache_manager: Optional[EntryCacheManager] = None,
    ):
        """初期化

        Args:
            library_type: 使用するPOライブラリの種類
            db_accessor: データベースアクセサのインスタンス（省略時は内部で生成）
            cache_manager: キャッシュマネージャのインスタンス（省略時は内部で生成）
            
        外部からDatabaseAccessorとEntryCacheManagerを注入可能な設計になっており、
        テスト時にはモックやスタブを使用して依存関係を置き換えることができます。
        """
        # 親クラスの初期化
        super().__init__(library_type, db_accessor, cache_manager)

        # デフォルトのソート条件
        self._sort_column: str = "position"  # ソート対象列名
        self._sort_order: str = "ASC"       # ソート順序 (ASC or DESC)

        # フィルタ関連のデフォルト値 (ViewerPOFileFilter からの移譲を想定)
        self.exact_match: bool = False
        self.case_sensitive: bool = False

        logger.debug("ViewerPOFileRefactored: 初期化完了")

    async def load(self, path: Union[str, Path]) -> None:
        """POファイルを非同期で読み込む

        Args:
            path: 読み込むPOファイルのパス
            
        このメソッドはsuper().load()を呼び出し、ViewerPOFileBase.loadメソッドの機能を使用します。
        非同期で動作し、UIのブロックを防ぎながらPOファイルを読み込みます。
        """
        # 親クラスのload()メソッドを非同期で呼び出す
        await super().load(path)
        logger.debug(f"ViewerPOFileRefactored.load: {path} の読み込みが完了しました")

    def get_all_entries(self) -> List[EntryModel]:
        """すべてのエントリを取得する

        データベースから全エントリを位置順に取得し、EntryModelリストとして返します。
        キャッシュは使用せず、常に最新のデータを返します。

        Returns:
            List[EntryModel]: すべてのエントリのリスト
        """
        # データベースからすべてのエントリを取得
        entries_dict = self.db_accessor.get_filtered_entries(
            sort_column="position", sort_order="ASC"
        )

        # リストからEntryModelオブジェクトのリストに変換
        entries = [EntryModel.from_dict(entry_dict) for entry_dict in entries_dict]

        return entries

    def reset_filter(self) -> None:
        """フィルタをリセットする

        すべてのフィルタ条件をクリアし、デフォルト状態に戻します。
        また、キャッシュマネージャのフィルタキャッシュも無効化します。
        """
        self.set_filter(
            search_text="",
            sort_column="position",
            sort_order="ASC",
            flag_conditions={},
            translation_status=None,
        )

        # フィルタリング結果を強制的に更新（キャッシュマネージャ経由）
        if self.cache_manager:
            self.cache_manager.set_force_filter_update(True)
            self.cache_manager.invalidate_filter_cache()
        self.filtered_entries = []

    def is_loaded(self) -> bool:
        """ファイルが読み込まれているかを返す

        Returns:
            bool: ファイルが読み込まれている場合はTrue
        """
        return self._is_loaded

    def is_modified(self) -> bool:
        """ファイルが変更されているかを返す

        Returns:
            bool: ファイルが変更されている場合はTrue
        """
        return self.modified

    def set_modified(self, modified: bool = True) -> None:
        """変更フラグを設定する

        Args:
            modified: 設定する変更フラグの値
        """
        self.modified = modified

    def get_entry(self, key: str) -> Optional[EntryModel]:
        """エントリキーからエントリを取得する (従来メソッドとの互換性用)

        Args:
            key: エントリキー

        Returns:
            Optional[EntryModel]: 見つかったエントリ、または None
        """
        return self.get_entry_by_key(key)

    def get_entry_position(self, position: int) -> Optional[EntryModel]:
        """エントリ番号からエントリを取得する (従来メソッドとの互換性用)

        Args:
            position: エントリ番号

        Returns:
            Optional[EntryModel]: 見つかったエントリ、または None
        """
        return self.get_entry_at(position)

    def count_entries(self) -> int:
        """全エントリ数を取得する

        Returns:
            int: エントリの総数
        """
        return self.db_accessor.count_entries() if self.db_accessor else 0

    def get_available_flags(self) -> Set[str]:
        """利用可能なすべてのフラグのセットを取得する

        Returns:
            Set[str]: 利用可能なフラグのセット
        """
        if not self.db_accessor:
            return set()
        return self.db_accessor.get_all_flags()

    def get_filters(self) -> FilterSettings:
        """現在のフィルタ設定を取得する

        Returns:
            FilterSettings: 現在のフィルタ設定
        """
        return {
            "search_text": self.search_text,
            "sort_column": self.sort_column,
            "sort_order": self.sort_order,
            "flag_conditions": self.flag_conditions.copy() if self.flag_conditions else {},
            "translation_status": self.translation_status,
        }

    def set_sort_criteria(self, column: str, order: str) -> None:
        """ソート条件を設定する

        Args:
            column: ソートする列名
            order: ソート順序 ('ASC' or 'DESC')
        """
        logger.debug(f"ViewerPOFileRefactored.set_sort_criteria: column={column}, order={order}")
        valid_order = order.upper() if order else "ASC"
        if valid_order not in ["ASC", "DESC"]:
            valid_order = "ASC"
            
        if self._sort_column != column or self._sort_order != valid_order:
            self._sort_column = column
            self._sort_order = valid_order
            self.invalidate_cache() # ソート条件が変わったらキャッシュを無効化

    def invalidate_cache(self) -> None:
        """キャッシュを無効化する

        フィルタリング結果とキャッシュマネージャのキャッシュを無効化し、
        次回のget_filtered_entriesでフィルタ再計算を強制します。
        """
        logger.debug("ViewerPOFileRefactored.invalidate_cache: キャッシュ無効化")
        if self.cache_manager:
            self.cache_manager.set_force_filter_update(True)
            self.cache_manager.clear_cache()
        self.filtered_entries = []
        
    def prefetch_entries(self, keys: List[str]) -> None:
        """指定されたキーのエントリをプリフェッチする
        
        Args:
            keys: プリフェッチするエントリのキーのリスト
        """
        if not self.cache_manager or not self.db_accessor or not keys:
            return
            
        logger.debug(f"ViewerPOFileRefactored.prefetch_entries: {len(keys)}件のエントリをプリフェッチ")
        
        self.cache_manager.prefetch_visible_entries(
            keys,
            fetch_callback=self._fetch_entries_by_keys
        )
        
    def _fetch_entries_by_keys(self, keys: List[str]) -> List[EntryModel]:
        """指定されたキーのエントリをデータベースから取得する
        
        Args:
            keys: 取得するエントリのキーのリスト
            
        Returns:
            List[EntryModel]: 取得したエントリのリスト
        """
        if not self.db_accessor or not keys:
            return []
            
        try:
            entries_dict = self.db_accessor.get_entries_by_keys(keys)
            
            entries = [EntryModel.from_dict(cast(EntryDict, entry_dict)) for entry_dict in entries_dict]
            
            return entries
        except Exception as e:
            logger.error(f"エントリ取得中にエラーが発生: {e}")
            return []

    def get_unique_msgid_count(self) -> int:
        """一意のmsgid数を取得する

        Returns:
            int: 一意のmsgidの数
        """
        if not self.db_accessor:
            return 0
        return self.db_accessor.get_unique_msgid_count()

    def get_filename(self) -> str:
        """現在のファイル名を取得する

        Returns:
            str: ファイル名
        """
        if not self.path:
            return ""
        return Path(self.path).name

    def get_filtered_entries(
        self,
        filter_text: str = "すべて",
        filter_keyword: Optional[str] = None,
        match_mode: str = "部分一致",
        case_sensitive: bool = False,
        filter_status: Optional[Set[str]] = None,
        filter_obsolete: bool = True,
        update_filter: bool = True,
        search_text: Optional[str] = None,
    ) -> List[EntryModel]:
        """フィルタリングされたエントリのリストを取得する。

        Args:
            filter_text: フィルタテキスト (advanced_searchでは直接使用されない)
            filter_keyword: フィルタキーワード (search_textがNoneの場合に使用)
            match_mode: マッチモード (advanced_searchでは直接使用されない)
            case_sensitive: 大文字小文字を区別するかどうか (インスタンス変数 self.case_sensitive に影響)
            filter_status: 翻訳ステータスのセット (インスタンス変数 self.filter_status に影響)
            filter_obsolete: 廃止エントリを含むかどうか (advanced_searchでは直接使用されない)
            update_filter: フィルタを更新するかどうか (インスタンス変数とキャッシュに影響)
            search_text: 検索テキスト (filter_keywordより優先、インスタンス変数 self.search_text に影響)

        Returns:
            List[EntryModel]: フィルタリングされたエントリのリスト
        """
        # --- フィルタ更新ロジック --- 
        needs_update = False # Start assuming no update needed unless specified or changed
        if update_filter:
            needs_update = True # If update_filter is true, always assume an update is needed initially
            
            # Update search_text only if search_text or filter_keyword is provided and differs
            current_search_text = search_text if search_text is not None else filter_keyword
            if current_search_text is not None and self.search_text != current_search_text:
                self.search_text = current_search_text
                # needs_update = True # Already set by update_filter=True
            # If both are None and self.search_text is not None, update to None
            elif current_search_text is None and self.search_text is not None:
                 self.search_text = None
                 # needs_update = True

            # Update filter_status only if filter_status parameter is provided and differs
            if filter_status is not None and self.filter_status != filter_status:
                self.filter_status = filter_status
                # needs_update = True
            # If parameter is None, don't change the instance variable unless it was already None (no real change)
            
            # Update case_sensitive only if provided and differs
            if self.case_sensitive != case_sensitive:
                self.case_sensitive = case_sensitive
                # needs_update = True

            # Update exact_match similarly (parameter missing, use self.exact_match?)
            # Assuming exact_match parameter should exist or be derived from match_mode
            # Let's assume self.exact_match is updated elsewhere or via a dedicated method
            # if self.exact_match != exact_match: self.exact_match = exact_match; needs_update = True

        # If update_filter is False, but cache is empty, we need an update
        if not update_filter and not self.filtered_entries:
            needs_update = True
            
        # Force update from cache manager overrides everything
        force_update = self.cache_manager.is_force_filter_update() if self.cache_manager else False
        if force_update:
            needs_update = True

        # --- キャッシュ利用 or DB検索 --- 
        # 更新不要でキャッシュがあればキャッシュを返す
        if not needs_update and self.filtered_entries is not None:
            logger.debug(
                "ViewerPOFileRefactored.get_filtered_entries: キャッシュされたフィルタ結果を使用"
            )
            return self.filtered_entries

        # DBからフィルタリング実行
        logger.debug(
            f"ViewerPOFileRefactored.get_filtered_entries: DBからフィルタリング実行 update_filter={update_filter}, force_update={force_update}, needs_update={needs_update}"
        )

        # advanced_search に渡すパラメータはインスタンス変数から取得する
        db_flag_conditions = self.flag_conditions.copy() if self.flag_conditions else {}

        # DatabaseAccessor.advanced_search を使用してエントリを取得
        filtered_entries_dicts = self.db_accessor.advanced_search(
            search_text=self.search_text,             # Use instance variable
            search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"], # 検索対象フィールド
            sort_column=self._sort_column,             # Use instance variable
            sort_order=self._sort_order,               # Use instance variable
            flag_conditions=db_flag_conditions,       # Use instance variable
            translation_status=self.filter_status,     # Use instance variable (assuming self.filter_status)
            exact_match=self.exact_match,              # Use instance variable
            case_sensitive=self.case_sensitive,        # Use instance variable
            limit=None,
            offset=0,
        )

        # 辞書のリストをEntryModelのリストに変換
        filtered_entries = [
            EntryModel.from_dict(cast(EntryDict, entry_dict))
            for entry_dict in filtered_entries_dicts
        ]

        # フィルタリング結果をキャッシュ
        self.filtered_entries = filtered_entries

        # 強制更新フラグをリセット
        if self.cache_manager and force_update:
            self.cache_manager.set_force_filter_update(False)

        logger.debug(
            f"ViewerPOFileRefactored.get_filtered_entries: DBから {len(filtered_entries)} 件取得"
        )
        return filtered_entries

    def get_filtered_entries_from_db(
        self,
        filter_text: str,
        filter_keyword: str,
        match_mode: str,
        case_sensitive: bool,
        filter_status: Optional[Set[str]],
        filter_obsolete: bool
    ) -> List[EntryModel]:
        """データベースからフィルタリングされたエントリのリストを取得する

        Args:
            filter_text: フィルタテキスト
            filter_keyword: フィルタキーワード
            match_mode: マッチモード
            case_sensitive: 大文字小文字を区別するかどうか
            filter_status: 翻訳ステータスのセット
            filter_obsolete: 廃止エントリを含むかどうか

        Returns:
            List[EntryModel]: フィルタリングされたエントリのリスト
        """
        # データベースからフィルタリングされたエントリを取得
        entries_dict = self.db_accessor.get_filtered_entries(
            filter_text=filter_text,
            filter_keyword=filter_keyword,
            match_mode=match_mode,
            case_sensitive=case_sensitive,
            filter_status=filter_status,
            filter_obsolete=filter_obsolete
        )

        # リストからEntryModelオブジェクトのリストに変換
        entries = [EntryModel.from_dict(entry_dict) for entry_dict in entries_dict]

        return entries
