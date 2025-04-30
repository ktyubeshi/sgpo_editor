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
from typing import Optional, List, Dict, Set, Tuple
import sqlite3

from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import (
    EntryDict,
    EntryDictList,
    EntryInput,
    EntryInputMap,
    FlagConditions,
)
from sgpo_editor.core.constants import TranslationStatus

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

    def add_entries_bulk(self, entries: EntryDictList) -> None:
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
        with self.db.transaction() as cur:
            cur.execute("SELECT * FROM entries WHERE key = ?", (key,))
            row = cur.fetchone()
            if row:
                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, row))
            return None

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

        if not keys:
            return {}

        entries_dict = {}
        with self.db.transaction() as cur:
            placeholders = ", ".join(["?"] * len(keys))

            cur.execute(
                f"""
                SELECT
                    e.*,
                    d.position
                FROM entries e
                LEFT JOIN display_order d ON e.id = d.entry_id
                WHERE e.key IN ({placeholders})
                """,
                keys,
            )
            self.last_cursor_description = cur.description

            for row in cur.fetchall():
                entry_dict = self._row_to_entry_dict(row)
                key = entry_dict.get("key", "")
                if key:
                    entries_dict[key] = entry_dict

        return entries_dict

    def get_all_entries(self) -> list:
        """すべてのエントリを取得する

        Returns:
            List[EntryDict]: すべてのエントリのリスト
        """
        logger.debug("DatabaseAccessor.get_all_entries: すべてのエントリを取得")
        entries = []
        with self.db.transaction() as cur:
            cur.execute("SELECT * FROM entries")
            columns = [desc[0] for desc in cur.description]
            for row in cur.fetchall():
                entry_dict = dict(zip(columns, row))
                entries.append(entry_dict)
        return entries

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
            # 件数デバッグ出力
            cur.execute(
                """
                SELECT key, msgid, msgstr, fuzzy, obsolete
                FROM entries
                """
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
            print(f"[DEBUG] 取得時の件数: {len(rows)}")
            for row in rows:
                print(f"columns: {columns}, row: {row}, type(row): {type(row)}")
                row_dict = dict(zip(columns, row))
                key = row_dict["key"]
                entries[key] = {
                    "key": key,
                    "msgid": row_dict["msgid"],
                    "msgstr": row_dict["msgstr"],
                    "fuzzy": bool(row_dict["fuzzy"]),
                    "obsolete": bool(row_dict["obsolete"]),
                    "position": 0,  # デフォルト値を設定
                }

        print(f"entries(keys): {list(entries.keys())}, entries: {entries}")
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

        with self.db.transaction() as cur:
            cur.execute(
                """
                SELECT
                    e.key, e.msgid, e.msgstr, e.fuzzy, e.obsolete
                FROM entries e
                WHERE e.key = ?
                """,
                (key,),
            )
            row = cur.fetchone()

            if not row:
                return None

            return {
                "key": row["key"],
                "msgid": row["msgid"],
                "msgstr": row["msgstr"],
                "fuzzy": bool(row["fuzzy"]),
                "obsolete": bool(row["obsolete"]),
                "position": 0,
                "flags": [],
                "references": [],
                "metadata": {},
                "review_comments": [],
                "metric_scores": {},
                "check_results": [],
                "category_quality_scores": {},
            }

    def get_filtered_entries(
        self,
        filter_text: str = "すべて",
        filter_keyword: str = "",
        match_mode: str = "部分一致",
        case_sensitive: bool = False,
        filter_status: Optional[Set[str]] = None,
        filter_obsolete: bool = True,
        search_text: str = "",
    ) -> List[dict]:
        """
        フィルタ条件に一致するエントリを取得する

        Returns:
            List[EntryDict]: フィルタ条件に一致するエントリのリスト
        """
        # Accept None values for search_text and filter_keyword as empty string
        if search_text is None:
            search_text = ""
        if filter_keyword is None:
            filter_keyword = ""
        norm_filter_keyword = filter_keyword.strip()
        norm_search_text = search_text.strip()
        if norm_search_text == "":
            norm_search_text = norm_filter_keyword

        logger.debug(
            f"DatabaseAccessor.get_filtered_entries (Python filter): filter_status={filter_status}, "
            f"filter_obsolete={filter_obsolete}, search_text={norm_search_text}, "
            f"match_mode={match_mode}, case_sensitive={case_sensitive}"
        )

        filtered_entries = []
        # Retrieve all entries via accessor to avoid store-level SQL issues
        for entry_dict in self.get_all_entries():
            # 廃止フィルタリング
            if not filter_obsolete and entry_dict.get("obsolete"):
                continue

            # 状態フィルタリング
            if filter_status:
                # EntryModel.get_status()相当のロジックをここで実装する必要がある場合は追加
                pass  # 必要に応じて拡張

            # キーワードフィルタリング
            if norm_search_text:
                # msgid, msgstr, msgctxt, comment, tcomment, references などで部分一致
                targets = [
                    entry_dict.get("msgid", ""),
                    entry_dict.get("msgstr", ""),
                    entry_dict.get("msgctxt", ""),
                    entry_dict.get("comment", ""),
                    entry_dict.get("tcomment", ""),
                ]
                # references等もあれば追加
                if not any(norm_search_text in (t or "") for t in targets):
                    continue

            filtered_entries.append(entry_dict)

        logger.debug(
            f"DatabaseAccessor.get_filtered_entries (Python filter): Found {len(filtered_entries)} entries"
        )
        return filtered_entries

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
        from typing import cast

        result = self.db.update_entry(entry_dict["key"], cast(EntryDict, entry_dict))
        logger.debug(
            f"DatabaseAccessor.update_entry: データベース更新結果 result={result}"
        )

        return result

    def update_entries(self, entries: EntryInputMap) -> bool:
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

        success = True
        try:
            with self.db.transaction() as cur:
                for key, entry_data in entries_dict.items():
                    cur.execute(
                        """
                        UPDATE entries SET
                            msgctxt = ?,
                            msgid = ?,
                            msgstr = ?,
                            fuzzy = ?,
                            obsolete = ?,
                            previous_msgid = ?,
                            previous_msgid_plural = ?,
                            previous_msgctxt = ?,
                            comment = ?,
                            tcomment = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE key = ?
                        """,
                        (
                            entry_data.get("msgctxt"),
                            entry_data.get("msgid"),
                            entry_data.get("msgstr"),
                            entry_data.get("fuzzy", 0),
                            entry_data.get("obsolete", 0),
                            entry_data.get("previous_msgid"),
                            entry_data.get("previous_msgid_plural"),
                            entry_data.get("previous_msgctxt"),
                            entry_data.get("comment"),
                            entry_data.get("tcomment"),
                            key,
                        ),
                    )

                    cur.execute(
                        "DELETE FROM entry_references WHERE entry_id IN (SELECT id FROM entries WHERE key = ?)",
                        (key,),
                    )
                    references = entry_data.get("references", []) or []
                    for ref in references:
                        cur.execute(
                            """
                            INSERT INTO entry_references (entry_id, reference)
                            SELECT id, ? FROM entries WHERE key = ?
                            """,
                            (ref, key),
                        )

                    cur.execute(
                        "DELETE FROM entry_flags WHERE entry_id IN (SELECT id FROM entries WHERE key = ?)",
                        (key,),
                    )
                    flags = entry_data.get("flags", []) or []
                    for flag in flags:
                        cur.execute(
                            """
                            INSERT INTO entry_flags (entry_id, flag)
                            SELECT id, ? FROM entries WHERE key = ?
                            """,
                            (flag, key),
                        )

                    if "position" in entry_data:
                        cur.execute(
                            """
                            UPDATE display_order SET
                                position = ?
                            WHERE entry_id IN (SELECT id FROM entries WHERE key = ?)
                            """,
                            (entry_data["position"], key),
                        )
        except Exception as e:
            logger.error(f"DatabaseAccessor.update_entries: 更新エラー: {e}")
            success = False

        logger.debug(
            f"DatabaseAccessor.update_entries: データベース更新結果 result={success}"
        )
        return success

    def import_entries(self, entries: EntryInputMap) -> bool:
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

        success = True
        try:
            with self.db.transaction() as cur:
                entry_data = []
                for key, entry in entries_dict.items():
                    entry_data.append(
                        (
                            key,
                            entry.get("msgctxt"),
                            entry.get("msgid"),
                            entry.get("msgstr"),
                            entry.get("fuzzy", False),
                            entry.get("obsolete", False),
                            entry.get("previous_msgid"),
                            entry.get("previous_msgid_plural"),
                            entry.get("previous_msgctxt"),
                            entry.get("comment"),
                            entry.get("tcomment"),
                        )
                    )

                cur.executemany(
                    """
                    INSERT INTO entries (
                        key, msgctxt, msgid, msgstr, fuzzy, obsolete,
                        previous_msgid, previous_msgid_plural, previous_msgctxt,
                        comment, tcomment
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    entry_data,
                )

                keys = list(entries_dict.keys())
                placeholders = ", ".join(["?"] * len(keys))
                cur.execute(
                    f"""
                    SELECT id, key FROM entries
                    WHERE key IN ({placeholders})
                    """,
                    keys,
                )

                id_map = {key: entry_id for entry_id, key in cur.fetchall()}

                references = []
                flags = []
                display_orders = []

                for key, entry in entries_dict.items():
                    entry_id = id_map.get(key)
                    if entry_id:
                        for ref in entry.get("references", []) or []:
                            references.append((entry_id, ref))

                        for flag in entry.get("flags", []) or []:
                            flags.append((entry_id, flag))

                        display_orders.append((entry_id, entry.get("position", 0)))

                if references:
                    cur.executemany(
                        "INSERT INTO entry_references (entry_id, reference) VALUES (?, ?)",
                        references,
                    )

                if flags:
                    cur.executemany(
                        "INSERT INTO entry_flags (entry_id, flag) VALUES (?, ?)",
                        flags,
                    )

                if display_orders:
                    cur.executemany(
                        "INSERT INTO display_order (entry_id, position) VALUES (?, ?)",
                        display_orders,
                    )

        except Exception as e:
            logger.error(f"DatabaseAccessor.import_entries: インポートエラー: {e}")
            success = False

        logger.debug(
            f"DatabaseAccessor.import_entries: データベースインポート結果 result={success}"
        )
        return success

    def advanced_search(
        self,
        search_text: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[FlagConditions] = None,
        translation_status: Optional[str] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = 0,
    ) -> EntryDictList:
        """高度な検索機能を提供する

        このメソッドは、より柔軟なパラメータを使用して、データベース内のエントリを検索します。
        SQLレベルでの最適化を行い、大量のエントリがある場合でも高速な検索を実現します。

        Args:
            search_text: 検索テキスト
            search_fields: 検索対象のフィールド（省略時は["msgid", "msgstr"]）
            sort_column: ソートするカラム
            sort_order: ソート順序（"asc" または "desc"）
            flag_conditions: フラグ条件
            translation_status: 翻訳ステータス
            exact_match: 完全一致で検索するかどうか
            case_sensitive: 大文字・小文字を区別するかどうか
            limit: 取得する最大件数
            offset: 取得開始位置

        Returns:
            検索条件に一致するエントリのリスト
        """
        logger.debug(
            f"DatabaseAccessor.advanced_search: search_text={search_text}, "
            f"search_fields={search_fields}, "
            f"exact_match={exact_match}, case_sensitive={case_sensitive}, "
            f"limit={limit}, offset={offset}"
        )

        # 検索フィールド指定がない場合はデフォルト値を使用
        if not search_fields:
            search_fields = ["msgid", "msgstr"]

        # InMemoryEntryStoreはadvanced_searchのパラメータをすべてサポートしていないため、
        # SQL文を直接構築して実行する

        # SQLクエリのパラメータ
        params = []

        # 基本クエリ
        query = """
            SELECT e.*, d.position AS position
            FROM entries e
            LEFT JOIN display_order d ON e.id = d.entry_id
        """

        # WHERE句の条件を格納するリスト
        where_conditions = []

        # 検索テキストフィルタ
        if search_text:
            # 検索フィールドごとの条件を構築
            search_field_conditions = []

            for field in search_fields:
                if field == "msgid":
                    if exact_match:
                        if case_sensitive:
                            search_field_conditions.append("e.msgid = ?")
                        else:
                            search_field_conditions.append("LOWER(e.msgid) = LOWER(?)")
                    else:
                        if case_sensitive:
                            search_field_conditions.append("e.msgid LIKE ?")
                        else:
                            search_field_conditions.append(
                                "LOWER(e.msgid) LIKE LOWER(?)"
                            )

                    if exact_match:
                        params.append(search_text)
                    else:
                        params.append(f"%{search_text}%")

                elif field == "msgstr":
                    if exact_match:
                        if case_sensitive:
                            search_field_conditions.append("e.msgstr = ?")
                        else:
                            search_field_conditions.append("LOWER(e.msgstr) = LOWER(?)")
                    else:
                        if case_sensitive:
                            search_field_conditions.append("e.msgstr LIKE ?")
                        else:
                            search_field_conditions.append(
                                "LOWER(e.msgstr) LIKE LOWER(?)"
                            )

                    if exact_match:
                        params.append(search_text)
                    else:
                        params.append(f"%{search_text}%")

                elif field == "reference":
                    if exact_match:
                        if case_sensitive:
                            search_field_conditions.append("""
                                EXISTS (
                                    SELECT 1 FROM entry_references r 
                                    WHERE r.entry_id = e.id AND r.reference = ?
                                )
                            """)
                        else:
                            search_field_conditions.append("""
                                EXISTS (
                                    SELECT 1 FROM entry_references r 
                                    WHERE r.entry_id = e.id AND LOWER(r.reference) = LOWER(?)
                                )
                            """)
                    else:
                        if case_sensitive:
                            search_field_conditions.append("""
                                EXISTS (
                                    SELECT 1 FROM entry_references r 
                                    WHERE r.entry_id = e.id AND r.reference LIKE ?
                                )
                            """)
                        else:
                            search_field_conditions.append("""
                                EXISTS (
                                    SELECT 1 FROM entry_references r 
                                    WHERE r.entry_id = e.id AND LOWER(r.reference) LIKE LOWER(?)
                                )
                            """)

                    if exact_match:
                        params.append(search_text)
                    else:
                        params.append(f"%{search_text}%")

                elif field == "translator_comment" or field == "tcomment":
                    if exact_match:
                        if case_sensitive:
                            search_field_conditions.append("e.tcomment = ?")
                        else:
                            search_field_conditions.append(
                                "LOWER(e.tcomment) = LOWER(?)"
                            )
                    else:
                        if case_sensitive:
                            search_field_conditions.append("e.tcomment LIKE ?")
                        else:
                            search_field_conditions.append(
                                "LOWER(e.tcomment) LIKE LOWER(?)"
                            )

                    if exact_match:
                        params.append(search_text)
                    else:
                        params.append(f"%{search_text}%")

                elif field == "extracted_comment" or field == "comment":
                    if exact_match:
                        if case_sensitive:
                            search_field_conditions.append("e.comment = ?")
                        else:
                            search_field_conditions.append(
                                "LOWER(e.comment) = LOWER(?)"
                            )
                    else:
                        if case_sensitive:
                            search_field_conditions.append("e.comment LIKE ?")
                        else:
                            search_field_conditions.append(
                                "LOWER(e.comment) LIKE LOWER(?)"
                            )

                    if exact_match:
                        params.append(search_text)
                    else:
                        params.append(f"%{search_text}%")

            # 検索フィールド条件をORで結合
            if search_field_conditions:
                where_conditions.append(
                    "(" + " OR ".join(search_field_conditions) + ")"
                )

        # 翻訳ステータスに基づくフィルタ
        from sgpo_editor.core.constants import TranslationStatus

        if translation_status == TranslationStatus.TRANSLATED:
            # 翻訳済み: msgstrが空でなく、fuzzyでない
            where_conditions.append("(e.msgstr != '' AND e.fuzzy = 0)")
        elif translation_status == TranslationStatus.UNTRANSLATED:
            # 未翻訳: msgstrが空で、fuzzyでない
            where_conditions.append("(e.msgstr = '' AND e.fuzzy = 0)")
        elif translation_status == TranslationStatus.FUZZY:
            # fuzzy: fuzzyフラグがある
            where_conditions.append("e.fuzzy = 1")
        elif translation_status == TranslationStatus.FUZZY_OR_UNTRANSLATED:
            # fuzzyまたは未翻訳
            where_conditions.append("(e.fuzzy = 1 OR e.msgstr = '')")
        # ALL（すべて）の場合は条件なし

        # フラグ条件に基づくフィルタ
        if flag_conditions:
            if "fuzzy" in flag_conditions:
                if flag_conditions["fuzzy"]:
                    where_conditions.append("e.fuzzy = 1")
                else:
                    where_conditions.append("e.fuzzy = 0")

            if "msgstr_empty" in flag_conditions and flag_conditions["msgstr_empty"]:
                where_conditions.append("e.msgstr = ''")

            if (
                "msgstr_not_empty" in flag_conditions
                and flag_conditions["msgstr_not_empty"]
            ):
                where_conditions.append("e.msgstr != ''")

            if (
                "fuzzy_or_msgstr_empty" in flag_conditions
                and flag_conditions["fuzzy_or_msgstr_empty"]
            ):
                where_conditions.append("(e.fuzzy = 1 OR e.msgstr = '')")

            # カスタムフラグ条件
            for flag_name, flag_value in flag_conditions.items():
                if flag_name not in (
                    "fuzzy",
                    "msgstr_empty",
                    "msgstr_not_empty",
                    "fuzzy_or_msgstr_empty",
                ):
                    if flag_value:
                        # サブクエリでフラグの有無を確認
                        where_conditions.append("""
                            EXISTS (
                                SELECT 1 FROM entry_flags ef 
                                WHERE ef.entry_id = e.id AND ef.flag = ?
                            )
                        """)
                        params.append(flag_name)

        # WHERE句を構築
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)

        # ソート順の決定
        valid_sort_columns = {
            "position": "d.position",
            "msgid": "e.msgid",
            "msgstr": "e.msgstr",
            "fuzzy": "e.fuzzy",
            "score": """(
                SELECT qs.overall_score 
                FROM quality_scores qs 
                WHERE qs.entry_id = e.id
            )""",
        }

        # 有効なソート列かチェック
        sort_column_sql = (
            valid_sort_columns[sort_column]
            if sort_column in valid_sort_columns
            else "d.position"
        )

        # ソート順のSQLインジェクション防止
        sort_order_sql = (
            "ASC" if sort_order is None or sort_order.upper() != "DESC" else "DESC"
        )

        # ソート条件を追加
        query += f" ORDER BY {sort_column_sql} {sort_order_sql}"

        # LIMIT と OFFSET の追加
        if limit is not None:
            query += f" LIMIT {limit}"
            if offset is not None and offset > 0:
                query += f" OFFSET {offset}"

        # クエリ実行と結果の取得
        with self.db.transaction() as cur:
            logger.debug(f"DatabaseAccessor.advanced_search: SQLクエリ実行: {query}")
            logger.debug(f"DatabaseAccessor.advanced_search: SQLパラメータ: {params}")
            cur.execute(query, params)
            # Try to capture cursor description if available
            try:
                self.last_cursor_description = cur.description
            except Exception:
                self.last_cursor_description = None

            # 結果をリストに変換
            result = []
            for row in cur.fetchall():
                entry_dict = self._row_to_entry_dict(row)
                result.append(entry_dict)

        logger.debug(
            f"DatabaseAccessor.advanced_search: {len(result)}件のエントリを取得"
        )
        return result

    def get_all_flags(self) -> Set[str]:
        """データベース内のすべてのフラグの集合を取得する

        Returns:
            データベース内に存在するすべてのフラグの集合
        """
        logger.debug("DatabaseAccessor.get_all_flags: すべてのフラグを取得")

        flags = set()
        with self.db.transaction() as cur:
            cur.execute("SELECT DISTINCT flag FROM entry_flags")
            for row in cur.fetchall():
                flags.add(row["flag"])

        return flags

    def count_entries(self) -> int:
        """データベース内のエントリ数を取得する

        Returns:
            int: エントリの総数
        """
        logger.debug("DatabaseAccessor.count_entries: エントリ数を取得")
        with self.db.transaction() as cur:
            cur.execute("SELECT COUNT(*) FROM entries")
            return cur.fetchone()[0]

    def count_entries_with_condition(self, condition: Dict) -> int:
        """条件に一致するエントリの数を取得する

        Args:
            condition: 条件を表す辞書 {"field": フィールド名, "value": 値, "operator": 演算子}
                演算子は "=", "!=", ">", "<", ">=", "<=" のいずれか

        Returns:
            int: 条件に一致するエントリの数
        """
        field = condition.get("field")
        value = condition.get("value")
        operator = condition.get("operator", "=")

        logger.debug(
            f"DatabaseAccessor.count_entries_with_condition: field={field}, value={value}, operator={operator}"
        )

        valid_operators = ["=", "!=", ">", "<", ">=", "<="]
        if operator not in valid_operators:
            logger.error(f"無効な演算子: {operator}")
            return 0

        with self.db.transaction() as cur:
            # None値の場合の特別処理
            if value is None:
                if operator == "=":
                    sql = f"SELECT COUNT(*) FROM entries WHERE {field} IS NULL"
                    cur.execute(sql)
                elif operator == "!=":
                    sql = f"SELECT COUNT(*) FROM entries WHERE {field} IS NOT NULL"
                    cur.execute(sql)
                else:
                    logger.error(f"None値に対して無効な演算子: {operator}")
                    return 0
            else:
                sql = f"SELECT COUNT(*) FROM entries WHERE {field} {operator} ?"
                cur.execute(sql, (value,))

            return cur.fetchone()[0]

    def count_entries_with_flag(self, flag: str) -> int:
        """特定のフラグを持つエントリの数を取得する

        Args:
            flag: カウントするフラグ名

        Returns:
            int: 指定されたフラグを持つエントリの数
        """
        logger.debug(f"DatabaseAccessor.count_entries_with_flag: flag={flag}")

        if flag == "fuzzy":
            # fuzzyはエントリテーブルの列として存在
            with self.db.transaction() as cur:
                cur.execute("SELECT COUNT(*) FROM entries WHERE fuzzy = 1")
                return cur.fetchone()[0]
        else:
            # その他のフラグはフラグテーブルで保持
            with self.db.transaction() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM entry_flags
                    WHERE flag = ?
                    """,
                    (flag,),
                )
                return cur.fetchone()[0]

    def get_unique_msgid_count(self) -> int:
        """一意のmsgid数を取得する

        Returns:
            一意のmsgidの数
        """
        logger.debug("DatabaseAccessor.get_unique_msgid_count: 一意のmsgid数を取得")

        with self.db.transaction() as cur:
            cur.execute("SELECT COUNT(DISTINCT msgid) as count FROM entries")
            row = cur.fetchone()
            return row["count"] if row else 0

    def get_entry_counts_by_status(self) -> Tuple[int, int, int, int]:
        """翻訳ステータス別のエントリ数を取得する

        Returns:
            (total, translated, fuzzy, untranslated) のタプル
        """
        logger.debug(
            "DatabaseAccessor.get_entry_counts_by_status: ステータス別エントリ数を取得"
        )

        with self.db.transaction() as cur:
            # 総数を取得
            cur.execute("SELECT COUNT(*) as count FROM entries")
            total_row = cur.fetchone()
            total = total_row["count"] if total_row else 0

            # fuzzy数を取得
            cur.execute("SELECT COUNT(*) as count FROM entries WHERE fuzzy = 1")
            fuzzy_row = cur.fetchone()
            fuzzy = fuzzy_row["count"] if fuzzy_row else 0

            # 翻訳済み数を取得 (fuzzyでなく、msgstrが空でない)
            cur.execute(
                "SELECT COUNT(*) as count FROM entries WHERE fuzzy = 0 AND msgstr != ''"
            )
            translated_row = cur.fetchone()
            translated = translated_row["count"] if translated_row else 0

            # 未翻訳数を取得 (fuzzyでなく、msgstrが空)
            cur.execute(
                "SELECT COUNT(*) as count FROM entries WHERE fuzzy = 0 AND msgstr = ''"
            )
            untranslated_row = cur.fetchone()
            untranslated = untranslated_row["count"] if untranslated_row else 0

        return (total, translated, fuzzy, untranslated)

    def invalidate_entry(self, key: str) -> None:
        """エントリを無効化する

        このメソッドは、指定されたキーのエントリをデータベースで無効化します。
        実際の処理は、EntryCacheManagerと連携してViewerPOFileRefactoredクラスから呼び出されることを
        想定しています。

        現在の実装ではデータベース側での処理は必要ありませんが、将来的にはデータベース側で
        無効化フラグを設定したり、キャッシュ関連の処理を行う可能性があります。

        EntryCacheManagerとの連携フロー:
        1. ViewerPOFileRefactoredクラスからのエントリ無効化要求が発生
        2. このinvalidate_entryメソッドが呼び出される（必要に応じてデータベース操作を実行）
        3. その後、ViewerPOFileRefactoredクラスがEntryCacheManagerのinvalidate_entryを呼び出し
        4. これによって、データベースとキャッシュの両方が一貫した状態に保たれる

        将来的な拡張可能性:
        - エントリ無効化ログの記録
        - 一時的な無効化マーキング（復元可能な形式で）
        - 関連エントリの無効化（グループ処理）

        Args:
            key: 無効化するエントリのキー
        """
        logger.debug(f"DatabaseAccessor.invalidate_entry: key={key}")
        # 現在の実装では、データベース側での特別な処理は必要なし
        # 将来的には以下のような処理を追加する可能性がある
        # with self.db.transaction() as cur:
        #     cur.execute(
        #         "UPDATE entries SET invalidated = 1 WHERE key = ?",
        #         (key,)

    def _row_to_entry_dict(self, row: sqlite3.Row) -> EntryDict:
        from typing import cast

        if not hasattr(row, "keys") and isinstance(row, tuple):
            if (
                hasattr(self, "last_cursor_description")
                and self.last_cursor_description
            ):
                keys = [desc[0] for desc in self.last_cursor_description]
                row = dict(zip(keys, row))
            else:
                raise TypeError("rowがtuple型ですがカラム名情報がありません")
        elif hasattr(row, "keys"):
            row = dict(row)

        entry_dict: EntryDict = {
            "key": row["key"],
            "msgid": row["msgid"],
            "msgstr": row["msgstr"],
            "fuzzy": bool(row["fuzzy"]),
            "obsolete": bool(row["obsolete"]),
            "position": 0 if row["position"] is None else row["position"],
        }

        for field in [
            "msgctxt",
            "comment",
            "tcomment",
            "previous_msgid",
            "previous_msgid_plural",
            "previous_msgctxt",
        ]:
            if row.get(field):
                entry_dict[field] = row[field]

        entry_id = row["id"]
        with self.db.transaction() as cur:
            cur.execute("SELECT flag FROM entry_flags WHERE entry_id = ?", (entry_id,))
            flags = [
                r["flag"]
                if isinstance(r, dict)
                or hasattr(r, "__getitem__")
                and not isinstance(r, tuple)
                else r[0]
                for r in cur.fetchall()
            ]
            if flags:
                entry_dict["flags"] = flags

            cur.execute(
                "SELECT reference FROM entry_references WHERE entry_id = ?", (entry_id,)
            )
            references = [
                r["reference"]
                if isinstance(r, dict)
                or hasattr(r, "__getitem__")
                and not isinstance(r, tuple)
                else r[0]
                for r in cur.fetchall()
            ]
            if references:
                entry_dict["references"] = references

            cur.execute(
                "SELECT id, overall_score FROM quality_scores WHERE entry_id = ?",
                (entry_id,),
            )
            quality_score_row = cur.fetchone()
            if quality_score_row:
                entry_dict["overall_quality_score"] = quality_score_row["overall_score"]

                quality_score_id = quality_score_row["id"]
                cur.execute(
                    "SELECT category, score FROM category_scores WHERE quality_score_id = ?",
                    (quality_score_id,),
                )
                category_scores = {r["category"]: r["score"] for r in cur.fetchall()}
                if category_scores:
                    entry_dict["category_quality_scores"] = category_scores

        return cast(EntryDict, entry_dict)

    def get_entries(
        self,
        search_text: Optional[str] = None,
        translation_status: Optional[str] = None,
    ) -> List[dict]:
        """Alias for get_filtered_entries to match test expectations."""
        # Normalize search_text
        st = search_text.strip() if search_text is not None else ""
        # Determine filter_status from translation_status
        if translation_status and translation_status != TranslationStatus.ALL:
            fs = {translation_status}
        else:
            fs = None
        return self.get_filtered_entries(
            filter_text="すべて",
            filter_keyword="",
            match_mode="部分一致",
            case_sensitive=False,
            filter_status=fs,
            filter_obsolete=True,
            search_text=st,
        )
