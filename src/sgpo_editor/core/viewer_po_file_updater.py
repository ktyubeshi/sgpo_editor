"""POファイルエントリ更新クラス

このモジュールは、POファイルのエントリを更新するための機能を提供します。
ViewerPOFileFilterを継承し、エントリ更新に関連する機能を実装します。
"""

import logging

from sgpo_editor.core.viewer_po_file_filter import ViewerPOFileFilter
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import EntryDict, EntryInput, EntryInputMap

logger = logging.getLogger(__name__)


class ViewerPOFileUpdater(ViewerPOFileFilter):
    """POファイルのエントリを更新するためのクラス

    このクラスは、ViewerPOFileFilterを継承し、エントリ更新に関連する機能を実装します。
    """

    def _entry_needs_update(
        self, entry_obj: EntryModel, entry_dict: EntryDict
    ) -> bool:
        """エントリオブジェクトが更新を必要とするかどうかを判断する

        Args:
            entry_obj: 既存のエントリオブジェクト
            entry_dict: 新しいエントリデータ

        Returns:
            bool: 更新が必要な場合はTrue
        """
        # 重要なフィールドが変更されている場合のみ更新
        return (
            entry_obj.msgid != entry_dict.get("msgid", "")
            or entry_obj.msgstr != entry_dict.get("msgstr", "")
            or entry_obj.fuzzy != ("fuzzy" in entry_dict.get("flags", []))
        )

    def update_entry(self, entry: EntryInput) -> bool:
        """エントリを更新する

        Args:
            entry: 更新するエントリ（辞書またはEntryModelオブジェクト）

        Returns:
            bool: 更新が成功したかどうか
        """
        logger.debug("ViewerPOFileUpdater.update_entry: 開始")
        try:
            # データベースアクセサを使用してエントリを更新
            result = self.db_accessor.update_entry(entry)
            logger.debug(
                f"ViewerPOFileUpdater.update_entry: データベース更新結果 result={result}"
            )

            if not result:
                logger.error("ViewerPOFileUpdater.update_entry: データベース更新失敗")
                return False

            # キャッシュを更新
            if result:
                # EntryModelオブジェクトに変換
                entry_obj = (
                    entry
                    if isinstance(entry, EntryModel)
                    else EntryModel.from_dict(entry)
                )
                key = entry_obj.key

                # キャッシュマネージャを使用してキャッシュを更新
                self.cache_manager.cache_complete_entry(key, entry_obj)

                # 基本情報キャッシュも更新
                basic_info = EntryModel(
                    key=entry_obj.key,
                    position=entry_obj.position,
                    msgid=entry_obj.msgid,
                    msgstr=entry_obj.msgstr,
                    flags=entry_obj.flags,  # flagsも含める
                    obsolete=entry_obj.obsolete,
                )
                self.cache_manager.cache_basic_info_entry(key, basic_info)

                # 変更フラグを設定
                self.modified = True

                # フィルタリング結果を更新
                self._force_filter_update = True
                self.get_filtered_entries(update_filter=True)

                return True
            return False
        except Exception as e:
            logger.error(f"ViewerPOFileUpdater.update_entry: エラー発生 {e}")
            logger.error(f"エントリ更新エラー: {e}")
            return False

    def update_entries(
        self, entries: EntryInputMap
    ) -> bool:
        """複数のエントリを一括更新する

        Args:
            entries: 更新するエントリのマッピング（キー→エントリ）

        Returns:
            bool: 更新が成功したかどうか
        """
        logger.debug(f"ViewerPOFileUpdater.update_entries: エントリ数={len(entries)}")
        try:
            # データベースアクセサを使用して一括更新
            result = self.db_accessor.update_entries(entries)
            logger.debug(
                f"ViewerPOFileUpdater.update_entries: データベース更新結果 result={result}"
            )

            if not result:
                logger.error("ViewerPOFileUpdater.update_entries: データベース更新失敗")
                return False

            # キャッシュを更新
            if result:
                for key, entry in entries.items():
                    # EntryModelオブジェクトに変換
                    entry_obj = (
                        entry
                        if isinstance(entry, EntryModel)
                        else EntryModel.from_dict(entry)
                    )

                    # キャッシュマネージャを使用してキャッシュを更新
                    self.cache_manager.cache_complete_entry(key, entry_obj)

                    # 基本情報キャッシュも更新
                    basic_info = EntryModel(
                        key=entry_obj.key,
                        position=entry_obj.position,
                        msgid=entry_obj.msgid,
                        msgstr=entry_obj.msgstr,
                        fuzzy=entry_obj.fuzzy,
                        obsolete=entry_obj.obsolete,
                    )
                    self.cache_manager.cache_basic_info_entry(key, basic_info)

                # 変更フラグを設定
                self.modified = True

                # フィルタリング結果を更新
                self._force_filter_update = True
                self.get_filtered_entries(update_filter=True)

                return True
            return False
        except Exception as e:
            logger.error(f"複数エントリ更新エラー: {e}")
            return False

    def import_entries(
        self, entries: EntryInputMap
    ) -> bool:
        """エントリをインポートする（既存エントリの上書き）

        Args:
            entries: インポートするエントリのマッピング（キー→エントリ）

        Returns:
            bool: インポートが成功したかどうか
        """
        logger.debug(f"ViewerPOFileUpdater.import_entries: エントリ数={len(entries)}")
        try:
            # データベースアクセサを使用して一括インポート
            result = self.db_accessor.import_entries(entries)
            logger.debug(
                f"ViewerPOFileUpdater.import_entries: データベースインポート結果 result={result}"
            )

            if not result:
                logger.error(
                    "ViewerPOFileUpdater.import_entries: データベースインポート失敗"
                )
                return False

            # キャッシュを更新
            if result:
                for key, entry in entries.items():
                    # EntryModelオブジェクトに変換
                    entry_obj = (
                        entry
                        if isinstance(entry, EntryModel)
                        else EntryModel.from_dict(entry)
                    )

                    # キャッシュマネージャを使用してキャッシュを更新
                    self.cache_manager.cache_complete_entry(key, entry_obj)

                    # 基本情報キャッシュも更新
                    basic_info = EntryModel(
                        key=entry_obj.key,
                        position=entry_obj.position,
                        msgid=entry_obj.msgid,
                        msgstr=entry_obj.msgstr,
                        fuzzy=entry_obj.fuzzy,
                        obsolete=entry_obj.obsolete,
                    )
                    self.cache_manager.cache_basic_info_entry(key, basic_info)

                # 変更フラグを設定
                self.modified = True

                # フィルタリング結果を更新
                self._force_filter_update = True
                self.get_filtered_entries(update_filter=True)

                return True
            return False
        except Exception as e:
            logger.error(f"エントリインポートエラー: {e}")
            return False
