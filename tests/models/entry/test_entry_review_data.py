"""エントリモデルのレビューデータ機能テスト"""

import unittest
import uuid

from sgpo_editor.models.entry import EntryModel


class TestEntryReviewData(unittest.TestCase):
    """エントリモデルのレビューデータ機能テスト"""

    def setUp(self):
        """テスト前の準備"""
        self.entry = EntryModel(
            key=f"test-key-{uuid.uuid4()}",
            msgid="Hello, world!",
            msgstr="こんにちは、世界！",
            flags=["fuzzy"],
        )

    def test_translator_comment(self):
        """翻訳者コメントの設定と取得をテスト"""
        # 初期状態では翻訳者コメントはNone
        self.assertIsNone(self.entry.tcomment)

        # 翻訳者コメントを設定
        test_comment = "これは翻訳者コメントです。"
        self.entry.tcomment = test_comment

        # 設定したコメントが取得できることを確認
        self.assertEqual(self.entry.tcomment, test_comment)

        # 辞書形式に変換したときにtcommentが含まれていることを確認
        entry_dict = self.entry.to_dict()
        self.assertIn("tcomment", entry_dict)
        self.assertEqual(entry_dict["tcomment"], test_comment)

    def test_review_comments(self):
        """レビューコメント機能をテスト"""
        # 初期状態ではレビューコメントは空リスト
        self.assertEqual(self.entry.review_comments, [])

        # レビューコメントを追加
        comment_id = self.entry.add_review_comment(
            author="テスト太郎", comment="これはテストコメントです。"
        )

        # コメントが追加されたことを確認
        self.assertEqual(len(self.entry.review_comments), 1)
        self.assertEqual(self.entry.review_comments[0]["author"], "テスト太郎")
        self.assertEqual(
            self.entry.review_comments[0]["comment"], "これはテストコメントです。"
        )
        self.assertEqual(self.entry.review_comments[0]["id"], comment_id)

        # さらにコメントを追加
        comment_id2 = self.entry.add_review_comment(
            author="テスト花子", comment="二つ目のコメントです。"
        )

        # 2つのコメントが存在することを確認
        self.assertEqual(len(self.entry.review_comments), 2)

        # コメントを削除
        result = self.entry.remove_review_comment(comment_id)

        # 削除が成功したことを確認
        self.assertTrue(result)
        self.assertEqual(len(self.entry.review_comments), 1)
        self.assertEqual(self.entry.review_comments[0]["id"], comment_id2)

        # 存在しないIDで削除を試みると失敗することを確認
        result = self.entry.remove_review_comment("non-existent-id")
        self.assertFalse(result)

        # 全てのコメントをクリア
        self.entry.clear_review_comments()
        self.assertEqual(self.entry.review_comments, [])

    def test_quality_score(self):
        """品質スコア機能をテスト"""
        # 初期状態では品質スコアはNone
        self.assertIsNone(self.entry.overall_quality_score)
        self.assertEqual(self.entry.category_quality_scores, {})

        # 品質スコアを設定
        self.entry.set_overall_quality_score(85)
        self.assertEqual(self.entry.overall_quality_score, 85)

        # カテゴリスコアを設定
        self.entry.set_category_score("正確性", 90)
        self.entry.set_category_score("流暢さ", 80)

        # カテゴリスコアが設定されたことを確認
        self.assertEqual(len(self.entry.category_quality_scores), 2)
        self.assertEqual(self.entry.category_quality_scores["正確性"], 90)
        self.assertEqual(self.entry.category_quality_scores["流暢さ"], 80)

        # スコアをクリア
        self.entry.clear_quality_scores()
        self.assertIsNone(self.entry.overall_quality_score)
        self.assertEqual(self.entry.category_quality_scores, {})

    def test_check_results(self):
        """チェック結果機能をテスト"""
        # 初期状態ではチェック結果は空リスト
        self.assertEqual(self.entry.check_results, [])

        # チェック結果を追加
        self.entry.add_check_result(
            code=1001, message="フォーマットエラー", severity="warning"
        )

        # チェック結果が追加されたことを確認
        self.assertEqual(len(self.entry.check_results), 1)
        self.assertEqual(self.entry.check_results[0]["code"], 1001)
        self.assertEqual(self.entry.check_results[0]["message"], "フォーマットエラー")
        self.assertEqual(self.entry.check_results[0]["severity"], "warning")

        # さらにチェック結果を追加
        self.entry.add_check_result(code=2002, message="文法エラー", severity="error")

        # 2つのチェック結果が存在することを確認
        self.assertEqual(len(self.entry.check_results), 2)

        # コードでチェック結果を削除
        result = self.entry.remove_check_result(1001)

        # 削除が成功したことを確認
        self.assertTrue(result)
        self.assertEqual(len(self.entry.check_results), 1)
        self.assertEqual(self.entry.check_results[0]["code"], 2002)

        # 存在しないコードで削除を試みると失敗することを確認
        result = self.entry.remove_check_result(9999)
        self.assertFalse(result)

        # 全てのチェック結果をクリア
        self.entry.clear_check_results()
        self.assertEqual(self.entry.check_results, [])

    def test_to_dict_includes_review_data(self):
        """to_dict()でレビューデータが正しく含まれることをテスト"""
        # レビューデータを追加
        self.entry.tcomment = "翻訳者コメント"
        self.entry.add_review_comment(author="レビュアー1", comment="レビューコメント")
        self.entry.set_overall_quality_score(75)
        self.entry.set_category_score("正確性", 80)
        self.entry.add_check_result(
            code=1001, message="フォーマットエラー", severity="warning"
        )

        # 辞書に変換
        entry_dict = self.entry.to_dict()

        # レビューデータが含まれていることを確認
        self.assertEqual(entry_dict["tcomment"], "翻訳者コメント")
        self.assertEqual(len(entry_dict["review_comments"]), 1)
        self.assertEqual(entry_dict["overall_quality_score"], 75)
        self.assertEqual(len(entry_dict["category_quality_scores"]), 1)
        self.assertEqual(entry_dict["category_quality_scores"]["正確性"], 80)
        self.assertEqual(len(entry_dict["check_results"]), 1)
        self.assertEqual(entry_dict["check_results"][0]["code"], 1001)


if __name__ == "__main__":
    unittest.main()
