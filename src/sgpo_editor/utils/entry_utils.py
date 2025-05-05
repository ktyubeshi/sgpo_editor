"""
Entryユーティリティ関数群
- dict/EntryModel/POEntryなど、エントリ型の違いを吸収してアクセスする
"""
from typing import Any

def get_entry_key(entry: Any) -> str:
    """
    エントリ（dict, EntryModel, POEntry等）からキーを取得する
    Args:
        entry: エントリ（dictまたは属性アクセス可能なオブジェクト）
    Returns:
        str: エントリのキー
    Raises:
        AttributeError, KeyError: キーが取得できない場合
    """
    if isinstance(entry, dict):
        return entry["key"]
    if hasattr(entry, "key"):
        return getattr(entry, "key")
    raise AttributeError("entryに'key'属性が存在しません")
