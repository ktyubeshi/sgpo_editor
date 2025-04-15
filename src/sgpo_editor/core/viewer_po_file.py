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

logger = logging.getLogger(__name__)


class ViewerPOFile:
    def get_entries_by_keys(self, keys: list[str]) -> dict[str, 'EntryModel']:
        """複数のキーに対応するエントリを一括取得"""
        return self.retriever.get_entries_by_keys(keys)

    def get_entry_by_number(self, position: int) -> Optional[EntryModel]:
        """エントリ番号（インデックス）からエントリを取得"""
        return self.retriever.get_entry_at(position)

    """POファイルを読み込み、表示するためのクラス

    @property
    def search_text(self) -> str:
        return self.filter.search_text

    @search_text.setter
    def search_text(self, value: str):
        self.filter.search_text = value

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

    def get_entry_at(self, position: int) -> Optional[EntryModel]:
        """位置（インデックス）からエントリを取得する

        Args:
            position: エントリの位置（インデックス）

        Returns:
            Optional[EntryModel]: 指定された位置のエントリ。見つからない場合はNone
        """
        return self.retriever.get_entry_at(position)

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
            search_text, sort_column, sort_order, flag_conditions, translation_status
        )

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

        Returns:
            List[EntryModel]: フィルタ条件に一致するエントリのリスト
        """
        entries = self.filter.get_filtered_entries(
            filter_text, filter_keyword, match_mode, case_sensitive,
            filter_status, filter_obsolete, update_filter, search_text
        )
        # FilterComponent 側の filter_status を同期
        self.filter_status = self.filter.filter_status
        return entries

    def update_entry(self, key: str, field: str, value: Any) -> bool:
        """エントリの特定のフィールドを更新する

        Args:
            key: 更新するエントリのキー
            field: 更新するフィールド名
            value: 設定する値

        Returns:
            bool: 更新が成功した場合はTrue、失敗した場合はFalse
        """
        return self.updater.update_entry(key, field, value)

    def update_entry_model(self, entry: EntryModel) -> bool:
        """エントリモデル全体を更新する

        Args:
            entry: 更新するエントリモデル

        Returns:
            bool: 更新が成功した場合はTrue、失敗した場合はFalse
        """
        return self.updater.update_entry_model(entry)

    def set_flag(self, key: str, flag: str, value: bool = True) -> bool:
        """エントリのフラグを設定または解除する

        Args:
            key: 対象エントリのキー
            flag: 設定するフラグ名
            value: フラグ値（Trueで設定、Falseで解除）

        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        return self.updater.set_flag(key, flag, value)

    def toggle_flag(self, key: str, flag: str) -> bool:
        """エントリのフラグを切り替える

        Args:
            key: 対象エントリのキー
            flag: 切り替えるフラグ名

        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        return self.updater.toggle_flag(key, flag)

    def get_statistics(self) -> StatisticsInfo:
        """翻訳統計情報を取得する

        Returns:
            StatisticsInfo: 統計情報を含む辞書
        """
        return self.stats.get_statistics()

    def get_flag_statistics(self) -> Dict[str, int]:
        """すべてのフラグの統計情報を取得する

        Returns:
            Dict[str, int]: フラグ名とそのフラグを持つエントリ数の辞書
        """
        return self.stats.get_flag_statistics()

    def get_entry_counts_by_type(self) -> Dict[str, int]:
        """タイプ別のエントリ数を取得する

        Returns:
            Dict[str, int]: タイプとエントリ数の辞書
        """
        return self.stats.get_entry_counts_by_type()

    def get_unique_msgid_count(self) -> int:
        """ユニークなmsgid（原文）の数を取得する

        Returns:
            int: ユニークなmsgidの数
        """
        return self.retriever.get_unique_msgid_count()

    def get_filename(self) -> str:
        """POファイルの名前を取得する

        Returns:
            str: ファイル名（読み込まれていない場合は空文字列）
        """
        return self.base.get_filename()

    async def save(self, path: Optional[Union[str, Path]] = None) -> bool:
        """POファイルを保存する

        Args:
            path: 保存先のパス (Noneの場合は現在のパスを使用)

        Returns:
            bool: 保存が成功した場合はTrue、失敗した場合はFalse
        """
        success = await self.stats.save(path)
        if success:
            self.set_modified(False)
        return success

    def enable_cache(self, enabled: bool = True) -> None:
        """キャッシュ機能の有効/無効を設定する

        Args:
            enabled: キャッシュを有効にするかどうか
        """
        self.base.enable_cache(enabled) 