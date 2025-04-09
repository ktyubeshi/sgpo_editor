"""翻訳評価状態の列挙型定義"""

from enum import Enum, auto


class EvaluationState(Enum):
    """翻訳評価の状態を示す列挙型

    - NOT_EVALUATED: 未評価
    - EVALUATING: 評価中
    - EVALUATED: 評価済み
    """

    NOT_EVALUATED = auto()  # 未評価
    EVALUATING = auto()  # 評価中
    EVALUATED = auto()  # 評価済み

    def __str__(self) -> str:
        """文字列表現を取得"""
        return {
            EvaluationState.NOT_EVALUATED: "未評価",
            EvaluationState.EVALUATING: "評価中",
            EvaluationState.EVALUATED: "評価済み",
        }[self]
