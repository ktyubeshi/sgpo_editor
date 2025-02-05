from __future__ import annotations

from typing import List, Optional

import polib
from pydantic import BaseModel, ConfigDict, Field


class DuplicateEntry(BaseModel):
    """重複エントリの情報を保持するクラス"""

    model_config = ConfigDict(frozen=True)  # イミュータブルに設定

    line1: Optional[int] = Field(None, description="1つ目のエントリの行番号")
    line2: Optional[int] = Field(None, description="2つ目のエントリの行番号")
    msgid: str = Field(
        ...,  # 必須フィールド
        description="重複しているmsgid",
    )
    msgctxt1: str = Field(
        ...,  # 必須フィールド
        description="1つ目のエントリのmsgctxt",
    )
    msgctxt2: str = Field(
        ...,  # 必須フィールド
        description="2つ目のエントリのmsgctxt",
    )


def check_msgctxt_duplicates(po_file: polib.POFile) -> List[DuplicateEntry]:
    """
    SmartGitの圧縮表記を考慮して重複エントリをチェックする

    Args:
        po_file: チェック対象のPOファイル

    Returns:
        重複エントリのリスト
    """
    duplicates: List[DuplicateEntry] = []
    for i, entry1 in enumerate(po_file):
        for j, entry2 in enumerate(po_file):
            if i >= j:  # 同じエントリ同士や、既にチェック済みの組み合わせはスキップ
                continue
            if entry1.msgid == entry2.msgid:  # msgidが同じ場合のみチェック
                if _has_msgctxt_overlap(entry1.msgctxt, entry2.msgctxt):
                    duplicates.append(
                        DuplicateEntry(
                            line1=entry1.linenum,
                            line2=entry2.linenum,
                            msgid=entry1.msgid,
                            msgctxt1=entry1.msgctxt,
                            msgctxt2=entry2.msgctxt,
                        )
                    )
    return duplicates


def _has_msgctxt_overlap(msgctxt1: str, msgctxt2: str) -> bool:
    """
    2つのmsgctxtが重複するかチェックする
    SmartGitの圧縮表記を展開して比較する

    Args:
        msgctxt1: 比較対象の1つ目のmsgctxt
        msgctxt2: 比較対象の2つ目のmsgctxt

    Returns:
        重複する場合はTrue、しない場合はFalse
    """
    expanded1 = _expand_msgctxt(msgctxt1)
    expanded2 = _expand_msgctxt(msgctxt2)
    return bool(set(expanded1) & set(expanded2))


def _expand_msgctxt(msgctxt: str) -> List[str]:
    """
    SmartGitの圧縮表記を展開する

    Args:
        msgctxt: 展開対象のmsgctxt

    Returns:
        展開後のmsgctxtのリスト
    """
    # 圧縮表記がない場合は元の文字列をリストで返す
    if "(" not in msgctxt:
        return [msgctxt]

    # 圧縮表記を展開
    prefix = msgctxt[: msgctxt.find("(")]
    compressed = msgctxt[msgctxt.find("(") + 1 : msgctxt.find(")")]
    suffix = msgctxt[msgctxt.find(")") + 1 :]

    # | で区切られた部分を展開
    parts = [part for part in compressed.split("|") if part]
    return [f"{prefix}{part}{suffix}" for part in parts]
