"""POエントリのモデル"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from sgpo_editor.types import EntryDict

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
from sgpo_editor.utils.metadata_utils import (
    extract_metadata_from_comment,
    create_comment_with_metadata,
)
from sgpo_editor.core.constants import TranslationStatus

logger = logging.getLogger(__name__)


class EntryModel(BaseModel):
    """POエントリのPydanticモデル実装"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _po_entry: Optional[POEntry] = PrivateAttr(default=None)  # 元のPOEntryへの参照
    _score: Optional[float] = PrivateAttr(default=None)  # 総合スコア
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
    category_quality_scores: Dict[str, float] = Field(
        default_factory=dict
    )  # カテゴリ別品質スコア
    _overall_quality_score: Optional[float] = PrivateAttr(default=None)  # 総合品質スコア

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

    @property
    def fuzzy(self) -> bool:
        """ファジーかどうか"""
        return "fuzzy" in self.flags

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
        return bool(self.msgstr) and not self.fuzzy

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
            return TranslationStatus.OBSOLETE
        elif self.fuzzy:
            return TranslationStatus.FUZZY
        elif self.is_untranslated:
            return TranslationStatus.UNTRANSLATED
        else:
            return TranslationStatus.TRANSLATED

    @property
    def score(self) -> Optional[float]:
        """総合スコアを取得
        スコアが明示的に設定されていない場合は、以下の優先順位で値を返す
        1. 明示的に設定されたスコア (_score)
        2. LLM評価による総合スコア (overall_quality_score)
        3. 指標スコアの平均値
        4. None (スコアなし)

        Returns:
            Optional[float]: 総合スコア（0-100）または未設定の場合はNone
        """
        # 明示的に設定されたスコアがある場合はそれを返す
        if self._score is not None:
            return self._score

        # LLM評価による総合スコアがある場合はそれを返す
        if self.overall_quality_score is not None:
            return self.overall_quality_score

        # 指標スコアがある場合はその平均値を返す
        if self.metric_scores:
            return sum(self.metric_scores.values()) / len(self.metric_scores)

        # スコアがない場合はNoneを返す
        return None

    @score.setter
    def score(self, value: Optional[float]) -> None:
        """総合スコアを設定

        Args:
            value: 設定するスコア値（0-100）またはNone

        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        if value is not None and (value < 0 or value > 100):
            raise ValueError("スコアは0から100の範囲で指定してください")
        self._score = value

    def add_review_comment(self, author: str, comment: str) -> str:
        """レビューコメントを追加

        Args:
            author: レビュー作成者
            comment: レビューコメント

        Returns:
            str: 生成されたコメントID
        """
        from datetime import datetime

        comment_id = str(len(self.review_comments) + 1)
        self.review_comments.append(
            {
                "id": comment_id,
                "author": author,
                "comment": comment,
                "created_at": datetime.now().isoformat(),
            }
        )
        return comment_id

    def remove_review_comment(self, comment_id: str) -> bool:
        """特定のレビューコメントを削除

        Args:
            comment_id: 削除するコメントのID

        Returns:
            bool: 削除が成功した場合はTrue、失敗した場合はFalse
        """
        original_length = len(self.review_comments)
        self.review_comments = [
            c for c in self.review_comments if c["id"] != comment_id
        ]
        return len(self.review_comments) < original_length

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

    def set_category_score(self, category: str, score: float) -> None:
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
    def overall_quality_score(self) -> Optional[float]:
        """総合品質スコアを取得"""
        return self._overall_quality_score

    @overall_quality_score.setter
    def overall_quality_score(self, score: Optional[float]) -> None:
        """総合品質スコアを設定

        Args:
            score: スコア値（0-100）またはNone

        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        self.set_overall_quality_score(score)

    def set_overall_quality_score(self, score: Optional[float]) -> None:
        """総合品質スコアを設定

        Args:
            score: スコア値（0-100）

        Raises:
            ValueError: スコアが0-100の範囲外の場合
        """
        if score is not None and (score < 0 or score > 100):
            raise ValueError("スコアは0から100の範囲で指定してください")
        self._overall_quality_score = score

    def clear_quality_scores(self) -> None:
        """品質スコアをクリア
        総合品質スコアとカテゴリ別品質スコアをクリアします。
        """
        self._overall_quality_score = None
        self.category_quality_scores.clear()

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

        # commentからメタデータを抽出
        if model_data["comment"]:
            metadata = extract_metadata_from_comment(model_data["comment"])
            if metadata:
                model_data["metadata"] = metadata

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
        result = {
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
            "fuzzy": self.fuzzy,  # fuzzyフラグを追加
            "is_translated": self.is_translated,  # 翻訳状態を追加
            "is_untranslated": self.is_untranslated,  # 未翻訳状態を追加
        }

        return result

    def update_po_entry(self) -> None:
        """POEntryを更新"""
        if not self._po_entry:
            return

        self._po_entry.msgstr = self.msgstr

        # flagsの更新
        try:
            if isinstance(self._po_entry.flags, str):
                self._po_entry.flags = ", ".join(self.flags)
            else:
                setattr(self._po_entry, "flags", self.flags)
        except (AttributeError, TypeError):
            logger.warning("POEntryのflagsを更新できませんでした。読み取り専用の可能性があります。")

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
        if occurrences is not None:
            for occ in occurrences:
                if isinstance(occ, tuple) and len(occ) == 2:
                    model.references.append(f"{occ[0]}:{occ[1]}")

        # コメントからメタデータを抽出
        comment = safe_getattr(po_entry, "comment", None)
        if comment:
            metadata = extract_metadata_from_comment(comment)
            if metadata:
                # 抽出したメタデータをモデルに設定
                for key, value in metadata.items():
                    model.add_metadata(key, value)

        return model

    @classmethod
    def from_dict(cls, data: "EntryDict") -> "EntryModel":
        """辞書からインスタンスを生成"""
        # 拡張フィールドを処理
        review_comments = data.pop("review_comments", [])
        overall_quality_score = data.pop("overall_quality_score", None)
        category_quality_scores = data.pop("category_quality_scores", {})
        check_results = data.pop("check_results", [])

        # flagsフィールドの処理
        flags = data.get("flags", [])
        if isinstance(flags, str):
            # カンマ区切りの文字列の場合はリストに変換
            data["flags"] = [flag.strip() for flag in flags.split(",") if flag.strip()]
        elif not isinstance(flags, list):
            # リストでない場合は空リストにする
            data["flags"] = []

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
    def add_check_result(self, code: Union[str, int], message: str, severity: str) -> None:
        """自動チェック結果を追加

        Args:
            code: チェックコード（文字列または整数）
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

    def to_po_entry(self) -> POEntry:
        """EntryModelをPOEntryオブジェクトに変換する

        Returns:
            POEntry: 変換されたPOEntryオブジェクト
        """
        if self._po_entry:
            # POEntry参照があればそれを更新して返す
            po_entry = self._po_entry

            # 基本フィールドを更新
            po_entry.msgid = self.msgid
            po_entry.msgstr = self.msgstr
            po_entry.obsolete = self.obsolete
            po_entry.flags = self.flags

            # メタデータをコメントに保存
            if self.metadata:
                # 既存のコメントとメタデータを結合
                combined_comment = create_comment_with_metadata(
                    po_entry.comment, self.metadata
                )
                po_entry.comment = combined_comment

            return po_entry

        # 新しいPOEntryを作成
        kwargs = {
            "msgid": self.msgid,
            "msgstr": self.msgstr,
            "obsolete": self.obsolete,
            "flags": self.flags,
        }

        # オプションフィールドを追加
        if self.msgctxt:
            kwargs["msgctxt"] = self.msgctxt
        if self.previous_msgid:
            kwargs["previous_msgid"] = self.previous_msgid
        if self.previous_msgid_plural:
            kwargs["previous_msgid_plural"] = self.previous_msgid_plural
        if self.previous_msgctxt:
            kwargs["previous_msgctxt"] = self.previous_msgctxt

        # メタデータがある場合はコメントに保存
        if self.metadata:
            combined_comment = create_comment_with_metadata(self.comment, self.metadata)
            kwargs["comment"] = combined_comment
        elif self.comment:
            kwargs["comment"] = self.comment

        if self.tcomment:
            kwargs["tcomment"] = self.tcomment
        if self.occurrences:
            kwargs["occurrences"] = self.occurrences

        # 新しいPOEntryを返す
        return POEntry(**kwargs)

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

    def __getitem__(self, key: str) -> Any:
        """辞書アクセスをサポートするためのメソッド

        テスト互換性のために、EntryModelオブジェクトを辞書のように扱えるようにする

        Args:
            key: アクセスするキー

        Returns:
            キーに対応する値

        Raises:
            KeyError: キーが存在しない場合
        """
        if hasattr(self, key):
            return getattr(self, key)
            
        if key == "fuzzy":
            return self.fuzzy
        elif key == "is_translated":
            return self.is_translated
        elif key == "is_untranslated":
            return self.is_untranslated
        elif key == "score":
            return self.score
        elif key == "overall_quality_score":
            return self.overall_quality_score
        elif key == "evaluation_state":
            return self.evaluation_state
            
        dict_result = self.to_dict()
        if key in dict_result:
            return dict_result[key]
            
        raise KeyError(f"キー '{key}' は存在しません")

    def __contains__(self, key: str) -> bool:
        """キーが存在するかどうかを確認するためのメソッド

        Args:
            key: 確認するキー

        Returns:
            キーが存在する場合はTrue、そうでない場合はFalse
        """
        if hasattr(self, key):
            return True
            
        if key in [
            "fuzzy", 
            "is_translated", 
            "is_untranslated", 
            "score", 
            "overall_quality_score", 
            "evaluation_state"
        ]:
            return True
            
        return key in self.to_dict()
