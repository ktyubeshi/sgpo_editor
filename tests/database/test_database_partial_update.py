"""データベースの部分更新テスト"""

import unittest
import uuid
from datetime import datetime

from sgpo_editor.models.database import Database


class TestDatabasePartialUpdate(unittest.TestCase):
    """データベースの部分更新テスト"""

    def setUp(self):
        """テスト前の準備"""
        self.db = Database()
        self._prepare_test_data()

    def _prepare_test_data(self):
        """テスト用のデータを準備"""
        self.test_entry = {
            "key": f"test-key-{uuid.uuid4()}",
            "msgid": "test message id",
            "msgstr": "test message string",
            "flags": ["fuzzy"],
            "references": ["file.c:123"],
            "position": 1,
            "tcomment": "初期コメント",
        }
        self.db.add_entry(self.test_entry)
        self.entry_from_db = self.db.get_entry_by_key(self.test_entry["key"])

    def test_update_fuzzy_flag(self):
        """Fuzzyフラグの部分更新テスト"""
        # Fuzzyフラグを更新
        result = self.db.update_entry_field(self.test_entry["key"], "fuzzy", False)
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertNotIn("fuzzy", updated_entry["flags"])

        # 他のフィールドは変更されていないことを確認
        self.assertEqual(updated_entry["msgid"], self.test_entry["msgid"])
        self.assertEqual(updated_entry["msgstr"], self.test_entry["msgstr"])

    def test_update_tcomment(self):
        """翻訳者コメントの部分更新テスト"""
        # 翻訳者コメントを更新
        new_comment = "更新されたコメント"
        result = self.db.update_entry_field(
            self.test_entry["key"], "tcomment", new_comment
        )
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertEqual(updated_entry["tcomment"], new_comment)

        # 他のフィールドは変更されていないことを確認
        self.assertEqual(updated_entry["msgid"], self.test_entry["msgid"])
        self.assertEqual(updated_entry["msgstr"], self.test_entry["msgstr"])

    def test_update_quality_score(self):
        """品質スコアの部分更新テスト"""
        # 品質スコアを更新
        quality_score = 85
        result = self.db.update_entry_review_data(
            self.test_entry["key"], "quality_score", quality_score
        )
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertIn("review_data", updated_entry)
        self.assertEqual(updated_entry["review_data"]["quality_score"], quality_score)

        # 他のフィールドは変更されていないことを確認
        self.assertEqual(updated_entry["msgid"], self.test_entry["msgid"])
        self.assertEqual(updated_entry["msgstr"], self.test_entry["msgstr"])

    def test_update_category_scores(self):
        """カテゴリスコアの部分更新テスト"""
        # カテゴリスコアを更新
        category_scores = {
            "正確性": 90,
            "流暢さ": 80,
        }
        result = self.db.update_entry_review_data(
            self.test_entry["key"], "category_scores", category_scores
        )
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertIn("review_data", updated_entry)
        self.assertEqual(
            updated_entry["review_data"]["category_scores"], category_scores
        )

    def test_add_review_comment(self):
        """レビューコメントの追加テスト"""
        # レビューコメントを追加
        comment = {
            "id": f"comment-{uuid.uuid4()}",
            "author": "テスト太郎",
            "comment": "テストコメント",
            "created_at": datetime.now().isoformat(),
        }
        result = self.db.add_review_comment(self.test_entry["key"], comment)
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertIn("review_data", updated_entry)
        self.assertIn("review_comments", updated_entry["review_data"])
        self.assertEqual(len(updated_entry["review_data"]["review_comments"]), 1)
        self.assertEqual(
            updated_entry["review_data"]["review_comments"][0]["author"], "テスト太郎"
        )
        self.assertEqual(
            updated_entry["review_data"]["review_comments"][0]["comment"],
            "テストコメント",
        )

    def test_remove_review_comment(self):
        """レビューコメントの削除テスト"""
        # まずレビューコメントを追加
        comment_id = f"comment-{uuid.uuid4()}"
        comment = {
            "id": comment_id,
            "author": "テスト太郎",
            "comment": "削除されるコメント",
            "created_at": datetime.now().isoformat(),
        }
        self.db.add_review_comment(self.test_entry["key"], comment)

        # コメントを削除
        result = self.db.remove_review_comment(self.test_entry["key"], comment_id)
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertIn("review_data", updated_entry)
        self.assertIn("review_comments", updated_entry["review_data"])
        self.assertEqual(len(updated_entry["review_data"]["review_comments"]), 0)

    def test_add_check_result(self):
        """チェック結果の追加テスト"""
        # チェック結果を追加
        check_result = {
            "code": "format-error",
            "message": "フォーマットエラー",
            "severity": "warning",
            "created_at": datetime.now().isoformat(),
        }
        result = self.db.add_check_result(self.test_entry["key"], check_result)
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertIn("review_data", updated_entry)
        self.assertIn("check_results", updated_entry["review_data"])
        self.assertEqual(len(updated_entry["review_data"]["check_results"]), 1)
        self.assertEqual(
            updated_entry["review_data"]["check_results"][0]["code"], "format-error"
        )
        self.assertEqual(
            updated_entry["review_data"]["check_results"][0]["message"],
            "フォーマットエラー",
        )

    def test_remove_check_result(self):
        """チェック結果の削除テスト"""
        # まずチェック結果を追加
        check_result = {
            "code": "format-error",
            "message": "削除されるエラー",
            "severity": "warning",
            "created_at": datetime.now().isoformat(),
        }
        self.db.add_check_result(self.test_entry["key"], check_result)

        # チェック結果を削除
        result = self.db.remove_check_result(self.test_entry["key"], "format-error")
        self.assertTrue(result)

        # 更新後のエントリを取得して確認
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        self.assertIn("review_data", updated_entry)
        self.assertIn("check_results", updated_entry["review_data"])
        self.assertEqual(len(updated_entry["review_data"]["check_results"]), 0)


if __name__ == "__main__":
    unittest.main()
