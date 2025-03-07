"""POエントリのモデル"""
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field, computed_field, model_validator, field_validator, ConfigDict

from polib import POEntry

logger = logging.getLogger(__name__)


class EntryModel(BaseModel):
    """POエントリのPydanticモデル実装"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _po_entry: Optional[POEntry] = None  # 元のPOEntryへの参照

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
    
    # レビュー機能拡張フィールド
    review_comments: List[Dict[str, Any]] = Field(default_factory=list)
    overall_quality_score: Optional[int] = None
    category_quality_scores: Dict[str, int] = Field(default_factory=dict)
    check_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    def __init__(self, **data):
        super().__init__(**data)
        # キーが空の場合は生成する
        if not self.key:
            self.key = self._generate_key()
    
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
    
    @model_validator(mode="before")
    @classmethod
    def validate_po_entry(cls, data: Any) -> Any:
        """POEntryからの変換"""
        if isinstance(data, dict):
            return data
        
        if not hasattr(data, "msgid"):
            return data
        
        po_entry = data
        
        # POEntryからEntryModelへの変換
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
        
        # flagsの処理
        flags = getattr(po_entry, "flags", [])
        if isinstance(flags, str):
            model_data["flags"] = [flag.strip() for flag in flags.split(",") if flag.strip()]
        elif isinstance(flags, list):
            model_data["flags"] = flags
        else:
            model_data["flags"] = []
        
        return model_data
    
    @field_validator("flags", mode="before")
    @classmethod
    def validate_flags(cls, v: Any) -> List[str]:
        """flagsのバリデーション"""
        if isinstance(v, str):
            return [flag.strip() for flag in v.split(",") if flag.strip()]
        elif isinstance(v, list):
            # リスト内の各要素を文字列に変換
            return [str(flag) for flag in v]
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        return {
            "key": self.key,
            "msgid": self.msgid,
            "msgstr": self.msgstr,
            "msgctxt": self.msgctxt,
            "obsolete": self.obsolete,
            "position": self.position,
            "flags": self.flags,
            "is_fuzzy": self.is_fuzzy,
            "fuzzy": self.fuzzy,
            "is_translated": self.is_translated,
            "is_untranslated": self.is_untranslated,
            "previous_msgid": self.previous_msgid,
            "previous_msgid_plural": self.previous_msgid_plural,
            "previous_msgctxt": self.previous_msgctxt,
            "comment": self.comment,
            "tcomment": self.tcomment,
            "occurrences": self.occurrences,
            "references": self.references,
            # レビュー機能の拡張フィールド
            "review_comments": self.review_comments,
            "overall_quality_score": self.overall_quality_score,
            "category_quality_scores": self.category_quality_scores,
            "check_results": self.check_results,
        }
        
    def get_status(self) -> str:
        """エントリの状態を取得"""
        if self.is_fuzzy:
            return "要確認"
        elif self.is_translated:
            return "完了"
        else:
            return "未翻訳"
    
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
        """等価比較"""
        if not isinstance(other, EntryModel):
            return False
        
        return self.position == other.position
        
    def _generate_key(self) -> str:
        """キーを生成する"""
        if self.msgctxt:
            return f"{self.msgctxt}\x04{self.msgid}"
        else:
            return f"|{self.msgid}"
    
    @classmethod
    def from_po_entry(cls, po_entry: POEntry, position: int = 0) -> 'EntryModel':
        """POEntryからEntryModelを作成"""
        msgctxt = getattr(po_entry, "msgctxt", None)
        key = ""
        if msgctxt:
            key = f"{msgctxt}\x04{po_entry.msgid}"
        else:
            key = f"|{po_entry.msgid}"
            
        # 安全に属性を取得する関数
        def safe_getattr(obj, attr_name, default=None):
            try:
                value = getattr(obj, attr_name, default)
                # Mockオブジェクトの場合はデフォルト値を使用
                if hasattr(value, "__class__") and "Mock" in value.__class__.__name__:
                    return default
                return value
            except (AttributeError, TypeError):
                return default
        
        # POEntryの属性を安全に取得
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
            references=[]
        )
        
        # POEntryへの参照を保持
        model._po_entry = po_entry
        
        # flagsの処理
        flags = safe_getattr(po_entry, "flags", [])
        if isinstance(flags, str):
            model.flags = [flag.strip() for flag in flags.split(",") if flag.strip()]
        elif isinstance(flags, list):
            model.flags = flags
        else:
            model.flags = []
            
        # referencesの処理（occurrencesから生成）
        occurrences = safe_getattr(po_entry, "occurrences", [])
        for occ in occurrences:
            if isinstance(occ, tuple) and len(occ) == 2:
                model.references.append(f"{occ[0]}:{occ[1]}")
        
        return model
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntryModel':
        """辞書からEntryModelを作成"""
        return cls(**data)
    
    def add_flag(self, flag: str) -> None:
        """フラグを追加"""
        if flag not in self.flags:
            self.flags.append(flag)
    
    def remove_flag(self, flag: str) -> None:
        """フラグを削除"""
        if flag in self.flags:
            self.flags.remove(flag)
    
    # レビューコメント機能のメソッド
    def add_review_comment(self, comment: str, author: str) -> str:
        """レビューコメントを追加
        
        Args:
            comment: コメント内容
            author: コメント作成者
        
        Returns:
            str: コメントID
        """
        comment_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        self.review_comments.append({
            "id": comment_id,
            "author": author,
            "comment": comment,
            "created_at": timestamp,
        })
        
        return comment_id
    
    def remove_review_comment(self, comment_id: str) -> bool:
        """特定のレビューコメントを削除
        
        Args:
            comment_id: 削除するコメントのID
            
        Returns:
            bool: 削除に成功したかどうか
        """
        original_length = len(self.review_comments)
        self.review_comments = [c for c in self.review_comments if c["id"] != comment_id]
        return len(self.review_comments) < original_length
    
    def clear_review_comments(self) -> None:
        """すべてのレビューコメントをクリア"""
        self.review_comments = []
    
    # 評価スコア機能のメソッド
    def set_overall_quality_score(self, score: int) -> None:
        """翻訳品質の全体スコアを設定
        
        Args:
            score: 0-100の品質スコア
        """
        if not 0 <= score <= 100:
            raise ValueError("品質スコアは0から100の範囲で指定してください")
        self.overall_quality_score = score
    
    def set_category_score(self, category: str, score: int) -> None:
        """カテゴリ別の品質スコアを設定
        
        Args:
            category: スコアのカテゴリ (accuracy, fluency など)
            score: 0-100の品質スコア
        """
        if not 0 <= score <= 100:
            raise ValueError("品質スコアは0から100の範囲で指定してください")
        self.category_quality_scores[category] = score
    
    def clear_quality_scores(self) -> None:
        """品質スコアをクリア"""
        self.overall_quality_score = None
        self.category_quality_scores = {}
    
    def reset_scores(self) -> None:
        """すべての品質スコアをリセット"""
        self.clear_quality_scores()
    
    # 自動チェック結果の管理メソッド
    def add_check_result(self, code: int, message: str, severity: str) -> None:
        """自動チェック結果を追加
        
        Args:
            code: チェックルールのエラーコード
            message: エラーメッセージ
            severity: 重要度 (error, warning, info など)
        """
        self.check_results.append({
            "code": code,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        })
    
    def remove_check_result(self, code: int) -> bool:
        """特定のコードのチェック結果を削除
        
        Args:
            code: 削除するチェック結果のコード
            
        Returns:
            bool: 削除に成功したかどうか
        """
        original_length = len(self.check_results)
        self.check_results = [r for r in self.check_results if r["code"] != code]
        return len(self.check_results) < original_length
    
    def clear_check_results(self) -> None:
        """すべてのチェック結果をクリア"""
        self.check_results = []
