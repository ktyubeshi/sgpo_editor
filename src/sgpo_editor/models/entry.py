"""POエントリのモデル"""
import logging
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel, Field, computed_field, model_validator, field_validator, ConfigDict

from sgpo_editor.types.po_entry import POEntry

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
    
    @computed_field
    @property
    def is_fuzzy(self) -> bool:
        """ファジーかどうか"""
        return "fuzzy" in self.flags
    
    @computed_field
    @property
    def is_translated(self) -> bool:
        """翻訳済みかどうか"""
        return bool(self.msgstr) and not self.is_fuzzy
    
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
            return v
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
            "is_translated": self.is_translated,
            "is_untranslated": self.is_untranslated,
            "previous_msgid": self.previous_msgid,
            "previous_msgid_plural": self.previous_msgid_plural,
            "previous_msgctxt": self.previous_msgctxt,
            "comment": self.comment,
            "tcomment": self.tcomment,
            "occurrences": self.occurrences,
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
        """等価比較"""
        if not isinstance(other, EntryModel):
            return False
        
        return self.position == other.position
