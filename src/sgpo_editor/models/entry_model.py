"""エントリモデル

このモジュールは、POファイルのエントリを表現するためのモデルを提供します。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Entry:
    """POファイルのエントリを表現するクラス"""
    key: str
    msgid: str
    msgstr: str = ""
    flags: List[str] = field(default_factory=list)
    position: int = 0
    obsolete: bool = False
    fuzzy: bool = False
    tcomment: Optional[str] = None
    comment: Optional[str] = None
    msgctxt: Optional[str] = None
    msgid_plural: Optional[str] = None
    msgstr_plural: Dict[int, str] = field(default_factory=dict)
    previous_msgid: Optional[str] = None
    previous_msgid_plural: Optional[str] = None
    previous_msgctxt: Optional[str] = None
    references: List[str] = field(default_factory=list)
    occurrences: List[tuple] = field(default_factory=list)
    linenum: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entry':
        """辞書からEntryオブジェクトを作成する"""
        # 必須フィールド
        key = data.get("key", "")
        msgid = data.get("msgid", "")
        
        # その他のフィールド
        entry = cls(
            key=key,
            msgid=msgid,
            msgstr=data.get("msgstr", ""),
            flags=data.get("flags", []),
            position=data.get("position", 0),
            obsolete=data.get("obsolete", False),
            fuzzy=data.get("fuzzy", False),
            tcomment=data.get("tcomment"),
            comment=data.get("comment"),
            msgctxt=data.get("msgctxt"),
            msgid_plural=data.get("msgid_plural"),
            previous_msgid=data.get("previous_msgid"),
            previous_msgid_plural=data.get("previous_msgid_plural"),
            previous_msgctxt=data.get("previous_msgctxt"),
            references=data.get("references", []),
            occurrences=data.get("occurrences", []),
            linenum=data.get("linenum")
        )
        
        # msgstr_pluralがある場合は設定
        if "msgstr_plural" in data:
            entry.msgstr_plural = data["msgstr_plural"]
            
        return entry
    
    def to_dict(self) -> Dict[str, Any]:
        """Entryオブジェクトを辞書に変換する"""
        result = {
            "key": self.key,
            "msgid": self.msgid,
            "msgstr": self.msgstr,
            "flags": self.flags,
            "position": self.position,
            "obsolete": self.obsolete,
            "fuzzy": self.fuzzy
        }
        
        # Noneでないフィールドのみ追加
        if self.tcomment is not None:
            result["tcomment"] = self.tcomment
        if self.comment is not None:
            result["comment"] = self.comment
        if self.msgctxt is not None:
            result["msgctxt"] = self.msgctxt
        if self.msgid_plural is not None:
            result["msgid_plural"] = self.msgid_plural
        if self.previous_msgid is not None:
            result["previous_msgid"] = self.previous_msgid
        if self.previous_msgid_plural is not None:
            result["previous_msgid_plural"] = self.previous_msgid_plural
        if self.previous_msgctxt is not None:
            result["previous_msgctxt"] = self.previous_msgctxt
        if self.references:
            result["references"] = self.references
        if self.occurrences:
            result["occurrences"] = self.occurrences
        if self.linenum is not None:
            result["linenum"] = self.linenum
        if self.msgstr_plural:
            result["msgstr_plural"] = self.msgstr_plural
            
        return result
    
    def __getitem__(self, key: str) -> Any:
        """辞書のような添え字アクセスをサポート（entry["key"]）"""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Entryオブジェクトに '{key}' キーがありません")
    
    def __contains__(self, key: str) -> bool:
        """in演算子をサポート（"key" in entry）"""
        return hasattr(self, key)
    
    def get(self, key: str, default: Any = None) -> Any:
        """辞書のようなgetメソッドをサポート"""
        if hasattr(self, key):
            return getattr(self, key)
        return default
