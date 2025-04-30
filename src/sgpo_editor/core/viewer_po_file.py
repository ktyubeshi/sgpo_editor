"""POファイルビューア

このモジュールは、POファイルを読み込み、表示、編集するための機能を提供します。
各機能コンポーネントを内部に保持するコンポジション構造で実装されています。
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, Any

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.po_components.base import POFileBaseComponent
from sgpo_editor.core.po_components.filter import FilterComponent
from sgpo_editor.core.po_components.retriever import EntryRetrieverComponent
from sgpo_editor.core.po_components.stats import StatsComponent
from sgpo_editor.core.po_components.updater import UpdaterComponent
from sgpo_editor.core.po_factory import POLibraryType
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import FilterSettings, StatisticsInfo
from sgpo_editor.core.constants import TranslationStatus

logger = logging.getLogger(__name__)


class ViewerPOFile:
    @property
    def path(self):
        return self.base.path

    def get_stats(self):
        """統計情報を取得する"""
        return self.stats.get_statistics()

    def get_entries_by_keys(self, keys: list[str]) -> dict[str, "EntryModel"]:
        """複数のキーに対応するエントリを一括取得"""
        return self.retriever.get_entries_by_keys(keys)

    def get_entry_by_number(self, position: int) -> Optional[EntryModel]:
        """エントリ番号（インデックス）からエントリを取得"""
        return self.retriever.get_entry_at(position)

    def get_entry_at(self, position: int) -> Optional[EntryModel]:
        """位置（インデックス）からエントリを取得"""
        return self.retriever.get_entry_at(position)

    @property
    def search_text(self) -> Optional[str]:
        value = self.filter.search_text
        logger.debug(f"ViewerPOFile search_text getter called, returning: {value}")
        return value if value is not None else ""

    @search_text.setter
    def search_text(self, value: Optional[str]):
        self.filter.search_text = value
        logger.debug(f"ViewerPOFile search_text set to: {value}")

    @property
    def translation_status(self) -> Optional[str]:
        return self.filter.translation_status

    @translation_status.setter
    def translation_status(self, value: Optional[str]):
        self.filter.translation_status = value

    """POファイルを読み込み、表示するためのクラス

    このクラスは、コンポジションパターンを使用して実装されており、
    各機能コンポーネントを内部に保持し、その機能を利用します。

    主要コンポーネント:
    - POFileBaseComponent: POファイルの読み込みと基本操作
    - EntryRetrieverComponent: エントリの取得と検索
    - FilterComponent: エントリのフィルタリングとソート
    - UpdaterComponent: エントリの更新と変更管理
    - StatsComponent: 統計情報と保存機能

    依存性注入パターンによりDatabaseAccessorとEntryCacheManagerを外部から注入できるため、
    - 単体テストが容易（モックやスタブの使用が可能）
    - 異なるデータベース実装やキャッシュ戦略への切り替えが容易
    - 実行時の設定に応じた振る舞いの変更が可能
    になっています。
    """

    def __init__(
        self,
        library_type: POLibraryType = POLibraryType.SGPO,
        db_accessor: Optional[DatabaseAccessor] = None,
        cache_manager: Optional[EntryCacheManager] = None,
    ):
        """初期化

        Args:
            library_type: 使用するPOライブラリの種類
            db_accessor: データベースアクセサのインスタンス（省略時は内部で生成）
            cache_manager: キャッシュマネージャのインスタンス（省略時は内部で生成）
        """
        # DBとキャッシュの共有インスタンスを作成
        self.db_accessor = db_accessor
        self.cache_manager = cache_manager or EntryCacheManager()

        # 各コンポーネントの初期化
        self.base = POFileBaseComponent(
            library_type=library_type,
            db_accessor=self.db_accessor,
            cache_manager=self.cache_manager,
        )

        # データベースアクセサが指定されていない場合は、BaseComponentから取得
        if not self.db_accessor:
            self.db_accessor = self.base.db_accessor

        # 各コンポーネントの初期化
        self.retriever = EntryRetrieverComponent(
            db_accessor=self.db_accessor,
            cache_manager=self.cache_manager,
        )

        self.filter = FilterComponent(
            db_accessor=self.db_accessor,
            cache_manager=self.cache_manager,
        )
        self.filter.search_text = ""  # Explicitly ensure search_text is an empty string
        self.filter.translation_status = {TranslationStatus.TRANSLATED, TranslationStatus.UNTRANSLATED}  # Set default translation status
        logger.debug(f"ViewerPOFile initialized with search_text: {self.filter.search_text}")

        self.updater = UpdaterComponent(
            db_accessor=self.db_accessor,
            cache_manager=self.cache_manager,
        )

        self.stats = StatsComponent(
            db_accessor=self.db_accessor,
            cache_manager=self.cache_manager,
            library_type=library_type,
        )

        logger.debug("ViewerPOFile: コンポジション構造の初期化完了")

    async def load(self, path: Union[str, Path]) -> None:
        """POファイルを非同期で読み込む

        Args:
            path: 読み込むPOファイルのパス
        """
        # POFileBaseComponentの読み込み機能を利用
        await self.base.load(path)

        # 他のコンポーネントにも情報を共有
        self.stats.set_path(self.base.path)
        self.stats.set_metadata(self.base.metadata)

        logger.debug(f"ViewerPOFile.load: {path} の読み込みが完了しました")

    def get_all_entries(self) -> List[EntryModel]:
        """すべてのエントリを取得する

        Returns:
            List[EntryModel]: すべてのエントリのリスト
        """
        return self.retriever.get_all_entries()

    def reset_filter(self) -> None:
        """フィルタをリセットする"""
        self.filter.reset_filter()

    def is_loaded(self) -> bool:
        """ファイルが読み込まれているかを返す

        Returns:
            bool: ファイルが読み込まれている場合はTrue
        """
        return self.base.is_loaded()

    def is_modified(self) -> bool:
        """ファイルが変更されているかを返す

        Returns:
            bool: ファイルが変更されている場合はTrue
        """
        return self.base.is_modified() or self.updater.is_modified()

    def set_modified(self, modified: bool = True) -> None:
        """変更フラグを設定する

        Args:
            modified: 設定する変更フラグの値
        """
        self.base.set_modified(modified)
        self.updater.set_modified(modified)

    def get_entry(self, key: str) -> Optional[EntryModel]:
        """エントリキーからエントリを取得する

        Args:
            key: エントリキー

        Returns:
            Optional[EntryModel]: 見つかったエントリ、または None
        """
        return self.get_entry_by_key(key)

    def get_entry_by_key(self, key: str) -> Optional[EntryModel]:
        """エントリキーからエントリを取得する

        Args:
            key: エントリキー

        Returns:
            Optional[EntryModel]: 見つかったエントリ、または None
        """
        return self.retriever.get_entry_by_key(key)

    def get_entry_position(self, position: int) -> Optional[EntryModel]:
        """エントリ番号からエントリを取得する

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
        return self.retriever.count_entries()

    def get_available_flags(self) -> Set[str]:
        """利用可能なすべてのフラグのセットを取得する

        Returns:
            Set[str]: 利用可能なフラグのセット
        """
        return self.filter.get_available_flags()

    def get_filters(self) -> FilterSettings:
        """現在のフィルタ設定を取得する

        Returns:
            FilterSettings: 現在のフィルタ設定
        """
        return self.filter.get_filters()

    def set_filter(
        self,
        search_text: str = "",
        sort_column: str = "position",
        sort_order: str = "ASC",
        flag_conditions: Optional[Dict[str, bool]] = None,
        translation_status: Optional[str] = None,
    ) -> None:
        """フィルタ条件を設定する

        Args:
            search_text: 検索テキスト
            sort_column: ソート列
            sort_order: ソート順序 ("ASC" or "DESC")
            flag_conditions: フラグ条件の辞書 (フラグ名 -> 値)
            translation_status: 翻訳状態フィルタ
        """
        self.filter.set_filter(
            search_text=search_text,
            sort_column=sort_column,
            sort_order=sort_order,
            flag_conditions=flag_conditions,
            translation_status=translation_status,
        )
        self.search_text = search_text
        if translation_status is not None:
            self.translation_status = translation_status

    def set_filter_keyword(self, keyword: str) -> None:
        """フィルタキーワードを設定する

        Args:
            keyword: フィルタキーワード
        """
        self.filter.set_filter(search_text=keyword)
        self.search_text = keyword
        if self.cache_manager:
            self.cache_manager.set_force_filter_update(True)
            self.cache_manager.invalidate_filter_cache()

    def set_sort_criteria(self, column: str, order: str) -> None:
        """ソート条件を設定する

        Args:
            column: ソートする列名
            order: ソート順序 ('ASC' or 'DESC')
        """
        self.filter.set_sort_criteria(column, order)

    def get_sort_column(self) -> str:
        """現在のソート列を取得する

        Returns:
            str: ソート列名
        """
        return self.filter.get_sort_column()

    def get_sort_order(self) -> str:
        """現在のソート順序を取得する

        Returns:
            str: ソート順序 ('ASC' or 'DESC')
        """
        return self.filter.get_sort_order()

    def invalidate_cache(self) -> None:
        """キャッシュを無効化する"""
        self.updater.invalidate_cache()

    def prefetch_entries(self, keys: List[str]) -> None:
        """指定されたキーのエントリをプリフェッチする

        Args:
            keys: プリフェッチするエントリのキーのリスト
        """
        self.retriever.prefetch_entries(keys)

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
        translation_status: Optional[Set[str]] = None,
    ) -> List[EntryModel]:
        """フィルタ条件に一致するエントリを取得する

        Args:
            filter_text: フィルタテキスト
            filter_keyword: フィルタキーワード
            match_mode: 一致モード（'部分一致'または'完全一致'）
            case_sensitive: 大文字小文字を区別するかどうか
            filter_status: フィルタするステータスのセット
            filter_obsolete: 廃止されたエントリをフィルタするかどうか
            update_filter: フィルタ条件を更新するかどうか
            search_text: 検索テキスト（update_filter=Trueの場合に使用）
            translation_status: 翻訳状態フィルタ

        Returns:
            List[EntryModel]: フィルタ条件に一致するエントリのリスト
        """
        if update_filter:
            if search_text is not None:
                self.search_text = search_text
            if filter_keyword is not None:
                self.filter.set_filter(search_text=filter_keyword)
            else:
                # Reset only the keyword filter if previous search_text existed
                if self.search_text:
                    self.search_text = ""
                    if self.cache_manager:
                        self.cache_manager.set_force_filter_update(True)
                        self.cache_manager.invalidate_filter_cache()

            # 一致条件
            self.filter.exact_match = match_mode == "完全一致"
            self.filter.case_sensitive = case_sensitive

            # フィルタ条件
            if filter_status is not None:
                self.filter_status = filter_status
            self.filter_obsolete = filter_obsolete

            if translation_status is not None:
                self.translation_status = translation_status
                self.filter_status = translation_status  # Update filter_status with the provided translation_status
            else:
                # Ensure a default translation status if not set
                if not hasattr(self.filter, 'translation_status') or not self.filter.translation_status:
                    self.filter.translation_status = None  # Changed from set to None to match expected type

        # フィルタ条件を適用してエントリを取得
        entries = self.filter.get_filtered_entries(
            filter_text=filter_text,
            filter_keyword=filter_keyword,
            match_mode=match_mode,
            case_sensitive=case_sensitive,
            filter_status=self.filter_status if hasattr(self, 'filter_status') else None,
            filter_obsolete=filter_obsolete,
            update_filter=update_filter,
            search_text=self.search_text if hasattr(self, 'search_text') else None
        )
        
        # FilterComponent 側の filter_status を同期 (only if translation_status was not provided)
        if translation_status is None:
            self.filter_status = self.filter.filter_status
        return entries
