"""POエントリのデータモデル"""
from typing import Optional, List
from pydantic import BaseModel, Field, computed_field


class EntryModel(BaseModel):
    """POエントリのデータモデル"""
    msgid: str = Field(..., description="翻訳元のテキスト")
    msgstr: str = Field("", description="翻訳後のテキスト")
    msgctxt: Optional[str] = Field(None, description="コンテキスト")
    fuzzy: bool = Field(False, description="ファジーフラグ")
    obsolete: bool = Field(False, description="廃止フラグ")
    previous_msgid: Optional[str] = Field(None, description="以前の翻訳元テキスト")
    previous_msgstr: Optional[str] = Field(None, description="以前の翻訳後テキスト")
    references: List[str] = Field(default_factory=list, description="参照情報")
    comment: Optional[str] = Field(None, description="コメント")
    tcomment: Optional[str] = Field(None, description="翻訳者コメント")

    @computed_field
    @property
    def key(self) -> str:
        """エントリの一意キーを取得"""
        return f"{self.msgctxt or ''}|{self.msgid}"

    def translated(self) -> bool:
        """翻訳済みかどうかを返す"""
        return bool(self.msgstr)

    def is_fuzzy(self) -> bool:
        """ファジーかどうかを返す"""
        return self.fuzzy

    def get_status(self) -> str:
        """エントリの状態を返す"""
        if self.is_fuzzy():
            return "ファジー"
        return "翻訳済み" if self.translated() else "未翻訳"

    @classmethod
    def from_po_entry(cls, entry) -> "EntryModel":
        """POエントリからEntryModelを作成する

        Args:
            entry: POエントリ

        Returns:
            EntryModel: 作成されたモデル
        """
        return cls(
            msgid=str(entry.msgid),
            msgstr=str(entry.msgstr),
            msgctxt=str(entry.msgctxt) if entry.msgctxt else None,
            fuzzy="fuzzy" in entry.flags,
            obsolete=entry.obsolete,
            previous_msgid=str(entry.previous_msgid) if hasattr(entry, "previous_msgid") else None,
            previous_msgstr=str(entry.previous_msgstr) if hasattr(entry, "previous_msgstr") else None,
            references=getattr(entry, "references", []),
            comment=str(entry.comment) if entry.comment else None,
            tcomment=str(entry.tcomment) if entry.tcomment else None
        )
