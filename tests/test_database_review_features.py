"""データベースのレビュー機能テスト"""
import unittest
from datetime import datetime
import uuid
from typing import Dict, Any

from sgpo_editor.models.database import Database


class TestDatabaseReviewFeatures(unittest.TestCase):
    """データベースのレビュー機能テスト"""

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
        }
        self.db.add_entry(self.test_entry)
        self.entry_from_db = self.db.get_entry_by_key(self.test_entry["key"])

    def test_add_review_comment(self):
        """レビューコメント追加のテスト"""
        # レビューコメント追加用のデータ
        review_data = {
            "review_comments": [
                {
                    "id": f"comment-{uuid.uuid4()}",
                    "author": "テスト太郎",
                    "comment": "これはテストコメントです",
                    "created_at": datetime.now().isoformat(),
                }
            ],
        }
        
        # エントリを更新用にコピー
        entry_to_update = self.entry_from_db.copy()
        entry_to_update["review_data"] = review_data
        
        # データベースに保存
        self.db.update_entry(self.test_entry["key"], entry_to_update)
        
        # 更新後のエントリを取得
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        
        # 検証
        self.assertIn("review_data", updated_entry)
        self.assertIn("review_comments", updated_entry["review_data"])
        self.assertEqual(len(updated_entry["review_data"]["review_comments"]), 1)
        self.assertEqual(
            updated_entry["review_data"]["review_comments"][0]["author"], 
            "テスト太郎"
        )
        self.assertEqual(
            updated_entry["review_data"]["review_comments"][0]["comment"], 
            "これはテストコメントです"
        )

    def test_update_quality_score(self):
        """品質スコア更新のテスト"""
        # 品質スコア用のデータ
        review_data = {
            "quality_score": 85,
            "category_scores": {
                "正確性": 90,
                "流暢さ": 80,
                "一貫性": 85,
            },
        }
        
        # エントリを更新用にコピー
        entry_to_update = self.entry_from_db.copy()
        entry_to_update["review_data"] = review_data
        
        # データベースに保存
        self.db.update_entry(self.test_entry["key"], entry_to_update)
        
        # 更新後のエントリを取得
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        
        # 検証
        self.assertIn("review_data", updated_entry)
        self.assertEqual(updated_entry["review_data"]["quality_score"], 85)
        self.assertEqual(len(updated_entry["review_data"]["category_scores"]), 3)
        self.assertEqual(updated_entry["review_data"]["category_scores"]["正確性"], 90)
        self.assertEqual(updated_entry["review_data"]["category_scores"]["流暢さ"], 80)
        self.assertEqual(updated_entry["review_data"]["category_scores"]["一貫性"], 85)

    def test_add_check_result(self):
        """チェック結果追加のテスト"""
        # チェック結果用のデータ
        review_data = {
            "check_results": [
                {
                    "code": "format-error",
                    "message": "フォーマットエラーがあります",
                    "severity": "warning",
                    "created_at": datetime.now().isoformat(),
                },
                {
                    "code": "grammar-error",
                    "message": "文法エラーがあります",
                    "severity": "error",
                    "created_at": datetime.now().isoformat(),
                },
            ],
        }
        
        # エントリを更新用にコピー
        entry_to_update = self.entry_from_db.copy()
        entry_to_update["review_data"] = review_data
        
        # データベースに保存
        self.db.update_entry(self.test_entry["key"], entry_to_update)
        
        # 更新後のエントリを取得
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        
        # 検証
        self.assertIn("review_data", updated_entry)
        self.assertIn("check_results", updated_entry["review_data"])
        self.assertEqual(len(updated_entry["review_data"]["check_results"]), 2)
        
        # 各チェック結果の検証
        for result in updated_entry["review_data"]["check_results"]:
            self.assertIn(result["code"], ["format-error", "grammar-error"])
            if result["code"] == "format-error":
                self.assertEqual(result["severity"], "warning")
                self.assertEqual(result["message"], "フォーマットエラーがあります")
            elif result["code"] == "grammar-error":
                self.assertEqual(result["severity"], "error")
                self.assertEqual(result["message"], "文法エラーがあります")

    def test_update_all_review_data_at_once(self):
        """すべてのレビューデータを一度に更新するテスト"""
        # すべてのレビューデータを含むデータ
        review_data = {
            "review_comments": [
                {
                    "id": f"comment-{uuid.uuid4()}",
                    "author": "山田太郎",
                    "comment": "全体的にOKです",
                    "created_at": datetime.now().isoformat(),
                }
            ],
            "quality_score": 90,
            "category_scores": {
                "正確性": 95,
                "流暢さ": 85,
            },
            "check_results": [
                {
                    "code": "spelling",
                    "message": "スペルミス",
                    "severity": "info",
                    "created_at": datetime.now().isoformat(),
                }
            ],
        }
        
        # エントリを更新用にコピー
        entry_to_update = self.entry_from_db.copy()
        entry_to_update["review_data"] = review_data
        
        # データベースに保存
        self.db.update_entry(self.test_entry["key"], entry_to_update)
        
        # 更新後のエントリを取得
        updated_entry = self.db.get_entry_by_key(self.test_entry["key"])
        
        # 検証
        self.assertIn("review_data", updated_entry)
        
        # レビューコメントの検証
        self.assertEqual(len(updated_entry["review_data"]["review_comments"]), 1)
        self.assertEqual(updated_entry["review_data"]["review_comments"][0]["author"], "山田太郎")
        
        # 品質スコアの検証
        self.assertEqual(updated_entry["review_data"]["quality_score"], 90)
        self.assertEqual(len(updated_entry["review_data"]["category_scores"]), 2)
        self.assertEqual(updated_entry["review_data"]["category_scores"]["正確性"], 95)
        
        # チェック結果の検証
        self.assertEqual(len(updated_entry["review_data"]["check_results"]), 1)
        self.assertEqual(updated_entry["review_data"]["check_results"][0]["code"], "spelling")
        self.assertEqual(updated_entry["review_data"]["check_results"][0]["severity"], "info")


if __name__ == "__main__":
    unittest.main()
