"""評価状態の列挙型のテスト"""

import unittest
from sgpo_editor.models.evaluation_state import EvaluationState


class TestEvaluationState(unittest.TestCase):
    """評価状態の列挙型のテストケース"""

    def test_evaluation_states(self):
        """列挙型の値を検証"""
        # 列挙型の値が期待通りに定義されていることを確認
        self.assertIsNotNone(EvaluationState.NOT_EVALUATED)
        self.assertIsNotNone(EvaluationState.EVALUATING)
        self.assertIsNotNone(EvaluationState.EVALUATED)
        # 値が重複していないことを確認
        self.assertNotEqual(
            EvaluationState.NOT_EVALUATED.value, EvaluationState.EVALUATING.value
        )
        self.assertNotEqual(
            EvaluationState.EVALUATING.value, EvaluationState.EVALUATED.value
        )
        self.assertNotEqual(
            EvaluationState.NOT_EVALUATED.value, EvaluationState.EVALUATED.value
        )

    def test_string_representation(self):
        """文字列表現のテスト"""
        self.assertEqual(str(EvaluationState.NOT_EVALUATED), "未評価")
        self.assertEqual(str(EvaluationState.EVALUATING), "評価中")
        self.assertEqual(str(EvaluationState.EVALUATED), "評価済み")


if __name__ == "__main__":
    unittest.main()
