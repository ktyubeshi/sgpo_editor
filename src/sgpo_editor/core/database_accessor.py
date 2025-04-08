"""データベースアクセサモジュール

このモジュールは、インメモリデータベースへのアクセスを抽象化し、
ViewerPOFileクラスからデータベース操作の責務を分離します。

データベースアクセサの主な役割:
1. データベース操作の抽象化: InMemoryEntryStoreへの直接アクセスをラップし、高レベルなAPIを提供
2. エントリの取得・更新: キーやフィルタ条件に基づくエントリの取得や更新を行う
3. キャッシュシステムとの連携: EntryCacheManagerと連携し、キャッシュの一貫性を維持

キャッシュシステムとの連携方法:
- ViewerPOFileクラスは、まずEntryCacheManagerからエントリを取得を試み、キャッシュミスの場合にDatabaseAccessorを使用
- エントリ更新時は、DatabaseAccessorがデータベースを更新した後、ViewerPOFileがEntryCacheManagerのキャッシュも更新
- フィルタリング操作は、まずキャッシュを確認し、キャッシュミスまたは強制更新フラグがある場合にDatabaseAccessorを使用
"""

import logging
from typing import Optional, Union

from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import EntryDict, EntryDictList, EntryInput, EntryInputMap, FlagConditions

logger = logging.getLogger(__name__)


class DatabaseAccessor:
    """インメモリデータベースへのアクセスを抽象化するクラス

    このクラスは、InMemoryEntryStoreへのアクセスを抽象化し、
    データベース操作に関連する責務を一元管理します。
    
    このクラスは主に以下の機能を提供します：
    1. データベースの基本操作: クリア、エントリの追加、取得、更新
    2. フィルタリング: 検索テキスト、フラグ条件、翻訳ステータスに基づくエントリの絞り込み
    3. 一括操作: 複数エントリの一括取得、一括更新、インポート
    
    EntryCacheManagerとの連携:
    - EntryCacheManagerはキャッシュミス時にこのクラスのメソッドを呼び出し、データベースからエントリを取得
    - エントリ更新時は、まずこのクラスを使ってデータベースを更新し、その後キャッシュも更新
    - フィルタリング時は、キャッシュミスの場合にget_filtered_entriesメソッドが呼び出され、結果がキャッシュに保存
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

    def get_entry_by_key(self, key: str) -> Optional[EntryDict]:
        """キーでエントリを取得する

        このメソッドは、指定されたキーに対応するエントリをデータベースから取得します。
        通常、EntryCacheManagerのget_complete_entryメソッドでキャッシュを確認した後、
        キャッシュミスの場合にこのメソッドが呼び出されます。取得したエントリは
        EntryCacheManagerのcache_complete_entryメソッドでキャッシュに保存されます。

        Args:
            key: 取得するエントリのキー（通常は位置を表す文字列）

        Returns:
            エントリの辞書、存在しない場合はNone
        """
        logger.debug(f"DatabaseAccessor.get_entry_by_key: キー={key}のエントリを取得")
        return self.db.get_entry_by_key(key)

    def get_entries_by_keys(self, keys: List[str]) -> Dict[str, EntryDict]:
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

    def get_all_entries_basic_info(self) -> Dict[str, EntryDict]:
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

    def get_entry_basic_info(self, key: str) -> Optional[EntryDict]:
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
        search_text: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[FlagConditions] = None,
        translation_status: Optional[str] = None,
    ) -> EntryDictList:
        """フィルタ条件に合ったエントリを取得する

        このメソッドは、指定されたフィルタ条件に基づいてデータベースからエントリを検索します。
        ViewerPOFileFilterクラスから呼び出され、EntryCacheManagerのフィルタキャッシュと連携します。
        通常、EntryCacheManagerのget_filtered_entries_cacheメソッドで最初にキャッシュを確認し、
        キャッシュミスの場合や強制更新フラグがある場合にこのメソッドが呼び出されます。

        Args:
            search_text: 検索テキスト（msgid、msgstrに含まれる文字列）
            sort_column: ソート列（"position"、"msgid"、"msgstr"など）
            sort_order: ソート順序（"asc"または"desc"）
            flag_conditions: フラグ条件（"fuzzy": True/Falseなど）
            translation_status: 翻訳ステータス（"all"、"translated"、"untranslated"、"fuzzy"など）

        Returns:
            フィルタ条件に一致するエントリの辞書のリスト
        """
        logger.debug(
            f"DatabaseAccessor.get_filtered_entries: search_text={search_text}"
        )
        return self.db.get_entries(
            search_text=search_text,
            sort_column=sort_column,
            sort_order=sort_order,
            flag_conditions=flag_conditions,
            translation_status=translation_status,
        )

    def update_entry(self, entry: EntryInput) -> bool:
        """エントリを更新する

        このメソッドは、指定されたエントリでデータベースを更新します。
        ViewerPOFileクラスからの更新操作で呼び出され、データベースの更新後、
        EntryCacheManagerのupdate_entry_in_cacheメソッドを使ってキャッシュも更新されます。

        Args:
            entry: 更新するエントリ（辞書またはEntryModelオブジェクト）
                  EntryModelの場合は内部でPOEntryに変換してから更新

        Returns:
            更新が成功した場合はTrue、失敗した場合はFalse
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
        self, entries: EntryInputMap
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
        self, entries: EntryInputMap
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
