"""データベースアクセサモジュール

このモジュールは、インメモリデータベースへのアクセスを抽象化し、
ViewerPOFileクラスからデータベース操作の責務を分離します。
"""

import logging
from typing import Any, Dict, List, Optional, Union

from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class DatabaseAccessor:
    """インメモリデータベースへのアクセスを抽象化するクラス

    このクラスは、InMemoryEntryStoreへのアクセスを抽象化し、
    データベース操作に関連する責務を一元管理します。
    """

    def __init__(self, db: InMemoryEntryStore):
        """初期化

        Args:
            db: インメモリデータベースのインスタンス
        """
        self.db = db
        logger.debug("DatabaseAccessor: 初期化完了")

    def clear_database(self) -> None:
        """データベースの内容をクリアする"""
        logger.debug("DatabaseAccessor.clear_database: データベースをクリア")
        self.db.clear()

    def add_entries_bulk(self, entries: List[Dict[str, Any]]) -> None:
        """複数のエントリを一括でデータベースに追加する

        Args:
            entries: 追加するエントリのリスト
        """
        logger.debug(
            f"DatabaseAccessor.add_entries_bulk: {len(entries)}件のエントリを一括追加"
        )
        self.db.add_entries_bulk(entries)

    def get_entry_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """キーでエントリを取得する

        Args:
            key: 取得するエントリのキー

        Returns:
            エントリの辞書、存在しない場合はNone
        """
        logger.debug(f"DatabaseAccessor.get_entry_by_key: キー={key}のエントリを取得")
        return self.db.get_entry_by_key(key)

    def get_entries_by_keys(self, keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """複数のキーに対応するエントリを一度に取得する

        Args:
            keys: 取得するエントリのキーのリスト

        Returns:
            キーとエントリの辞書のマッピング
        """
        logger.debug(
            f"DatabaseAccessor.get_entries_by_keys: {len(keys)}件のエントリを一括取得"
        )
        return self.db.get_entries_by_keys(keys)

    def get_all_entries_basic_info(self) -> Dict[str, Dict[str, Any]]:
        """すべてのエントリの基本情報を取得する

        Returns:
            キーと基本情報のマッピング
        """
        logger.debug(
            "DatabaseAccessor.get_all_entries_basic_info: すべてのエントリの基本情報を取得"
        )

        # データベースからすべてのエントリの基本情報を取得
        entries = {}
        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT key, msgid, msgstr, fuzzy, obsolete
                FROM entries
                """
            )
            for row in cur.fetchall():
                key = row["key"]
                entries[key] = {
                    "key": key,
                    "msgid": row["msgid"],
                    "msgstr": row["msgstr"],
                    "fuzzy": bool(row["fuzzy"]),
                    "obsolete": bool(row["obsolete"]),
                    "position": 0,  # デフォルト値を設定
                }

        return entries

    def get_entry_basic_info(self, key: str) -> Optional[Dict[str, Any]]:
        """エントリの基本情報のみを取得する

        Args:
            key: 取得するエントリのキー

        Returns:
            基本情報のみを含むエントリの辞書、存在しない場合はNone
        """
        logger.debug(
            f"DatabaseAccessor.get_entry_basic_info: キー={key}の基本情報を取得"
        )
        return self.db.get_entry_basic_info(key)

    def get_filtered_entries(
        self,
        filter_text: Optional[str] = None,
        search_text: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[Dict[str, Any]] = None,
        translation_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """フィルタ条件に合ったエントリを取得する

        Args:
            filter_text: フィルタテキスト
            search_text: 検索テキスト
            sort_column: ソート列
            sort_order: ソート順序
            flag_conditions: フラグ条件
            translation_status: 翻訳ステータス

        Returns:
            フィルタ条件に一致するエントリのリスト
        """
        logger.debug(
            f"DatabaseAccessor.get_filtered_entries: filter_text={filter_text}, search_text={search_text}"
        )
        return self.db.get_entries(
            filter_text=filter_text,
            search_text=search_text,
            sort_column=sort_column,
            sort_order=sort_order,
            flag_conditions=flag_conditions,
            translation_status=translation_status,
        )

    def update_entry(self, entry: Union[Dict[str, Any], EntryModel]) -> bool:
        """エントリを更新する

        Args:
            entry: 更新するエントリ（辞書またはEntryModelオブジェクト）

        Returns:
            更新が成功したかどうか
        """
        # EntryModelオブジェクトを辞書に変換（必要な場合）
        if isinstance(entry, EntryModel):
            logger.debug(
                f"DatabaseAccessor.update_entry: EntryModelをPOEntryに変換 key={entry.key}"
            )
            # EntryModelをPOEntryに変換し、それを辞書に変換
            po_entry = entry.to_po_entry()
            entry_dict = {
                "key": entry.key,
                "msgid": po_entry.msgid,
                "msgstr": po_entry.msgstr,
                "flags": po_entry.flags,
                "obsolete": po_entry.obsolete,
                "position": entry.position,
            }

            # オプションフィールドを追加
            if hasattr(po_entry, "msgctxt") and po_entry.msgctxt:
                entry_dict["msgctxt"] = po_entry.msgctxt
            if hasattr(po_entry, "comment") and po_entry.comment:
                entry_dict["comment"] = po_entry.comment
            if hasattr(po_entry, "tcomment") and po_entry.tcomment:
                entry_dict["tcomment"] = po_entry.tcomment
        else:
            entry_dict = entry

        # データベースを更新
        logger.debug(
            f"DatabaseAccessor.update_entry: データベース更新開始 key={entry_dict.get('key')}"
        )
        result = self.db.update_entry(entry_dict)
        logger.debug(
            f"DatabaseAccessor.update_entry: データベース更新結果 result={result}"
        )

        return result

    def update_entries(
        self, entries: Dict[str, Union[Dict[str, Any], EntryModel]]
    ) -> bool:
        """複数のエントリを一括更新する

        Args:
            entries: 更新するエントリのマッピング（キー→エントリ）

        Returns:
            更新が成功したかどうか
        """
        logger.debug(
            f"DatabaseAccessor.update_entries: {len(entries)}件のエントリを一括更新"
        )

        # EntryModelオブジェクトを辞書に変換（必要な場合）
        entries_dict = {}
        for key, entry in entries.items():
            if isinstance(entry, EntryModel):
                # EntryModelをPOEntryに変換し、それを辞書に変換
                po_entry = entry.to_po_entry()
                entry_dict = {
                    "key": entry.key,
                    "msgid": po_entry.msgid,
                    "msgstr": po_entry.msgstr,
                    "flags": po_entry.flags,
                    "obsolete": po_entry.obsolete,
                    "position": entry.position,
                }

                # オプションフィールドを追加
                if hasattr(po_entry, "msgctxt") and po_entry.msgctxt:
                    entry_dict["msgctxt"] = po_entry.msgctxt
                if hasattr(po_entry, "comment") and po_entry.comment:
                    entry_dict["comment"] = po_entry.comment
                if hasattr(po_entry, "tcomment") and po_entry.tcomment:
                    entry_dict["tcomment"] = po_entry.tcomment

                entries_dict[key] = entry_dict
            else:
                entries_dict[key] = entry

        # データベースを更新
        result = self.db.update_entries(entries_dict)
        logger.debug(
            f"DatabaseAccessor.update_entries: データベース更新結果 result={result}"
        )

        return result

    def import_entries(
        self, entries: Dict[str, Union[Dict[str, Any], EntryModel]]
    ) -> bool:
        """エントリをインポートする（既存エントリの上書き）

        Args:
            entries: インポートするエントリのマッピング（キー→エントリ）

        Returns:
            インポートが成功したかどうか
        """
        logger.debug(
            f"DatabaseAccessor.import_entries: {len(entries)}件のエントリをインポート"
        )

        # EntryModelオブジェクトを辞書に変換（必要な場合）
        entries_dict = {}
        for key, entry in entries.items():
            entries_dict[key] = (
                entry.to_dict() if isinstance(entry, EntryModel) else entry
            )

        # データベースにインポート
        result = self.db.import_entries(entries_dict)
        logger.debug(
            f"DatabaseAccessor.import_entries: データベースインポート結果 result={result}"
        )

        return result
