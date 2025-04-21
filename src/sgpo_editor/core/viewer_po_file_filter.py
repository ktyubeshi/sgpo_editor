"""POファイルフィルタリングクラス

このモジュールは、POファイルのエントリをフィルタリングするための機能を提供します。
ViewerPOFileEntryRetrieverを継承し、フィルタリングに関連する機能を実装します。
"""

import logging
from typing import List, Optional, cast

from sgpo_editor.core.constants import TranslationStatus
from sgpo_editor.core.viewer_po_file_entry_retriever import ViewerPOFileEntryRetriever
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import FlagConditions

logger = logging.getLogger(__name__)


class ViewerPOFileFilter(ViewerPOFileEntryRetriever):
    """POファイルのエントリをフィルタリングするためのクラス

    このクラスは、ViewerPOFileEntryRetrieverを継承し、フィルタリングに関連する機能を実装します。
    """

    def _set_flag_conditions_from_status(self, status: str) -> None:
        """翻訳ステータスからフラグ条件を設定する

        Args:
            status: TranslationStatus定数
        """
        logger.debug(
            f"ViewerPOFileFilter._set_flag_conditions_from_status: ステータス={status}"
        )

        # フラグ条件をリセット
        self.flag_conditions = cast(FlagConditions, {})

        # ステータスに応じてフラグ条件を設定
        if status == TranslationStatus.TRANSLATED:
            # 翻訳済み: msgstrが空でなく、fuzzyでない
            self.flag_conditions = cast(
                FlagConditions,
                {
                    "msgstr_not_empty": True,
                    "fuzzy": False,
                },
            )
        elif status == TranslationStatus.UNTRANSLATED:
            # 未翻訳: msgstrが空で、fuzzyでない
            self.flag_conditions = cast(
                FlagConditions,
                {
                    "msgstr_empty": True,
                    "fuzzy": False,
                },
            )
        elif status == TranslationStatus.FUZZY:
            # fuzzy: fuzzyフラグがある
            self.flag_conditions = cast(
                FlagConditions,
                {
                    "fuzzy": True,
                },
            )
        elif status == TranslationStatus.FUZZY_OR_UNTRANSLATED:
            # fuzzyまたは未翻訳: fuzzyフラグがあるか、msgstrが空
            self.flag_conditions = cast(
                FlagConditions,
                {
                    "fuzzy_or_msgstr_empty": True,
                },
            )
        # ALL（すべて）の場合は条件なし

        # 翻訳ステータスを保存
        self.translation_status = status

    def _generate_filter_cache_key(self) -> str:
        """現在のフィルタ条件からキャッシュキーを生成する

        Returns:
            str: キャッシュキー
        """
        # フィルタ条件の各要素を文字列化
        translation_status_str = (
            str(self.translation_status) if self.translation_status else "None"
        )
        search_text_str = str(self.search_text) if self.search_text else "None"
        sort_column_str = str(self.sort_column) if self.sort_column else "None"
        sort_order_str = str(self.sort_order) if self.sort_order else "None"
        flag_conditions_str = (
            str(sorted(self.flag_conditions.items()))
            if self.flag_conditions
            else "None"
        )

        # キャッシュキーを生成（フィルタ条件の組み合わせ）
        cache_key = (
            f"filter_{translation_status_str}_{search_text_str}_{sort_column_str}_"
            f"{sort_order_str}_{flag_conditions_str}"
        )
        return cache_key

    def get_filtered_entries(
        self,
        update_filter: bool = False,
        translation_status: Optional[str] = None,
        filter_keyword: str = "",
    ) -> List[EntryModel]:
        """フィルタ条件に合ったエントリーを取得する

        Args:
            update_filter: フィルター条件を強制的に更新するフラグ
            translation_status: 翻訳ステータス（TranslationStatus定数を使用）
            filter_keyword: 検索キーワード（空文字列の場合はフィルタなしで全件取得。Noneは不可）

        Returns:
            フィルター条件に一致するEntryModelのリスト
        """
        logger.debug(
            f"ViewerPOFileFilter.get_filtered_entries: 開始 update_filter={update_filter}, "
            f"translation_status={translation_status}, filter_keyword={filter_keyword}, "
            f"_force_filter_update={self._force_filter_update}"
        )
        # フィルタ条件の更新
        if update_filter or translation_status is not None:
            if translation_status is not None:
                self.translation_status = translation_status
                self._set_flag_conditions_from_status(translation_status)
            self._force_filter_update = True

        # 検索キーワードの更新
        if filter_keyword != "":
            self.search_text = filter_keyword
            self._force_filter_update = True

        # キャッシュキーの生成
        cache_key = self._generate_filter_cache_key()
        logger.debug(
            f"ViewerPOFileFilter.get_filtered_entries: キャッシュキー={cache_key}"
        )

        # キャッシュからフィルタ結果を取得（強制更新でない場合）
        if not self._force_filter_update and self.filtered_entries:
            logger.debug(
                "ViewerPOFileFilter.get_filtered_entries: キャッシュされたフィルタ結果を使用"
            )
            return self.filtered_entries

        # データベースからフィルタリングされたエントリを取得
        db_filter_conditions = cast(FlagConditions, {})

        # 翻訳ステータスに応じたフィルタ条件を設定
        if self.flag_conditions:
            db_filter_conditions = cast(FlagConditions, dict(self.flag_conditions))

        # 検索キーワードがある場合は検索条件を追加
        search_text_param = None
        if self.search_text:
            search_text_param = self.search_text

        # ソート条件
        sort_column = self.sort_column or "position"
        sort_order = self.sort_order or "ASC"

        # データベースからフィルタリングされたエントリを取得
        filtered_entries_dict = self.db_accessor.get_filtered_entries(
            search_text=search_text_param,
            flag_conditions=db_filter_conditions,
            sort_column=sort_column,
            sort_order=sort_order,
            translation_status=self.translation_status,
        )

        filtered_entries = []
        for entry_dict in filtered_entries_dict:
            entry = EntryModel.from_dict(entry_dict)
            filtered_entries.append(entry)

        # フィルタ結果を保存
        self.filtered_entries = filtered_entries
        self._force_filter_update = False

        logger.debug(
            f"ViewerPOFileFilter.get_filtered_entries: フィルタ結果件数={len(filtered_entries)}"
        )
        return filtered_entries

    def set_filter(
        self,
        search_text: str = "",
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[FlagConditions] = None,
        translation_status: Optional[str] = None,
    ) -> None:
        """フィルタを設定する

        Args:
            search_text: 検索キーワード（空文字列の場合はフィルタなしで全件取得。Noneは不可）
            sort_column: ソート列
            sort_order: ソート順序
            flag_conditions: フラグ条件
            translation_status: 翻訳ステータス
        """
        logger.debug(
            f"ViewerPOFileFilter.set_filter: translation_status={translation_status}, search_text={search_text}, "
            f"sort_column={sort_column}, sort_order={sort_order}"
        )

        # 変更があるかどうかをチェック
        update_needed = False

        # 翻訳ステータス
        if (
            translation_status is not None
            and translation_status != self.translation_status
        ):
            self._set_flag_conditions_from_status(translation_status)
            update_needed = True

        # 検索テキスト
        if search_text != self.search_text:
            self.search_text = search_text
            update_needed = True

        # ソート条件
        if sort_column is not None and sort_column != self.sort_column:
            self.sort_column = sort_column
            update_needed = True
        if sort_order is not None and sort_order != self.sort_order:
            self.sort_order = sort_order
            update_needed = True

        # フラグ条件
        if flag_conditions is not None and flag_conditions != self.flag_conditions:
            self.flag_conditions = cast(FlagConditions, flag_conditions)
            update_needed = True

        # 変更があった場合はフィルタ更新フラグを設定
        if update_needed:
            # フィルタリング条件が変更された場合は、強制的に更新
            self._force_filter_update = True
            self.get_filtered_entries(update_filter=True)
