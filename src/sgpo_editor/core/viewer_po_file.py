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
        # Initialize instance search_text and filter_status
        self.search_text = self.filter.search_text
        self.filter_status = self.filter.translation_status

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
        """セットまたはリセット検索キーワード"""
        self.search_text = keyword
        # Keep filter_status unchanged

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

    def update_entry(self, key: str, field: str, value: Any) -> bool:
        """エントリの特定フィールドを更新する（UpdaterComponentへ委譲）"""
        return self.updater.update_entry(key, field, value)

    def get_filtered_entries(
        self,
        criteria: "SearchCriteria"
    ) -> List[EntryModel]:
        """フィルタ条件に一致するエントリを取得する

        Args:
            criteria: 検索条件
            case_sensitive: 大文字小文字を区別するかどうか
            filter_status: フィルタするステータスのセット
            filter_obsolete: 廃止されたエントリをフィルタするかどうか
            update_filter: フィルタ条件を更新するかどうか
            search_text: 検索テキスト（update_filter=Trueの場合に使用）
            translation_status: 翻訳状態フィルタ

        Returns:
            List[EntryModel]: フィルタ条件に一致するエントリのリスト
        """
        # criteriaから値を取得
        filter_status = getattr(criteria, 'filter_status', None)
        translation_status = getattr(criteria, 'filter', None)
        filter_keyword = getattr(criteria, 'filter_keyword', None)
        print(f"DEBUG: translation_status(from filter)={translation_status}")  # デバッグ用
        match_mode = getattr(criteria, 'match_mode', 'partial')
        case_sensitive = getattr(criteria, 'case_sensitive', False)
        filter_obsolete = getattr(criteria, 'filter_obsolete', False)
        update_filter = getattr(criteria, 'update_filter', False)
        search_text = getattr(criteria, 'search_text', None)

        # キャッシュ制御: update_filter=Falseかつキャッシュがあれば返却
        if not update_filter and getattr(self, 'filtered_entries', None):
            return self.filtered_entries
        # filter_keyword無指定時はインスタンスsearch_textを使用
        effective_keyword = (
            self.search_text if filter_keyword is None else filter_keyword
        )
        # テスト要件: キーワードや翻訳状態指定時はadvanced_searchを呼ぶ
        if filter_keyword or filter_status or search_text or translation_status:
            # advanced_searchを呼ぶ
            if translation_status is not None:
                translation_status_arg = translation_status
            elif isinstance(filter_status, set) and len(filter_status) == 1:
                translation_status_arg = list(filter_status)[0]
            else:
                translation_status_arg = None
            # translation_statusを必ずkwargsに含める（Noneでも明示的に渡す）
            entries_data = self.db_accessor.advanced_search(
                search_text=filter_keyword or search_text or "",
                search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"],
                sort_column="position",
                sort_order="ASC",
                flag_conditions={},
                exact_match=match_mode == "完全一致",
                case_sensitive=case_sensitive,
                limit=None,
                offset=0,
                translation_status=translation_status_arg
            )
        else:
            # 従来通り
            entries_data = self.db_accessor.get_filtered_entries(
                filter_text=filter_text,
                filter_keyword=effective_keyword or "",
                case_sensitive=case_sensitive,
                filter_status=filter_status,
                filter_obsolete=filter_obsolete,
            )
        entries = []
        for d in entries_data:
            entries.append(
                EntryModel.model_validate(d) if isinstance(d, dict) else d
            )
        self.filtered_entries = entries
        return entries

    async def save(self, path: Union[str, Path]) -> bool:
        try:
            logger.debug(f"ViewerPOFile.save: Attempting to save to path {path}")
            success = await self.base.save(path)
            if success:
                logger.debug("ViewerPOFile.save: Save successful, setting modified to False")
                self.set_modified(False)  # Reset modified flag on successful save
            else:
                logger.error(f"ViewerPOFile.save: Save failed for path {path}")
            return success
        except Exception as e:
            logger.error(f"ViewerPOFile.save: Error during save - {e}")
            return False
