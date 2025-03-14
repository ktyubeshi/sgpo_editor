"""EntryModelの翻訳品質評価関連機能のテスト"""

import unittest
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.models.evaluation_state import EvaluationState


class TestEntryModelEvaluation(unittest.TestCase):
    """EntryModelの翻訳品質評価関連機能のテストケース"""

    def test_score_field(self):
        """スコアフィールドのテスト"""
        # デフォルト値
        entry = EntryModel(msgid="test", msgstr="テスト")
        self.assertIsNone(entry.score)

        # 値の設定と取得
        entry.score = 85
        self.assertEqual(entry.score, 85)

        # 範囲外の値 (0-100の範囲を想定)
        with self.assertRaises(ValueError):
            entry.score = -10

        with self.assertRaises(ValueError):
            entry.score = 120

    def test_evaluation_state(self):
        """評価状態のテスト"""
        # デフォルト値
        entry = EntryModel(msgid="test", msgstr="テスト")
        self.assertEqual(entry.evaluation_state, EvaluationState.NOT_EVALUATED)

        # 値の設定と取得
        entry.evaluation_state = EvaluationState.EVALUATING
        self.assertEqual(entry.evaluation_state, EvaluationState.EVALUATING)

        entry.evaluation_state = EvaluationState.EVALUATED
        self.assertEqual(entry.evaluation_state, EvaluationState.EVALUATED)

        # 不正な値の設定
        with self.assertRaises(TypeError):
            entry.evaluation_state = "EVALUATED"

    def test_review_comments_multilingual(self):
        """多言語レビューコメントのテスト"""
        entry = EntryModel(msgid="test", msgstr="テスト")

        # デフォルト値
        self.assertEqual(entry.review_comments, [])

        # 日本語のコメント追加
        comment_id_ja = entry.add_review_comment("テスト太郎", "翻訳の品質は良好です")
        self.assertEqual(len(entry.review_comments), 1)
        self.assertEqual(entry.review_comments[0]["author"], "テスト太郎")
        self.assertEqual(entry.review_comments[0]["comment"], "翻訳の品質は良好です")
        self.assertEqual(entry.review_comments[0]["id"], comment_id_ja)

        # 英語のコメント追加
        comment_id_en = entry.add_review_comment("Test User", "The translation quality is good")
        self.assertEqual(len(entry.review_comments), 2)
        self.assertEqual(entry.review_comments[1]["author"], "Test User")
        self.assertEqual(entry.review_comments[1]["comment"], "The translation quality is good")
        self.assertEqual(entry.review_comments[1]["id"], comment_id_en)

        # コメントの削除
        result = entry.remove_review_comment(comment_id_en)
        self.assertTrue(result)
        self.assertEqual(len(entry.review_comments), 1)

        # 存在しないIDで削除を試みると失敗することを確認
        result = entry.remove_review_comment("non-existent-id")
        self.assertFalse(result)

        # 全てのコメントをクリア
        entry.clear_review_comments()
        self.assertEqual(entry.review_comments, [])

    def test_metric_scores(self):
        """評価指標ごとのスコアのテスト"""
        entry = EntryModel(msgid="test", msgstr="テスト")

        # デフォルト値
        self.assertEqual(entry.metric_scores, {})

        # 指標スコアの追加
        entry.set_metric_score("accuracy", 90)
        entry.set_metric_score("fluency", 85)

        self.assertIn("accuracy", entry.metric_scores)
        self.assertIn("fluency", entry.metric_scores)
        self.assertEqual(entry.metric_scores["accuracy"], 90)
        self.assertEqual(entry.metric_scores["fluency"], 85)

        # スコアの更新
        entry.set_metric_score("accuracy", 95)
        self.assertEqual(entry.metric_scores["accuracy"], 95)

        # 不正なスコア値の設定
        with self.assertRaises(ValueError):
            entry.set_metric_score("consistency", -10)

        with self.assertRaises(ValueError):
            entry.set_metric_score("style", 110)

        # スコアの削除
        entry.remove_metric_score("fluency")
        self.assertNotIn("fluency", entry.metric_scores)

        # 存在しない指標スコアの削除
        entry.remove_metric_score("terminology")  # エラーにならず無視される

        # 全指標スコアの削除
        entry.clear_metric_scores()
        self.assertEqual(entry.metric_scores, {})

    def test_overall_score_calculation(self):
        """総合スコア計算のテスト"""
        entry = EntryModel(msgid="test", msgstr="テスト")

        # 指標スコアが空の場合
        self.assertIsNone(entry.score)

        # 指標スコアが存在する場合の自動計算
        entry.set_metric_score("accuracy", 90)
        entry.set_metric_score("fluency", 80)
        entry.set_metric_score("style", 85)

        # 自動計算された総合スコア (単純平均を想定)
        expected_score = (90 + 80 + 85) // 3
        self.assertEqual(entry.score, expected_score)

        # 総合スコアの手動設定
        entry.score = 88
        self.assertEqual(entry.score, 88)

        # 総合スコアを手動設定後、指標スコアを変更しても総合スコアは変わらない
        entry.set_metric_score("accuracy", 95)
        self.assertEqual(entry.score, 88)  # 手動設定したスコアが維持される

    def test_to_dict_with_evaluation(self):
        """辞書変換メソッドでの評価情報の取り扱いテスト"""
        entry = EntryModel(msgid="test", msgstr="テスト")

        # 評価情報を設定
        entry.score = 85
        entry.evaluation_state = EvaluationState.EVALUATED
        comment_id_ja = entry.add_review_comment("テスト太郎", "翻訳の品質は良好です")
        comment_id_en = entry.add_review_comment("Test User", "The translation quality is good")
        entry.set_metric_score("accuracy", 90)
        entry.set_metric_score("fluency", 80)

        # 辞書に変換
        entry_dict = entry.to_dict()

        # 評価関連の情報が正しく含まれているか確認
        self.assertEqual(entry_dict["score"], 85)
        self.assertEqual(entry_dict["evaluation_state"], EvaluationState.EVALUATED)
        
        # review_commentsがリスト形式であることを確認
        self.assertEqual(len(entry_dict["review_comments"]), 2)
        
        # 日本語のコメントを確認
        ja_comment = next((c for c in entry_dict["review_comments"] if c["author"] == "テスト太郎"), None)
        self.assertIsNotNone(ja_comment)
        self.assertEqual(ja_comment["comment"], "翻訳の品質は良好です")
        self.assertEqual(ja_comment["id"], comment_id_ja)
        
        # 英語のコメントを確認
        en_comment = next((c for c in entry_dict["review_comments"] if c["author"] == "Test User"), None)
        self.assertIsNotNone(en_comment)
        self.assertEqual(en_comment["comment"], "The translation quality is good")
        self.assertEqual(en_comment["id"], comment_id_en)
        
        # 指標スコアを確認
        self.assertEqual(entry_dict["metric_scores"]["accuracy"], 90)
        self.assertEqual(entry_dict["metric_scores"]["fluency"], 80)


if __name__ == "__main__":
    unittest.main()
