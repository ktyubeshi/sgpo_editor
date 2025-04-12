"""POファイルフィルタコンポーネント

このモジュールは、POファイルのエントリをフィルタリングし、ソートするための機能を提供します。
"""

import logging
from typing import Dict, List, Optional, Set, Union

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.constants import TranslationStatus
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import FlagConditions, FilterSettings

logger = logging.getLogger(__name__)


class FilterComponent:
    """POファイルのフィルタリングとソート機能を提供するコンポーネント

    このクラスは、エントリのフィルタリングとソートを担当します。
    """

    def __init__(
        self,
        db_accessor: DatabaseAccessor,
        cache_manager: EntryCacheManager,
    ):
        """初期化

        Args:
            db_accessor: データベースアクセサのインスタンス
            cache_manager: キャッシュマネージャのインスタンス
        """
        self.db_accessor = db_accessor
        self.cache_manager = cache_manager

        # フィルタリング関連の状態
        self.filtered_entries: List[EntryModel] = []
        self.search_text: str = ""
        self.sort_column: str = "position"
        self.sort_order: str = "ASC"
        self.flag_conditions: FlagConditions = {}
        self.translation_status: Optional[str] = None
        
        # フィルタ関連のフラグ
        self.exact_match: bool = False
        self.case_sensitive: bool = False

        # filter_status は translation_status の別名（後方互換性のため）
        self.filter_status: Optional[Set[str]] = None
        
        logger.debug("FilterComponent: 初期化完了")

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
        logger.debug(
            f"FilterComponent.set_filter: search_text={search_text}, "
            f"sort_column={sort_column}, sort_order={sort_order}, "
            f"flag_conditions={flag_conditions}, translation_status={translation_status}"
        )

        # 検索テキスト
        self.search_text = search_text or ""

        # ソート条件
        self.sort_column = sort_column or "position"
        self.sort_order = sort_order or "ASC"

        # フラグ条件
        self.flag_conditions = flag_conditions or {}

        # 翻訳状態
        self.translation_status = translation_status

        # キャッシュを無効化
        if self.cache_manager:
            self.cache_manager.set_force_filter_update(True)
            self.cache_manager.invalidate_filter_cache()
        
        # フィルタリング結果をリセット
        self.filtered_entries = []

    def set_sort_criteria(self, column: str, order: str) -> None:
        """ソート条件を設定する

        Args:
            column: ソートする列名
            order: ソート順序 ('ASC' or 'DESC')
        """
        logger.debug(f"FilterComponent.set_sort_criteria: column={column}, order={order}")
        valid_order = order.upper() if order else "ASC"
        if valid_order not in ["ASC", "DESC"]:
            valid_order = "ASC"
            
        if self.sort_column != column or self.sort_order != valid_order:
            self.sort_column = column
            self.sort_order = valid_order
            
            # キャッシュを無効化
            if self.cache_manager:
                self.cache_manager.set_force_filter_update(True)
                self.cache_manager.invalidate_filter_cache()
            
            # フィルタリング結果をリセット
            self.filtered_entries = []

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
        # フィルタ条件をセットアップ
        if update_filter:
            # search_textはデータを流用しているケースもあるので
            # Noneでなければ優先的に使用する
            if search_text is not None:
                self.search_text = search_text
            
            # その他のパラメータも更新
            self.exact_match = match_mode == "完全一致"
            self.case_sensitive = case_sensitive
            
            # 内部キャッシュクリア
            self.filtered_entries = []

        # キャッシュからフィルタリング結果を取得
        cached_entries = None
        force_update = self.cache_manager.get_force_filter_update()
        
        if not force_update and self.filtered_entries:
            # 既に計算済みのフィルタ結果がある場合はそれを使用
            return self.filtered_entries
        
        if not force_update:
            # キャッシュ上の計算済みフィルタ結果をチェック
            cached_entries = self.cache_manager.get_filter_cache()
            if cached_entries is not None:
                # キャッシュヒット
                logger.debug(f"FilterComponent.get_filtered_entries: キャッシュヒット, {len(cached_entries)}件")
                self.filtered_entries = cached_entries
                return self.filtered_entries

        # DB上でフィルタリングを実行
        logger.debug("FilterComponent.get_filtered_entries: DBでフィルタリングを実行")
        db_filtered = self.get_filtered_entries_from_db(
            filter_text, filter_keyword, match_mode, 
            case_sensitive, filter_status, filter_obsolete
        )
        
        # 結果をキャッシュに保存
        if self.cache_manager:
            self.cache_manager.set_filter_cache(db_filtered)
            self.cache_manager.set_force_filter_update(False)
        
        self.filtered_entries = db_filtered
        return self.filtered_entries

    def get_filtered_entries_from_db(
        self,
        filter_text: str,
        filter_keyword: Optional[str],
        match_mode: str,
        case_sensitive: bool,
        filter_status: Optional[Set[str]],
        filter_obsolete: bool
    ) -> List[EntryModel]:
        """データベースから直接フィルタリングされたエントリを取得する

        Args:
            filter_text: フィルタテキスト
            filter_keyword: フィルタキーワード
            match_mode: 一致モード（'部分一致'または'完全一致'）
            case_sensitive: 大文字小文字を区別するかどうか
            filter_status: フィルタするステータスのセット
            filter_obsolete: 廃止されたエントリをフィルタするかどうか

        Returns:
            List[EntryModel]: フィルタリングされたエントリのリスト
        """
        # 検索とステータスの条件を構築
        search_condition = {}
        
        if self.search_text:
            search_condition = {
                "text": self.search_text,
                "exact_match": self.exact_match,
                "case_sensitive": self.case_sensitive,
            }
        
        status_condition = None
        if self.translation_status:
            if self.translation_status == TranslationStatus.UNTRANSLATED:
                status_condition = {
                    "field": "msgstr",
                    "value": "",
                    "operator": "="
                }
            elif self.translation_status == TranslationStatus.TRANSLATED:
                status_condition = {
                    "field": "msgstr",
                    "value": "",
                    "operator": "!="
                }
        
        # フラグ条件を構築
        flag_conditions = {}
        for flag, value in self.flag_conditions.items():
            if value is not None:  # True/False両方を条件として扱う
                flag_conditions[flag] = value
        
        # データベースからエントリを取得
        entries_dict = self.db_accessor.get_filtered_entries(
            filter_text=search_condition,
            filter_keyword=None,  # filter_keywordは使用しない
            match_mode="部分一致",
            case_sensitive=False,
            filter_status=status_condition,
            filter_obsolete=True,
            search_text=search_condition
        )
        
        # 既にEntryModelのリストが返されるので変換は不要
        return entries_dict

    def get_available_flags(self) -> Set[str]:
        """利用可能なすべてのフラグのセットを取得する

        Returns:
            Set[str]: 利用可能なフラグのセット
        """
        if not self.db_accessor:
            return set()
        return self.db_accessor.get_all_flags()

    def get_sort_column(self) -> str:
        """現在のソート列を取得する

        Returns:
            str: ソート列名
        """
        return self.sort_column

    def get_sort_order(self) -> str:
        """現在のソート順序を取得する

        Returns:
            str: ソート順序 ('ASC' or 'DESC')
        """
        return self.sort_order 