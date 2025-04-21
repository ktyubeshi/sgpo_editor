"""翻訳評価データベースモデル

このモジュールは、翻訳評価結果を保存するためのデータベースモデルを提供します。
"""

import json
import logging
import os
import sqlite3
from typing import List, Optional, cast

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.models.evaluation_state import EvaluationState
from sgpo_editor.types import (
    ReviewCommentType,
    ReviewDataDict,
    MetricScores,
    CategoryScores,
)

logger = logging.getLogger(__name__)


class EvaluationDatabase:
    """翻訳評価データベース

    POファイルのサイドカーとして、翻訳評価結果を保存するためのSQLiteデータベース。
    """

    def __init__(self, po_file_path: str):
        """初期化

        Args:
            po_file_path: POファイルのパス
        """
        self.po_file_path = po_file_path
        self.db_path = self._get_db_path(po_file_path)
        self.conn: Optional[sqlite3.Connection] = None
        self.initialized = False

    def _get_db_path(self, po_file_path: str) -> str:
        """データベースファイルのパスを取得

        Args:
            po_file_path: POファイルのパス

        Returns:
            str: データベースファイルのパス
        """
        # POファイルと同じディレクトリに、.evaldb拡張子で保存
        base_path, _ = os.path.splitext(po_file_path)
        return f"{base_path}.evaldb"

    def connect(self) -> None:
        """データベースに接続"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            if not self.initialized:
                self._initialize_db()
                self.initialized = True
        except sqlite3.Error as e:
            logger.error(f"データベース接続エラー: {e}")
            raise

    def close(self) -> None:
        """データベース接続を閉じる"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _initialize_db(self) -> None:
        """データベーススキーマを初期化"""
        if not self.conn:
            self.connect()

        try:
            cursor = self.conn.cursor()

            # エントリ識別テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    msgctxt TEXT,
                    msgid TEXT,
                    entry_key TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # 評価状態テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_states (
                    entry_id INTEGER PRIMARY KEY,
                    state INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id)
                )
                """
            )

            # 総合スコアテーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS overall_scores (
                    entry_id INTEGER PRIMARY KEY,
                    score INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id)
                )
                """
            )

            # 評価指標別スコアテーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metric_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    metric_name TEXT,
                    score INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id),
                    UNIQUE(entry_id, metric_name)
                )
                """
            )

            # レビューコメントテーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS review_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    comment_id TEXT,
                    author TEXT,
                    comment TEXT,
                    language TEXT DEFAULT 'ja',
                    created_at TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id)
                )
                """
            )

            # カテゴリ別スコアテーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS category_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    category_name TEXT,
                    score INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id),
                    UNIQUE(entry_id, category_name)
                )
                """
            )

            # 評価履歴テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER,
                    evaluation_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES entries (id)
                )
                """
            )

            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"データベース初期化エラー: {e}")
            self.conn.rollback()
            raise

    def _get_or_create_entry_id(self, entry: EntryModel) -> int:
        """エントリIDを取得または作成

        Args:
            entry: エントリモデル

        Returns:
            int: エントリID
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        entry_key = entry.key

        # エントリを検索
        cursor.execute("SELECT id FROM entries WHERE entry_key = ?", (entry_key,))
        result = cursor.fetchone()

        if result:
            return result["id"]

        # エントリが存在しない場合は作成
        cursor.execute(
            """
            INSERT INTO entries (msgctxt, msgid, entry_key)
            VALUES (?, ?, ?)
            """,
            (entry.msgctxt, entry.msgid, entry_key),
        )
        self.conn.commit()
        lastrowid = cursor.lastrowid
        if lastrowid is None:
            cursor.execute("SELECT id FROM entries WHERE entry_key = ?", (entry_key,))
            result = cursor.fetchone()
            if result:
                return result["id"]
            raise ValueError(f"Failed to create entry ID for {entry_key}")
        return lastrowid

    def save_evaluation_state(self, entry: EntryModel, state: EvaluationState) -> None:
        """評価状態を保存

        Args:
            entry: エントリモデル
            state: 評価状態
        """
        if not self.conn:
            self.connect()

        try:
            entry_id = self._get_or_create_entry_id(entry)
            cursor = self.conn.cursor()

            # 評価状態を更新または挿入
            cursor.execute(
                """
                INSERT OR REPLACE INTO evaluation_states (entry_id, state, updated_at)
                VALUES (?, ?, datetime('now'))
                """,
                (entry_id, state.value),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"評価状態保存エラー: {e}")
            self.conn.rollback()
            raise

    def get_evaluation_state(self, entry: EntryModel) -> EvaluationState:
        """評価状態を取得

        Args:
            entry: エントリモデル

        Returns:
            EvaluationState: 評価状態
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        entry_id = self._get_or_create_entry_id(entry)

        cursor.execute(
            "SELECT state FROM evaluation_states WHERE entry_id = ?", (entry_id,)
        )
        result = cursor.fetchone()

        if result:
            state_value = result["state"]
            # 整数値から列挙型に変換
            for state in EvaluationState:
                if state.value == state_value:
                    return state

        # デフォルトは未評価
        return EvaluationState.NOT_EVALUATED

    def save_overall_score(self, entry: EntryModel, score: int) -> None:
        """総合スコアを保存

        Args:
            entry: エントリモデル
            score: スコア値（0-100）
        """
        if not self.conn:
            self.connect()

        try:
            entry_id = self._get_or_create_entry_id(entry)
            cursor = self.conn.cursor()

            # スコアを更新または挿入
            cursor.execute(
                """
                INSERT OR REPLACE INTO overall_scores (entry_id, score, updated_at)
                VALUES (?, ?, datetime('now'))
                """,
                (entry_id, score),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"総合スコア保存エラー: {e}")
            self.conn.rollback()
            raise

    def get_overall_score(self, entry: EntryModel) -> Optional[int]:
        """総合スコアを取得

        Args:
            entry: エントリモデル

        Returns:
            Optional[int]: スコア値（0-100）または未設定の場合はNone
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        entry_id = self._get_or_create_entry_id(entry)

        cursor.execute(
            "SELECT score FROM overall_scores WHERE entry_id = ?", (entry_id,)
        )
        result = cursor.fetchone()

        return result["score"] if result else None

    def save_metric_score(
        self, entry: EntryModel, metric_name: str, score: int
    ) -> None:
        """評価指標スコアを保存

        Args:
            entry: エントリモデル
            metric_name: 評価指標名
            score: スコア値（0-100）
        """
        if not self.conn:
            self.connect()

        try:
            entry_id = self._get_or_create_entry_id(entry)
            cursor = self.conn.cursor()

            # 評価指標スコアを更新または挿入
            cursor.execute(
                """
                INSERT OR REPLACE INTO metric_scores (entry_id, metric_name, score, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (entry_id, metric_name, score),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"評価指標スコア保存エラー: {e}")
            self.conn.rollback()
            raise

    def get_metric_scores(self, entry: EntryModel) -> MetricScores:
        """評価指標スコアを取得

        Args:
            entry: エントリモデル

        Returns:
            MetricScores: 評価指標名とスコア値のマップ
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        entry_id = self._get_or_create_entry_id(entry)

        cursor.execute(
            """
            SELECT metric_name, score
            FROM metric_scores
            WHERE entry_id = ?
            """,
            (entry_id,),
        )
        results = cursor.fetchall()

        return {row["metric_name"]: float(row["score"]) for row in results}

    def save_review_comment(
        self,
        entry: EntryModel,
        comment_id: str,
        author: str,
        comment: str,
        language: str = "ja",
    ) -> None:
        """レビューコメントを保存

        Args:
            entry: エントリモデル
            comment_id: コメントID
            author: 作成者
            comment: コメント内容
            language: 言語コード（デフォルト: ja）
        """
        if not self.conn:
            self.connect()

        try:
            entry_id = self._get_or_create_entry_id(entry)
            cursor = self.conn.cursor()

            # レビューコメントを挿入
            cursor.execute(
                """
                INSERT INTO review_comments (entry_id, comment_id, author, comment, language, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (entry_id, comment_id, author, comment, language),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"レビューコメント保存エラー: {e}")
            self.conn.rollback()
            raise

    def get_review_comments(
        self, entry: EntryModel, language: Optional[str] = None
    ) -> List[ReviewCommentType]:
        """レビューコメントを取得

        Args:
            entry: エントリモデル
            language: 言語コード（指定がない場合は全言語）

        Returns:
            List[ReviewCommentType]: レビューコメントのリスト
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        entry_id = self._get_or_create_entry_id(entry)

        if language:
            cursor.execute(
                """
                SELECT comment_id, author, comment, language, created_at
                FROM review_comments
                WHERE entry_id = ? AND language = ?
                ORDER BY created_at DESC
                """,
                (entry_id, language),
            )
        else:
            cursor.execute(
                """
                SELECT comment_id, author, comment, language, created_at
                FROM review_comments
                WHERE entry_id = ?
                ORDER BY created_at DESC
                """,
                (entry_id,),
            )

        results = cursor.fetchall()
        comments: List[ReviewCommentType] = []

        for row in results:
            comments.append(
                {
                    "id": row["comment_id"],
                    "author": row["author"],
                    "comment": row["comment"],
                    "language": row["language"],
                    "created_at": row["created_at"],
                }
            )

        return comments

    def save_category_score(
        self, entry: EntryModel, category_name: str, score: int
    ) -> None:
        """カテゴリ別スコアを保存

        Args:
            entry: エントリモデル
            category_name: カテゴリ名
            score: スコア値（0-100）
        """
        if not self.conn:
            self.connect()

        try:
            entry_id = self._get_or_create_entry_id(entry)
            cursor = self.conn.cursor()

            # カテゴリ別スコアを更新または挿入
            cursor.execute(
                """
                INSERT OR REPLACE INTO category_scores (entry_id, category_name, score, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (entry_id, category_name, score),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"カテゴリ別スコア保存エラー: {e}")
            self.conn.rollback()
            raise

    def get_category_scores(self, entry: EntryModel) -> CategoryScores:
        """カテゴリ別スコアを取得

        Args:
            entry: エントリモデル

        Returns:
            CategoryScores: カテゴリ名とスコア値のマップ
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        entry_id = self._get_or_create_entry_id(entry)

        cursor.execute(
            """
            SELECT category_name, score
            FROM category_scores
            WHERE entry_id = ?
            """,
            (entry_id,),
        )
        results = cursor.fetchall()

        return {row["category_name"]: float(row["score"]) for row in results}

    def save_evaluation_history(self, entry: EntryModel, data: ReviewDataDict) -> None:
        """評価履歴を保存

        Args:
            entry: エントリモデル
            data: 評価データ
        """
        if not self.conn:
            self.connect()

        try:
            entry_id = self._get_or_create_entry_id(entry)
            cursor = self.conn.cursor()

            # 評価データをJSON形式で保存
            json_data = json.dumps(data, ensure_ascii=False)
            cursor.execute(
                """
                INSERT INTO evaluation_history (entry_id, evaluation_data, created_at)
                VALUES (?, ?, datetime('now'))
                """,
                (entry_id, json_data),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"評価履歴保存エラー: {e}")
            self.conn.rollback()
            raise

    def get_evaluation_history(self, entry: EntryModel) -> List[ReviewDataDict]:
        """評価履歴を取得

        Args:
            entry: エントリモデル

        Returns:
            List[ReviewDataDict]: 評価履歴のリスト
        """
        if not self.conn:
            self.connect()

        cursor = self.conn.cursor()
        entry_id = self._get_or_create_entry_id(entry)

        cursor.execute(
            """
            SELECT evaluation_data, created_at
            FROM evaluation_history
            WHERE entry_id = ?
            ORDER BY created_at DESC
            """,
            (entry_id,),
        )
        results = cursor.fetchall()
        history: List[ReviewDataDict] = []

        for row in results:
            data = cast(ReviewDataDict, json.loads(row["evaluation_data"]))
            data["created_at"] = row["created_at"]
            history.append(data)

        return history

    def load_entry_evaluation_data(self, entry: EntryModel) -> None:
        """エントリの評価データをロード

        Args:
            entry: エントリモデル
        """
        if not self.conn:
            self.connect()

        # 評価状態を取得
        state = self.get_evaluation_state(entry)
        entry.evaluation_state = state

        # 総合スコアを取得
        overall_score = self.get_overall_score(entry)
        if overall_score is not None:
            entry.overall_quality_score = overall_score

        # 評価指標スコアを取得
        metric_scores = self.get_metric_scores(entry)
        for metric_name, score in metric_scores.items():
            entry.set_metric_score(metric_name, score)

        # カテゴリ別スコアを取得
        category_scores = self.get_category_scores(entry)
        for category_name, score in category_scores.items():
            entry.set_category_score(category_name, score)

        # レビューコメントを取得
        review_comments = self.get_review_comments(entry)
        entry.review_comments = review_comments

    def save_entry_evaluation_data(self, entry: EntryModel) -> None:
        """エントリの評価データを保存

        Args:
            entry: エントリモデル
        """
        if not self.conn:
            self.connect()

        # 評価状態を保存
        self.save_evaluation_state(entry, entry.evaluation_state)

        # 総合スコアを保存
        if entry.overall_quality_score is not None:
            # float型からint型に変換
            overall_score = int(entry.overall_quality_score)
            self.save_overall_score(entry, overall_score)

        # 評価指標スコアを保存
        for metric_name, score in entry.metric_scores.items():
            # float型からint型に変換
            metric_score = int(score)
            self.save_metric_score(entry, metric_name, metric_score)

        # カテゴリ別スコアを保存
        for category_name, score in entry.category_quality_scores.items():
            # float型からint型に変換
            category_score = int(score)
            self.save_category_score(entry, category_name, category_score)

        # レビューコメントを保存
        for comment in entry.review_comments:
            self.save_review_comment(
                entry,
                comment["id"],
                comment["author"],
                comment["comment"],
                comment.get("language", "ja"),
            )

        # 評価履歴を保存
        history_data = {
            "overall_score": entry.overall_quality_score,
            "metric_scores": entry.metric_scores,
            "category_scores": entry.category_quality_scores,
        }
        self.save_evaluation_history(entry, history_data)

    def load_all_entries_evaluation_data(self, entries: List[EntryModel]) -> None:
        """全エントリの評価データをロード

        Args:
            entries: エントリモデルのリスト
        """
        for entry in entries:
            self.load_entry_evaluation_data(entry)

    def save_all_entries_evaluation_data(self, entries: List[EntryModel]) -> None:
        """全エントリの評価データを保存

        Args:
            entries: エントリモデルのリスト
        """
        for entry in entries:
            self.save_entry_evaluation_data(entry)
