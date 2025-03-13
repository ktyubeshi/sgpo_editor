"""POエントリのモデル"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from polib import POEntry
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    computed_field,
    field_validator,
    model_validator,
)

from sgpo_editor.models.evaluation_state import EvaluationState

logger = logging.getLogger(__name__)


class EntryModel(BaseModel):
    """POエントリのPydanticモデル実装"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _po_entry: Optional[POEntry] = PrivateAttr(default=None)  # 元のPOEntryへの参照
    _score: Optional[int] = PrivateAttr(default=None)  # 総合スコア
    _evaluation_state: EvaluationState = PrivateAttr(
        default=EvaluationState.NOT_EVALUATED
    )  # 評価状態
    key: str = ""
    msgid: str = ""
    msgstr: str = ""
    msgctxt: Optional[str] = None
    obsolete: bool = False
    position: int = 0
    flags: List[str] = Field(default_factory=list)
    previous_msgid: Optional[str] = None
    previous_msgid_plural: Optional[str] = None
    previous_msgctxt: Optional[str] = None
    comment: Optional[str] = None
    tcomment: Optional[str] = None
    occurrences: List[tuple[str, int]] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)

    # 翻訳品質評価機能の拡張フィールド
    review_comments: List[Dict[str, str]] = Field(
        default_factory=list
    )  # 多言語レビューコメント
    metric_scores: Dict[str, int] = Field(default_factory=dict)  # 評価指標ごとのスコア
    check_results: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # 自動チェック結果
    category_quality_scores: Dict[str, int] = Field(
        default_factory=dict
    )  # カテゴリ別品質スコア
    _overall_quality_score: Optional[int] = PrivateAttr(default=None)  # 総合品質スコア

    # ユーザー定義メタデータ
    metadata: Dict[str, Any] = Field(
        default_factory=dict
    )  # 任意のメタデータを格納する辞書

    def __init__(self, **data):
        # evaluation_stateが渡された場合、初期化後に設定
        evaluation_state = data.pop("evaluation_state", EvaluationState.NOT_EVALUATED)
        super().__init__(**data)
        # キーが空の場合は生成する
        if not self.key:
            self.key = self._generate_key()
        # 評価状態を設定
        self._evaluation_state = evaluation_state

    @property
    def evaluation_state(self) -> EvaluationState:
        """評価状態を取得"""
        return self._evaluation_state

    @evaluation_state.setter
    def evaluation_state(self, value) -> None:
        """評価状態を設定
        Args:
            value: 設定する評価状態（EvaluationState型）
        Raises:
            TypeError: 評価状態がEvaluationState型でない場合
        """
        if not isinstance(value, EvaluationState):
            raise TypeError("evaluation_stateはEvaluationState型である必要があります")
        self._evaluation_state = value

    @computed_field
    @property
    def is_fuzzy(self) -> bool:
        """ファジーかどうか"""
        return "fuzzy" in self.flags

    @property
    def fuzzy(self) -> bool:
        """ファジーかどうか（互換性のため）"""
        return self.is_fuzzy

    @fuzzy.setter
    def fuzzy(self, value: bool) -> None:
        """ファジーフラグを設定"""
        if value and "fuzzy" not in self.flags:
            self.flags.append("fuzzy")
        elif not value and "fuzzy" in self.flags:
            self.flags.remove("fuzzy")

    @computed_field
    @property
    def is_translated(self) -> bool:
        """翻訳済みかどうか"""
        return bool(self.msgstr) and not self.is_fuzzy

    def translated(self) -> bool:
        """翻訳済みかどうか（互換性のため）"""
        return self.is_translated

    @computed_field
    @property
    def is_untranslated(self) -> bool:
        """未翻訳かどうか"""
        return not self.msgstr

    def get_status(self) -> str:
        """ステータスを取得"""
        # ステータスの優先順位: 廃止済み > ファジー > 未翻訳 > 翻訳済み
        if self.obsolete:
            return "廃止済み"
        elif self.is_fuzzy:
            return "要確認"
        elif self.is_untranslated:
            return "未翻訳"
        else:
            return "完了"

    @property
    def score(self) -> Optional[int]:
        """総合スコアを取得
        スコアが明示的に設定されていない場合は、指標スコアの平均値を返す

        Returns:
            Optional[int]: 総合スコア（0-100）または未設定の場合はNone
        """
        if self._score is not None:
            return self._score
        if not self.metric_scores:
            return None
        # 指標スコアの平均値を計算して返す
        return sum(self.metric_scores.values()) // len(self.metric_scores)

    @score.setter
    def score(self, value: Optional[int]) -> None:
        """総合スコアを設定
        Args:
            value: 設定するスコア値（0-100）またはNone

        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        if value is not None and (value < 0 or value > 100):
            raise ValueError("スコアは0から100の範囲で指定してください")
        self._score = value

    def add_review_comment(self, author: str, comment: str) -> None:
        """レビューコメントを追加

        Args:
            author: レビュー作成者
            comment: レビューコメント
        """
        from datetime import datetime

        self.review_comments.append(
            {
                "id": str(len(self.review_comments) + 1),
                "author": author,
                "comment": comment,
                "created_at": datetime.now().isoformat(),
            }
        )

    def remove_review_comment(self, comment_id: str) -> None:
        """特定のレビューコメントを削除

        Args:
            comment_id: 削除するコメントのID
        """
        self.review_comments = [
            c for c in self.review_comments if c["id"] != comment_id
        ]

    def clear_review_comments(self) -> None:
        """全てのレビューコメントをクリア"""
        self.review_comments.clear()

    def set_metric_score(self, metric_name: str, score: int) -> None:
        """評価指標のスコアを設定
        Args:
            metric_name: 評価指標名
            score: スコア値（0-100）

        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        if score < 0 or score > 100:
            raise ValueError("スコアは0から100の範囲で指定してください")
        self.metric_scores[metric_name] = score

    def remove_metric_score(self, metric_name: str) -> None:
        """評価指標のスコアを削除

        Args:
            metric_name: 評価指標名
        """
        if metric_name in self.metric_scores:
            del self.metric_scores[metric_name]

    def clear_metric_scores(self) -> None:
        """全ての評価指標スコアをクリア"""
        self.metric_scores.clear()
        self._score = None  # スコアもクリア

    def set_quality_score(self, score: int) -> None:
        """総合品質スコアを設定（後方互換性のため）
        Args:
            score: 設定するスコア値（0-100）

        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        self.set_overall_quality_score(score)

    def set_category_score(self, category: str, score: int) -> None:
        """カテゴリ別スコアを設定（後方互換性のため）
        
        Args:
            category: カテゴリ名
            score: スコア値（0-100）
            
        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        if score < 0 or score > 100:
            raise ValueError("スコアは0から100の範囲で指定してください")
        self.category_quality_scores[category] = score

    @property
    def overall_quality_score(self) -> Optional[int]:
        """総合品質スコアを取得"""
        return self._overall_quality_score

    def set_overall_quality_score(self, score: int) -> None:
        """総合品質スコアを設定

        Args:
            score: スコア値（0-100）

        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        if score < 0 or score > 100:
            raise ValueError("スコアは0から100の範囲で指定してください")
        self._overall_quality_score = score

    def reset_scores(self) -> None:
        """全てのスコアをリセット"""
        self._overall_quality_score = None
        self.category_quality_scores.clear()
        self.metric_scores.clear()
        self._score = None

    @model_validator(mode="before")
    @classmethod
    def validate_po_entry(cls, data: Any) -> Any:
        """POEntryからの変換"""
        if isinstance(data, dict):
            return data

        if not hasattr(data, "msgid"):
            return data

        po_entry = data

        # POEntryからの変換
        model_data = {
            "_po_entry": po_entry,
            "key": getattr(po_entry, "msgctxt", "") or "" + po_entry.msgid,
            "msgid": po_entry.msgid,
            "msgstr": po_entry.msgstr,
            "msgctxt": getattr(po_entry, "msgctxt", None),
            "obsolete": getattr(po_entry, "obsolete", False),
            "position": getattr(po_entry, "linenum", 0),
            "previous_msgid": getattr(po_entry, "previous_msgid", None),
            "previous_msgid_plural": getattr(po_entry, "previous_msgid_plural", None),
            "previous_msgctxt": getattr(po_entry, "previous_msgctxt", None),
            "comment": getattr(po_entry, "comment", None),
            "tcomment": getattr(po_entry, "tcomment", None),
            "occurrences": getattr(po_entry, "occurrences", []),
        }

        # flagsの変換
        flags = getattr(po_entry, "flags", [])
        if isinstance(flags, str):
            model_data["flags"] = [
                flag.strip() for flag in flags.split(",") if flag.strip()
            ]
        elif isinstance(flags, list):
            model_data["flags"] = flags
        else:
            model_data["flags"] = []

        return model_data

    @field_validator("flags", mode="before")
    @classmethod
    def validate_flags(cls, v: Any) -> List[str]:
        """flagsの変換"""
        if isinstance(v, str):
            return [flag.strip() for flag in v.split(",") if flag.strip()]
        elif isinstance(v, list):
            # ストリング化
            return [str(flag) for flag in v]
        return []

    def to_dict(self) -> Dict[str, Any]:
        """辞書化"""
        return {
            "key": self.key,
            "msgid": self.msgid,
            "msgstr": self.msgstr,
            "msgctxt": self.msgctxt,
            "obsolete": self.obsolete,
            "position": self.position,
            "flags": self.flags,
            "previous_msgid": self.previous_msgid,
            "previous_msgid_plural": self.previous_msgid_plural,
            "previous_msgctxt": self.previous_msgctxt,
            "comment": self.comment,
            "tcomment": self.tcomment,
            "occurrences": self.occurrences,
            "references": self.references,
            "score": self.score,
            "evaluation_state": self.evaluation_state,
            "review_comments": self.review_comments,
            "metric_scores": self.metric_scores,
            "check_results": self.check_results,
            "metadata": self.metadata,
            "overall_quality_score": self.overall_quality_score,
            "category_quality_scores": self.category_quality_scores,
        }

    def update_po_entry(self) -> None:
        """POEntryを更新"""
        if not self._po_entry:
            return

        self._po_entry.msgstr = self.msgstr

        # flagsの更新
        if isinstance(self._po_entry.flags, str):
            self._po_entry.flags = ", ".join(self.flags)
        else:
            self._po_entry.flags = self.flags

    def __eq__(self, other: object) -> bool:
        """等価性を判定"""
        if not isinstance(other, EntryModel):
            return False

        return self.position == other.position

    def _generate_key(self) -> str:
        """キーを生成"""
        if self.msgctxt:
            return f"{self.msgctxt}\x04{self.msgid}"
        else:
            return f"|{self.msgid}"

    @classmethod
    def from_po_entry(cls, po_entry: POEntry, position: int = 0) -> "EntryModel":
        """POEntryからインスタンスを生成"""
        msgctxt = getattr(po_entry, "msgctxt", None)
        key = ""
        if msgctxt:
            key = f"{msgctxt}\x04{po_entry.msgid}"
        else:
            key = f"|{po_entry.msgid}"

        # POEntryからの変換
        def safe_getattr(obj, attr_name, default=None):
            try:
                value = getattr(obj, attr_name, default)
                # Mockの場合、デフォルト値を返す
                if hasattr(value, "__class__") and "Mock" in value.__class__.__name__:
                    return default
                return value
            except (AttributeError, TypeError):
                return default

        # POEntryからの変換
        model = cls(
            key=key,
            msgid=po_entry.msgid,
            msgstr=po_entry.msgstr,
            msgctxt=msgctxt,
            obsolete=safe_getattr(po_entry, "obsolete", False),
            position=position,
            previous_msgid=safe_getattr(po_entry, "previous_msgid", None),
            previous_msgid_plural=safe_getattr(po_entry, "previous_msgid_plural", None),
            previous_msgctxt=safe_getattr(po_entry, "previous_msgctxt", None),
            comment=safe_getattr(po_entry, "comment", None),
            tcomment=safe_getattr(po_entry, "tcomment", None),
            occurrences=safe_getattr(po_entry, "occurrences", []),
        )

        # POEntryへの参照を設定
        model._po_entry = po_entry

        # flagsの変換
        flags = safe_getattr(po_entry, "flags", [])
        if isinstance(flags, str):
            model.flags = [flag.strip() for flag in flags.split(",") if flag.strip()]
        elif isinstance(flags, list):
            model.flags = flags
        else:
            model.flags = []

        # referencesの変換
        occurrences = safe_getattr(po_entry, "occurrences", [])
        for occ in occurrences:
            if isinstance(occ, tuple) and len(occ) == 2:
                model.references.append(f"{occ[0]}:{occ[1]}")

        return model

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntryModel":
        """辞書からインスタンスを生成"""
        # 拡張フィールドを処理
        review_comments = data.pop("review_comments", [])
        overall_quality_score = data.pop("overall_quality_score", None)
        category_quality_scores = data.pop("category_quality_scores", {})
        check_results = data.pop("check_results", [])

        # 基本モデルを作成
        model = cls(**data)

        # 拡張フィールドを設定
        if isinstance(review_comments, list):
            model.review_comments = review_comments

        if overall_quality_score is not None:
            model.set_overall_quality_score(overall_quality_score)

        if category_quality_scores:
            for category, score in category_quality_scores.items():
                model.set_category_score(category, score)

        if check_results:
            for result in check_results:
                if (
                    isinstance(result, dict)
                    and "code" in result
                    and "message" in result
                    and "severity" in result
                ):
                    model.add_check_result(
                        result["code"], result["message"], result["severity"]
                    )

        return model

    def add_flag(self, flag: str) -> None:
        """フラグを追加"""
        if flag not in self.flags:
            self.flags.append(flag)

    def remove_flag(self, flag: str) -> None:
        """フラグを削除"""
        if flag in self.flags:
            self.flags.remove(flag)

    # 自動チェック結果の追加
    def add_check_result(self, code: int, message: str, severity: str) -> None:
        """自動チェック結果を追加

        Args:
            code: チェックコード
            message: チェックメッセージ
            severity: 重大度（error, warning, info）
        """
        self.check_results.append(
            {
                "code": code,
                "message": message,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def remove_check_result(self, code: int) -> bool:
        """自動チェック結果を削除

        Args:
            code: チェックコード
        Returns:
            bool: 削除に成功した場合True
        """
        original_length = len(self.check_results)
        self.check_results = [r for r in self.check_results if r["code"] != code]
        return len(self.check_results) < original_length

    def clear_check_results(self) -> None:
        """自動チェック結果をクリア"""
        self.check_results = []

    # メタデータの追加
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加

        Args:
            key: メタデータキー
            value: メタデータ値
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """メタデータを取得

        Args:
            key: メタデータキー
            default: デフォルト値
        Returns:
            Any: メタデータ値またはデフォルト値
        """
        return self.metadata.get(key, default)

    def remove_metadata(self, key: str) -> bool:
        """メタデータを削除

        Args:
            key: メタデータキー
        Returns:
            bool: 削除に成功した場合True
        """
        if key in self.metadata:
            del self.metadata[key]
            return True
        return False

    def clear_metadata(self) -> None:
        """メタデータをクリア"""
        self.metadata.clear()

    def get_all_metadata(self) -> Dict[str, Any]:
        """全てのメタデータを取得"""
        return self.metadata.copy()

    @evaluation_state.setter
    def evaluation_state(self, value) -> None:
        """評価状態を設定
        Args:
            value: 設定する評価状態（EvaluationState型）
        Raises:
            TypeError: 評価状態がEvaluationState型でない場合
        """
        if not isinstance(value, EvaluationState):
            raise TypeError("evaluation_stateはEvaluationState型である必要があります")
        self._evaluation_state = value
