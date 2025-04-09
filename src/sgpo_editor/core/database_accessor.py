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
from typing import Optional, List, Dict, Any, Set, Tuple
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

        最適化ポイント:
        - WHERE句の条件は動的に構築され、必要なフィルタのみが適用されます
        - パラメータ化されたクエリを使用してSQLインジェクションを防止します
        - フラグ条件は効率的なサブクエリとして実装されています
        - 翻訳ステータスに応じた条件が最適化されています
        - 適切なインデックスが使用されるようにクエリを設計

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
            f"DatabaseAccessor.get_filtered_entries: search_text={search_text}, "
            f"sort_column={sort_column}, sort_order={sort_order}, "
            f"flag_conditions={flag_conditions}, translation_status={translation_status}"
        )

        # デフォルト値設定
        sort_column = sort_column or "position"
        sort_order = sort_order or "ASC"
        flag_conditions = flag_conditions or {}

        # SQLクエリのパラメータ
        params = []

        # 基本クエリ
        query = """
            SELECT e.*, d.position AS position
            FROM entries e
            JOIN display_order d ON e.id = d.entry_id
        """

        # WHERE句の条件を格納するリスト
        where_conditions = []

        # 検索テキストフィルタ
        if search_text:
            where_conditions.append("(e.msgid LIKE ? OR e.msgstr LIKE ?)")
            search_pattern = f"%{search_text}%"
            params.extend([search_pattern, search_pattern])

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
        sort_column_sql = valid_sort_columns.get(sort_column, "d.position")

        # ソート順のSQLインジェクション防止
        sort_order_sql = "ASC" if sort_order.upper() != "DESC" else "DESC"

        # ソート条件を追加
        query += f" ORDER BY {sort_column_sql} {sort_order_sql}"

        # クエリ実行と結果の取得
        with self.db.transaction() as cur:
            logger.debug(
                f"DatabaseAccessor.get_filtered_entries: SQLクエリ実行: {query}"
            )
            logger.debug(
                f"DatabaseAccessor.get_filtered_entries: SQLパラメータ: {params}"
            )
            cur.execute(query, params)

            # 結果をリストに変換
            result = []
            for row in cur.fetchall():
                entry_dict = self._row_to_entry_dict(row)
                result.append(entry_dict)

        logger.debug(
            f"DatabaseAccessor.get_filtered_entries: {len(result)}件のエントリを取得"
        )
        return result

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

        # データベースを更新
        result = self.db.update_entries(entries_dict)
        logger.debug(
            f"DatabaseAccessor.update_entries: データベース更新結果 result={result}"
        )

        return result

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

        # データベースにインポート
        result = self.db.import_entries(entries_dict)
        logger.debug(
            f"DatabaseAccessor.import_entries: データベースインポート結果 result={result}"
        )

        return result

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
            f"DatabaseAccessor.advanced_search: search_text={search_text}, exact_match={exact_match}, case_sensitive={case_sensitive}"
        )

        # 検索フィールド指定がない場合はデフォルト値を使用
        if not search_fields:
            search_fields = ["msgid", "msgstr"]

        # データベースからエントリを取得
        entries = self.db.get_entries(
            search_text=search_text,
            sort_column=sort_column,
            sort_order=sort_order,
            flag_conditions=flag_conditions,
            translation_status=translation_status,
            exact_match=exact_match,
            case_sensitive=case_sensitive,
            search_fields=search_fields,
            limit=limit,
            offset=offset,
        )

        return entries

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
        """データベース内のエントリ総数を取得する

        Returns:
            エントリの総数
        """
        logger.debug("DatabaseAccessor.count_entries: エントリ数を取得")

        with self.db.transaction() as cur:
            cur.execute("SELECT COUNT(*) as count FROM entries")
            row = cur.fetchone()
            return row["count"] if row else 0

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

        Args:
            key: 無効化するエントリのキー
        """
        logger.debug(f"DatabaseAccessor.invalidate_entry: key={key}")
        # キャッシュと連携して無効化すべき機能だが、現在はデータベースのみの操作
        # キャッシュマネージャとの連携は ViewerPOFileRefactored クラスで行う

    def _row_to_entry_dict(self, row: sqlite3.Row) -> EntryDict:
        """SQLite RowオブジェクトをEntryDict形式に変換する

        データベースから取得したRowオブジェクトを、アプリケーション全体で使用される
        EntryDict形式に変換します。このメソッドは内部で使用され、
        get_filtered_entriesなどのメソッドから呼び出されます。

        最適化ポイント:
        - 必要なフィールドのみを効率的に抽出
        - 関連テーブル（フラグ、リファレンスなど）の情報も取得
        - 他の関連情報は遅延読み込みが可能なように設計

        Args:
            row: SQLite Rowオブジェクト

        Returns:
            EntryDict: 変換された辞書
        """
        entry_dict = {
            "key": row["key"],
            "msgid": row["msgid"],
            "msgstr": row["msgstr"],
            "fuzzy": bool(row["fuzzy"]),
            "obsolete": bool(row["obsolete"]),
            "position": row["position"],
        }

        # オプションフィールドの追加
        for field in [
            "msgctxt",
            "comment",
            "tcomment",
            "previous_msgid",
            "previous_msgid_plural",
            "previous_msgctxt",
        ]:
            if row[field]:
                entry_dict[field] = row[field]

        # 関連データ（フラグとリファレンス）を取得
        entry_id = row["id"]
        with self.db.transaction() as cur:
            # フラグの取得
            cur.execute("SELECT flag FROM entry_flags WHERE entry_id = ?", (entry_id,))
            flags = [row["flag"] for row in cur.fetchall()]
            if flags:
                entry_dict["flags"] = flags

            # リファレンスの取得
            cur.execute(
                "SELECT reference FROM entry_references WHERE entry_id = ?", (entry_id,)
            )
            references = [row["reference"] for row in cur.fetchall()]
            if references:
                entry_dict["references"] = references

            # 品質スコアの取得（あれば）
            cur.execute(
                "SELECT id, overall_score FROM quality_scores WHERE entry_id = ?",
                (entry_id,),
            )
            quality_score_row = cur.fetchone()
            if quality_score_row:
                entry_dict["quality_score"] = quality_score_row["overall_score"]

                # カテゴリースコアの取得
                quality_score_id = quality_score_row["id"]
                cur.execute(
                    "SELECT category, score FROM category_scores WHERE quality_score_id = ?",
                    (quality_score_id,),
                )
                category_scores = {
                    row["category"]: row["score"] for row in cur.fetchall()
                }
                if category_scores:
                    entry_dict["category_scores"] = category_scores

        return entry_dict
