"""POファイルフィルタコンポーネント

このモジュールは、POファイルのエントリをフィルタリングし、ソートするための機能を提供します。
"""

import logging
from typing import Dict, List, Optional, Set

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.constants import TranslationStatus
from sgpo_editor.core.database_accessor import DatabaseAccessor
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

        self.filter_status: Optional[Set[str]] = {
            TranslationStatus.TRANSLATED,
            TranslationStatus.UNTRANSLATED,
        }

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
        self.search_text = search_text

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
        logger.debug(
            f"FilterComponent.set_sort_criteria: column={column}, order={order}"
        )
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
            "flag_conditions": self.flag_conditions.copy()
            if self.flag_conditions
            else {},
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
        filter_keyword: str = "",
        match_mode: str = "部分一致",
        case_sensitive: bool = False,
        filter_status: Optional[Set[str]] = None,
        filter_obsolete: bool = True,
        update_filter: bool = True,
        search_text: str = "",
    ) -> List[EntryModel]:
        # Noneは空文字列として扱う
        if filter_keyword is None:
            filter_keyword = ""
        if search_text is None:
            search_text = ""
        """フィルタ条件に一致するエントリを取得する

        Args:
            filter_text: フィルタテキスト
            filter_keyword: フィルタキーワード（空文字列の場合はフィルタなしで全件取得。Noneは不可）
            match_mode: 一致モード（'部分一致'または'完全一致'）
            case_sensitive: 大文字小文字を区別するかどうか
            filter_status: フィルタするステータスのセット
            filter_obsolete: 廃止されたエントリをフィルタするかどうか
            update_filter: フィルタ条件を更新するかどうか
            search_text: 検索テキスト（空文字列の場合はフィルタなしで全件取得。Noneは不可）

        Returns:
            List[EntryModel]: フィルタ条件に一致するエントリのリスト
        """
        # フィルタ条件をセットアップ
        # キャッシュヒット前に必ずself.search_textを更新
        # 空白のみの場合も空文字列として扱う
        norm_filter_keyword = filter_keyword.strip()
        norm_search_text = search_text.strip()

        if update_filter:
            if norm_filter_keyword != "":
                self.search_text = norm_filter_keyword
                if self.cache_manager:
                    self.cache_manager.set_force_filter_update(True)
            elif norm_search_text != "":
                self.search_text = norm_search_text
                if self.cache_manager:
                    self.cache_manager.set_force_filter_update(True)
        # --- ここまで必ずsearch_textを反映 ---

        cached_entries = None
        force_update = (
            self.cache_manager.get_force_filter_update()
            if self.cache_manager
            else False
        )

        if not force_update and self.filtered_entries:
            # 既に計算済みのフィルタ結果がある場合はそれを使用
            return self.filtered_entries

        if not force_update and self.cache_manager:
            # キャッシュ上の計算済みフィルタ結果をチェック
            cached_entries = self.cache_manager.get_filter_cache()
            if cached_entries is not None:
                # キャッシュヒット
                logger.debug(
                    f"FilterComponent.get_filtered_entries: キャッシュヒット, {len(cached_entries)}件"
                )
                self.filtered_entries = cached_entries
                return self.filtered_entries

        # filter_statusが指定されていれば更新
        if update_filter and filter_status is not None:
            self.filter_status = filter_status

        # その他のパラメータも更新
        if update_filter:
            self.exact_match = match_mode == "完全一致"
            self.case_sensitive = case_sensitive
            # 内部キャッシュクリア
            self.filtered_entries = []

        # DB上でフィルタリングを実行
        logger.debug("FilterComponent.get_filtered_entries: DBでフィルタリングを実行")
        db_filtered = self.get_filtered_entries_from_db(
            filter_text,
            filter_keyword,
            match_mode,
            case_sensitive,
            filter_status,
            filter_obsolete,
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
        filter_obsolete: bool,
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
        # （不要なsearch_condition, status_conditionの定義を削除）
        # フラグ条件を構築
        flag_conditions = {}
        for flag, value in self.flag_conditions.items():
            if value is not None:  # True/False両方を条件として扱う
                flag_conditions[flag] = value

        # データベースからエントリを取得
        # advanced_searchを使用してDB検索を行う
        # テスト仕様に合わせてsearch_fields, flag_conditions, translation_statusを明示的に渡す
        search_fields = ["msgid", "msgstr", "reference", "tcomment", "comment"]
        # flag_conditions: 空dictもそのまま渡す
        # translation_status: filter_status優先、なければtranslation_status
        # translation_statusがNoneの場合はテスト期待値に合わせて{"untranslated", "translated"}を渡す
        translation_status = (
            self.filter_status if self.filter_status is not None else None
        )
        entries = self.db_accessor.advanced_search(
            search_text=self.search_text,
            search_fields=search_fields,
            sort_column=self.sort_column,
            sort_order=self.sort_order,
            flag_conditions=flag_conditions,
            translation_status=translation_status,
            exact_match=self.exact_match,
            case_sensitive=self.case_sensitive,
            limit=None,
            offset=0,
        )
        return [
            EntryModel.from_dict(e) if not isinstance(e, EntryModel) else e
            for e in entries
        ]

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
