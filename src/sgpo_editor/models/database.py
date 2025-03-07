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
        # データベースをin-memory化（一時データとして扱う）
        logger.debug("インメモリデータベース初期化")
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
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
            
            # レビューコメントテーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS review_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    comment_id TEXT NOT NULL,
                    author TEXT,
                    comment TEXT NOT NULL,
                    created_at TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
                )
            """)
            
            # 品質スコアテーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS quality_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    overall_score INTEGER,
                    FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE
                )
            """)
            
            # カテゴリースコアテーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS category_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quality_score_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    FOREIGN KEY (quality_score_id) REFERENCES quality_scores (id) ON DELETE CASCADE
                )
            """)
            
            # チェック結果テーブル
            cur.execute("""
                CREATE TABLE IF NOT EXISTS check_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    created_at TIMESTAMP,
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
            cur.execute("CREATE INDEX IF NOT EXISTS idx_review_comments_entry_id ON review_comments(entry_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_quality_scores_entry_id ON quality_scores(entry_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_check_results_entry_id ON check_results(entry_id)")

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

            # レビュー関連データを取得
            entry["review_data"] = self._get_review_data(entry_id)

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

            # レビュー関連データを取得
            entry["review_data"] = self._get_review_data(entry["id"])

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

            # レビュー関連データを更新
            if "review_data" in entry:
                self._save_review_data(self.get_entry_by_key(key)["id"], entry["review_data"])

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
        entries = [dict(row) for row in cursor.fetchall()]

        # レビュー関連データを取得
        for entry in entries:
            entry["review_data"] = self._get_review_data(entry["id"])

        return entries

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

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """SQLiteの行を辞書に変換"""
        result = dict(row)
        
        # flags文字列をリストに変換
        if "flags" in result and result["flags"]:
            result["flags"] = result["flags"].split(",")
        else:
            result["flags"] = []
            
        return result
        
    def _get_review_data(self, entry_id: int) -> Dict[str, Any]:
        """エントリのレビュー関連データを取得"""
        review_data = {
            "review_comments": [],
            "quality_score": None,
            "category_scores": {},
            "check_results": []
        }
        
        with self.transaction() as cur:
            # レビューコメントを取得
            cur.execute("""
                SELECT comment_id, author, comment, created_at
                FROM review_comments
                WHERE entry_id = ?
            """, (entry_id,))
            
            for row in cur.fetchall():
                review_data["review_comments"].append({
                    "id": row[0],
                    "author": row[1],
                    "comment": row[2],
                    "created_at": row[3]
                })
                
            # 品質スコアを取得
            cur.execute("""
                SELECT id, overall_score
                FROM quality_scores
                WHERE entry_id = ?
            """, (entry_id,))
            
            quality_score_row = cur.fetchone()
            if quality_score_row:
                quality_score_id, overall_score = quality_score_row
                review_data["quality_score"] = overall_score
                
                # カテゴリースコアを取得
                cur.execute("""
                    SELECT category, score
                    FROM category_scores
                    WHERE quality_score_id = ?
                """, (quality_score_id,))
                
                for category, score in cur.fetchall():
                    review_data["category_scores"][category] = score
                    
            # チェック結果を取得
            cur.execute("""
                SELECT code, message, severity, created_at
                FROM check_results
                WHERE entry_id = ?
            """, (entry_id,))
            
            for row in cur.fetchall():
                review_data["check_results"].append({
                    "code": row[0],
                    "message": row[1],
                    "severity": row[2],
                    "created_at": row[3]
                })
                
        return review_data
    
    def _save_review_data(self, entry_id: int, review_data: Dict[str, Any]) -> None:
        """エントリのレビュー関連データを保存"""
        with self.transaction() as cur:
            # レビューコメント保存
            if "review_comments" in review_data:
                # 既存のレビューコメントを削除
                cur.execute("DELETE FROM review_comments WHERE entry_id = ?", (entry_id,))
                
                # 新しいレビューコメントを保存
                for comment in review_data["review_comments"]:
                    cur.execute("""
                        INSERT INTO review_comments 
                        (entry_id, comment_id, author, comment, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        entry_id,
                        comment["id"],
                        comment.get("author"),
                        comment["comment"],
                        comment.get("created_at")
                    ))
            
            # 品質スコア保存
            if "quality_score" in review_data or "category_scores" in review_data:
                # 既存の品質スコア情報を削除
                cur.execute("DELETE FROM quality_scores WHERE entry_id = ?", (entry_id,))
                
                quality_score = review_data.get("quality_score")
                category_scores = review_data.get("category_scores", {})
                
                if quality_score is not None or category_scores:
                    # 新しい品質スコアを保存
                    cur.execute("""
                        INSERT INTO quality_scores (entry_id, overall_score)
                        VALUES (?, ?)
                    """, (entry_id, quality_score))
                    
                    quality_score_id = cur.lastrowid
                    
                    # カテゴリースコアを保存
                    for category, score in category_scores.items():
                        cur.execute("""
                            INSERT INTO category_scores 
                            (quality_score_id, category, score)
                            VALUES (?, ?, ?)
                        """, (quality_score_id, category, score))
            
            # チェック結果保存
            if "check_results" in review_data:
                # 既存のチェック結果を削除
                cur.execute("DELETE FROM check_results WHERE entry_id = ?", (entry_id,))
                
                # 新しいチェック結果を保存
                for result in review_data["check_results"]:
                    cur.execute("""
                        INSERT INTO check_results 
                        (entry_id, code, message, severity, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        entry_id,
                        result["code"],
                        result["message"],
                        result["severity"],
                        result.get("created_at")
                    ))

    def update_entry_field(self, key: str, field: str, value: Any) -> bool:
        """エントリの特定フィールドのみを更新する
        
        Args:
            key: エントリのキー
            field: 更新するフィールド名
            value: 新しい値
            
        Returns:
            bool: 更新が成功したかどうか
        """
        logger.debug("エントリフィールド更新開始: %s.%s", key, field)
        try:
            with self.transaction() as cur:
                if field == "fuzzy":
                    # fuzzyフラグの場合は特別な処理が必要
                    entry_id = self._get_entry_id_by_key(cur, key)
                    if entry_id is None:
                        return False
                        
                    # 既存のフラグを取得
                    cur.execute(
                        "SELECT flag FROM entry_flags WHERE entry_id = ?",
                        (entry_id,)
                    )
                    flags = [r[0] for r in cur.fetchall()]
                    
                    if value and "fuzzy" not in flags:
                        # fuzzyフラグを追加
                        cur.execute(
                            "INSERT INTO entry_flags (entry_id, flag) VALUES (?, ?)",
                            (entry_id, "fuzzy")
                        )
                    elif not value and "fuzzy" in flags:
                        # fuzzyフラグを削除
                        cur.execute(
                            "DELETE FROM entry_flags WHERE entry_id = ? AND flag = ?",
                            (entry_id, "fuzzy")
                        )
                elif field in ["msgctxt", "msgid", "msgstr", "comment", "tcomment"]:
                    # 標準フィールドの場合は直接更新
                    cur.execute(
                        f"""
                        UPDATE entries SET
                            {field} = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE key = ?
                        """,
                        (value, key)
                    )
                else:
                    # サポートされていないフィールド
                    logger.warning("サポートされていないフィールド: %s", field)
                    return False
                    
                return True
        except Exception as e:
            logger.error("エントリフィールド更新エラー: %s", e, exc_info=True)
            return False
    
    def update_entry_review_data(self, key: str, field: str, value: Any) -> bool:
        """エントリのレビュー関連データを部分的に更新する
        
        Args:
            key: エントリのキー
            field: 更新するフィールド名（quality_score, category_scores）
            value: 新しい値
            
        Returns:
            bool: 更新が成功したかどうか
        """
        logger.debug("エントリレビューデータ更新開始: %s.%s", key, field)
        try:
            entry_id = self._get_entry_id_by_key(None, key)
            if entry_id is None:
                return False
                
            # 現在のレビューデータを取得
            review_data = self._get_review_data(entry_id)
            
            # 指定されたフィールドを更新
            review_data[field] = value
            
            # 更新したレビューデータを保存
            self._save_review_data(entry_id, review_data)
            return True
        except Exception as e:
            logger.error("エントリレビューデータ更新エラー: %s", e, exc_info=True)
            return False
    
    def add_review_comment(self, key: str, comment: Dict[str, Any]) -> bool:
        """エントリにレビューコメントを追加する
        
        Args:
            key: エントリのキー
            comment: 追加するコメント情報
            
        Returns:
            bool: 追加が成功したかどうか
        """
        logger.debug("レビューコメント追加開始: %s", key)
        try:
            entry_id = self._get_entry_id_by_key(None, key)
            if entry_id is None:
                return False
                
            # 現在のレビューデータを取得
            review_data = self._get_review_data(entry_id)
            
            # コメントを追加
            review_data["review_comments"].append(comment)
            
            # 更新したレビューデータを保存
            self._save_review_data(entry_id, review_data)
            return True
        except Exception as e:
            logger.error("レビューコメント追加エラー: %s", e, exc_info=True)
            return False
    
    def remove_review_comment(self, key: str, comment_id: str) -> bool:
        """エントリからレビューコメントを削除する
        
        Args:
            key: エントリのキー
            comment_id: 削除するコメントID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        logger.debug("レビューコメント削除開始: %s, %s", key, comment_id)
        try:
            entry_id = self._get_entry_id_by_key(None, key)
            if entry_id is None:
                return False
                
            # 現在のレビューデータを取得
            review_data = self._get_review_data(entry_id)
            
            # コメントを削除
            review_data["review_comments"] = [
                c for c in review_data["review_comments"]
                if c["id"] != comment_id
            ]
            
            # 更新したレビューデータを保存
            self._save_review_data(entry_id, review_data)
            return True
        except Exception as e:
            logger.error("レビューコメント削除エラー: %s", e, exc_info=True)
            return False
    
    def add_check_result(self, key: str, check_result: Dict[str, Any]) -> bool:
        """エントリにチェック結果を追加する
        
        Args:
            key: エントリのキー
            check_result: 追加するチェック結果
            
        Returns:
            bool: 追加が成功したかどうか
        """
        logger.debug("チェック結果追加開始: %s", key)
        try:
            entry_id = self._get_entry_id_by_key(None, key)
            if entry_id is None:
                return False
                
            # 現在のレビューデータを取得
            review_data = self._get_review_data(entry_id)
            
            # チェック結果を追加
            review_data["check_results"].append(check_result)
            
            # 更新したレビューデータを保存
            self._save_review_data(entry_id, review_data)
            return True
        except Exception as e:
            logger.error("チェック結果追加エラー: %s", e, exc_info=True)
            return False
    
    def remove_check_result(self, key: str, code: str) -> bool:
        """エントリからチェック結果を削除する
        
        Args:
            key: エントリのキー
            code: 削除するチェック結果のコード
            
        Returns:
            bool: 削除が成功したかどうか
        """
        logger.debug("チェック結果削除開始: %s, %s", key, code)
        try:
            entry_id = self._get_entry_id_by_key(None, key)
            if entry_id is None:
                return False
                
            # 現在のレビューデータを取得
            review_data = self._get_review_data(entry_id)
            
            # チェック結果を削除
            review_data["check_results"] = [
                r for r in review_data["check_results"]
                if r["code"] != code
            ]
            
            # 更新したレビューデータを保存
            self._save_review_data(entry_id, review_data)
            return True
        except Exception as e:
            logger.error("チェック結果削除エラー: %s", e, exc_info=True)
            return False
    
    def _get_entry_id_by_key(self, cur: Optional[sqlite3.Cursor], key: str) -> Optional[int]:
        """キーからエントリIDを取得する
        
        Args:
            cur: SQLiteカーソル（Noneの場合は新しいカーソルを作成）
            key: エントリのキー
            
        Returns:
            Optional[int]: エントリID（存在しない場合はNone）
        """
        close_cur = False
        if cur is None:
            cur = self._conn.cursor()
            close_cur = True
            
        try:
            cur.execute("SELECT id FROM entries WHERE key = ?", (key,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            if close_cur:
                cur.close()
