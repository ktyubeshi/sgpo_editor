"""POエントリのデータベース"""
import sqlite3
from pathlib import Path
import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional, List, Dict

logger = logging.getLogger(__name__)


class Database:
    """POエントリのデータベース"""

    def __init__(self):
        """初期化"""
        # データベースファイルのパス設定
        self.db_path = Path(__file__).parent.parent.parent / "data" / "po_entries.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.debug("データベース初期化: %s", self.db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")
        self._create_tables()
        logger.debug("データベース初期化完了")

    def _create_tables(self) -> None:
        """テーブルを作成"""
        logger.debug("テーブル作成開始")
        with self.transaction() as cur:
            # エントリテーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    msgctxt TEXT,
                    msgid TEXT NOT NULL,
                    msgstr TEXT NOT NULL,
                    fuzzy BOOLEAN NOT NULL DEFAULT 0,
                    obsolete BOOLEAN NOT NULL DEFAULT 0,
                    previous_msgid TEXT,
                    previous_msgid_plural TEXT,
                    previous_msgctxt TEXT,
                    comment TEXT,
                    tcomment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # リファレンステーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entry_references (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    reference TEXT NOT NULL,
                    FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
                )
            """)

            # フラグテーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS entry_flags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    flag TEXT NOT NULL,
                    FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
                )
            """)

            # 表示順テーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS display_order (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
                )
            """)

            # インデックス作成（テーブル作成後に実行）
            cur.execute("CREATE INDEX IF NOT EXISTS idx_msgid ON entries(msgid)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_key ON entries(key)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_display_order_position ON display_order(position)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_display_order_entry_id ON display_order(entry_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entry_references ON entry_references(entry_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_entry_flags ON entry_flags(entry_id)")

        logger.debug("テーブル作成完了")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """トランザクションを開始"""
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception as e:
            logger.error("トランザクションエラー: %s", e, exc_info=True)
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def add_entries_bulk(self, entries: List[Dict[str, Any]]) -> None:
        """バルクインサートでエントリを追加"""
        logger.debug("バルクインサート開始（%d件）", len(entries))
        with self.transaction() as cur:
            # エントリ一括挿入
            entry_data = [
                (
                    entry["key"],
                    entry.get("msgctxt"),
                    entry["msgid"],
                    entry["msgstr"],
                    entry.get("fuzzy", False),
                    entry.get("obsolete", False),
                    entry.get("previous_msgid"),
                    entry.get("previous_msgid_plural"),
                    entry.get("previous_msgctxt"),
                    entry.get("comment"),
                    entry.get("tcomment"),
                )
                for entry in entries
            ]
            
            cur.executemany(
                """
                INSERT INTO entries (
                    key, msgctxt, msgid, msgstr, fuzzy, obsolete,
                    previous_msgid, previous_msgid_plural, previous_msgctxt,
                    comment, tcomment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                entry_data
            )
            
            # 挿入されたエントリのIDを取得
            # keyとidのマッピングを作成
            cur.execute("""
                SELECT id, key FROM entries
                WHERE key IN ({})
            """.format(','.join(['?'] * len(entries))), [entry["key"] for entry in entries])
            
            id_map = {key: id for id, key in cur.fetchall()}
            
            # エントリにIDを設定
            for entry in entries:
                entry["id"] = id_map.get(entry["key"])

            # リファレンス一括挿入
            references = []
            for entry in entries:
                entry_id = entry.get("id")
                if entry_id:
                    references.extend([(entry_id, ref) for ref in entry.get("references", [])])
            
            if references:
                cur.executemany(
                    "INSERT INTO entry_references (entry_id, reference) VALUES (?, ?)",
                    references
                )

            # フラグ一括挿入
            flags = []
            for entry in entries:
                entry_id = entry.get("id")
                if entry_id:
                    flags.extend([(entry_id, flag) for flag in entry.get("flags", [])])
            
            if flags:
                cur.executemany(
                    "INSERT INTO entry_flags (entry_id, flag) VALUES (?, ?)",
                    flags
                )

            # 表示順一括挿入
            display_orders = [(entry.get("id"), entry.get("position", 0)) for entry in entries if entry.get("id")]
            if display_orders:
                cur.executemany(
                    "INSERT INTO display_order (entry_id, position) VALUES (?, ?)",
                    display_orders
                )

        logger.debug("バルクインサート完了（%d件）", len(entries))

    def add_entry(self, entry: Dict[str, Any]) -> None:
        """エントリを追加"""
        logger.debug("エントリ追加開始: %s", entry["key"])
        with self.transaction() as cur:
            # エントリを追加
            cur.execute(
                """
                INSERT INTO entries (
                    key, msgctxt, msgid, msgstr, fuzzy, obsolete,
                    previous_msgid, previous_msgid_plural, previous_msgctxt,
                    comment, tcomment
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["key"],
                    entry.get("msgctxt"),
                    entry["msgid"],
                    entry["msgstr"],
                    entry.get("fuzzy", False),
                    entry.get("obsolete", False),
                    entry.get("previous_msgid"),
                    entry.get("previous_msgid_plural"),
                    entry.get("previous_msgctxt"),
                    entry.get("comment"),
                    entry.get("tcomment"),
                ),
            )
            entry_id = cur.lastrowid

            # リファレンスを追加
            for ref in entry.get("references", []):
                cur.execute(
                    "INSERT INTO entry_references (entry_id, reference) VALUES (?, ?)",
                    (entry_id, ref),
                )

            # フラグを追加
            for flag in entry.get("flags", []):
                cur.execute(
                    "INSERT INTO entry_flags (entry_id, flag) VALUES (?, ?)",
                    (entry_id, flag),
                )

            # 表示順を追加
            cur.execute(
                "INSERT INTO display_order (entry_id, position) VALUES (?, ?)",
                (entry_id, entry.get("position", 0)),
            )
        logger.debug("エントリ追加完了: %s", entry["key"])

    def clear(self) -> None:
        """全てのデータを削除"""
        with self.transaction() as cur:
            cur.execute("DELETE FROM entry_references")
            cur.execute("DELETE FROM entry_flags")
            cur.execute("DELETE FROM display_order")
            cur.execute("DELETE FROM entries")

    def get_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """エントリを取得"""
        with self.transaction() as cur:
            # エントリを取得
            cur.execute("""
                SELECT 
                    e.*,
                    d.position
                FROM entries e
                LEFT JOIN display_order d ON e.id = d.entry_id
                WHERE e.id = ?
            """, (entry_id,))
            row = cur.fetchone()
            if not row:
                return None

            entry = dict(row)

            # リファレンスを取得
            cur.execute(
                "SELECT reference FROM entry_references WHERE entry_id = ?",
                (entry_id,)
            )
            entry["references"] = [r[0] for r in cur.fetchall()]

            # フラグを取得
            cur.execute(
                "SELECT flag FROM entry_flags WHERE entry_id = ?",
                (entry_id,)
            )
            entry["flags"] = [r[0] for r in cur.fetchall()]

            return entry

    def get_entry_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """キーでエントリを取得"""
        with self.transaction() as cur:
            # エントリを取得
            cur.execute("""
                SELECT 
                    e.*,
                    d.position
                FROM entries e
                LEFT JOIN display_order d ON e.id = d.entry_id
                WHERE e.key = ?
            """, (key,))
            row = cur.fetchone()
            if not row:
                return None

            entry = dict(row)

            # リファレンスを取得
            cur.execute(
                "SELECT reference FROM entry_references WHERE entry_id = ?",
                (entry["id"],)
            )
            entry["references"] = [r[0] for r in cur.fetchall()]

            # フラグを取得
            cur.execute(
                "SELECT flag FROM entry_flags WHERE entry_id = ?",
                (entry["id"],)
            )
            entry["flags"] = [r[0] for r in cur.fetchall()]

            return entry

    def update_entry(self, key: str, entry: Dict[str, Any]) -> None:
        """エントリを更新する

        Args:
            key: エントリのキー
            entry: 更新するエントリ
        """
        logger.debug("エントリ更新開始: %s", key)
        with self.transaction() as cur:
            # エントリを更新
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
                    entry.get("msgctxt"),
                    entry["msgid"],
                    entry["msgstr"],
                    entry.get("fuzzy", False),
                    entry.get("obsolete", False),
                    entry.get("previous_msgid"),
                    entry.get("previous_msgid_plural"),
                    entry.get("previous_msgctxt"),
                    entry.get("comment"),
                    entry.get("tcomment"),
                    key,
                ),
            )

            # リファレンスを更新
            cur.execute("DELETE FROM entry_references WHERE entry_id IN (SELECT id FROM entries WHERE key = ?)", (key,))
            for ref in entry.get("references", []):
                cur.execute(
                    """
                    INSERT INTO entry_references (entry_id, reference)
                    SELECT id, ? FROM entries WHERE key = ?
                    """,
                    (ref, key),
                )

            # フラグを更新
            cur.execute("DELETE FROM entry_flags WHERE entry_id IN (SELECT id FROM entries WHERE key = ?)", (key,))
            for flag in entry.get("flags", []):
                cur.execute(
                    """
                    INSERT INTO entry_flags (entry_id, flag)
                    SELECT id, ? FROM entries WHERE key = ?
                    """,
                    (flag, key),
                )

            # 表示順を更新
            if "position" in entry:
                cur.execute(
                    """
                    UPDATE display_order SET
                        position = ?
                    WHERE entry_id IN (SELECT id FROM entries WHERE key = ?)
                    """,
                    (entry["position"], key),
                )

        logger.debug("エントリ更新完了: %s", key)

    def get_entries(
        self,
        filter_text: Optional[str] = None,
        search_text: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[Dict[str, Any]] = None,
        translation_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """エントリの一覧を取得

        Args:
            filter_text: フィルタテキスト
            search_text: 検索テキスト
            sort_column: ソートするカラム
            sort_order: ソート順序
            flag_conditions: フラグによるフィルタリング条件
                {
                    "include_flags": List[str],  # 含むべきフラグ
                    "exclude_flags": List[str],  # 除外するフラグ
                    "only_fuzzy": bool,  # fuzzyフラグを持つエントリのみ
                }
            translation_status: 翻訳状態によるフィルタリング
                "translated": 翻訳済み
                "untranslated": 未翻訳

        Returns:
            List[Dict[str, Any]]: エントリのリスト
        """
        query = """
            SELECT e.*, GROUP_CONCAT(f.flag) as flags, d.position
            FROM entries e
            LEFT JOIN entry_flags f ON e.id = f.entry_id
            LEFT JOIN display_order d ON e.id = d.entry_id
        """
        conditions = []
        params = []

        # フラグによるフィルタリング
        if flag_conditions:
            if "include_flags" in flag_conditions:
                flags = flag_conditions["include_flags"]
                placeholders = ", ".join("?" * len(flags))
                conditions.append(f"""
                    e.id IN (
                        SELECT entry_id
                        FROM entry_flags
                        WHERE flag IN ({placeholders})
                        GROUP BY entry_id
                        HAVING COUNT(DISTINCT flag) = {len(flags)}
                    )
                """)
                params.extend(flags)

            if "exclude_flags" in flag_conditions:
                flags = flag_conditions["exclude_flags"]
                placeholders = ", ".join("?" * len(flags))
                conditions.append(f"""
                    e.id NOT IN (
                        SELECT entry_id
                        FROM entry_flags
                        WHERE flag IN ({placeholders})
                    )
                """)
                params.extend(flags)

            if flag_conditions.get("only_fuzzy"):
                conditions.append("""
                    e.id IN (
                        SELECT entry_id
                        FROM entry_flags
                        WHERE flag = 'fuzzy'
                    )
                """)

        # 翻訳状態によるフィルタリング
        if translation_status == "translated":
            conditions.append("""
                e.msgstr != '' AND
                e.id NOT IN (
                    SELECT entry_id
                    FROM entry_flags
                    WHERE flag = 'fuzzy'
                )
            """)
        elif translation_status == "untranslated":
            conditions.append("""
                (e.msgstr = '' OR
                e.id IN (
                    SELECT entry_id
                    FROM entry_flags
                    WHERE flag = 'fuzzy'
                ))
            """)

        # 既存の検索条件
        if filter_text:
            conditions.append("(e.msgid LIKE ? OR e.msgstr LIKE ?)")
            params.extend([f"%{filter_text}%", f"%{filter_text}%"])

        if search_text:
            conditions.append("(e.msgid LIKE ? OR e.msgstr LIKE ?)")
            params.extend([f"%{search_text}%", f"%{search_text}%"])

        # WHERE句の構築
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # GROUP BY句の追加
        query += " GROUP BY e.id"

        # ORDER BY句の追加
        if sort_column and sort_order:
            query += f" ORDER BY {sort_column} {sort_order}"
        else:
            query += " ORDER BY COALESCE(d.position, 0)"

        cursor = self._conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def reorder_entries(self, entry_ids: List[int]) -> None:
        """エントリの表示順序を変更"""
        with self.transaction() as cur:
            # 一時的に制約を無効化
            cur.execute("PRAGMA foreign_keys = OFF")
            
            try:
                # 表示順序を更新
                cur.execute("DELETE FROM display_order")
                # enumerate関数は(index, value)のタプルを生成するため、
                # SQLのVALUES句に合わせて(value, index)の順序に入れ替える
                cur.executemany(
                    "INSERT INTO display_order (entry_id, position) VALUES (?, ?)",
                    [(entry_id, i) for i, entry_id in enumerate(entry_ids)]
                )
            finally:
                # 制約を有効化
                cur.execute("PRAGMA foreign_keys = ON")
