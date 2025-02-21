from typing import Optional, List, Union
from dataclasses import dataclass

@dataclass
class POEntry:
    """POファイルのエントリを表すクラス"""
    
    msgid: str
    """メッセージID"""
    
    msgstr: Union[str, List[str]] = ""
    """翻訳文字列。複数形の場合はリストになります"""
    
    msgid_plural: Optional[str] = None
    """複数形のメッセージID"""
    
    msgctxt: Optional[str] = None
    """メッセージコンテキスト"""
    
    comment: Optional[str] = None
    """翻訳者コメント"""
    
    tcomment: Optional[str] = None
    """技術的なコメント"""
    
    occurrences: List[tuple[str, Union[int, str]]] = None
    """出現位置のリスト (ファイル名, 行番号) のタプル"""
    
    flags: List[str] = None
    """フラグのリスト"""
    
    previous_msgctxt: Optional[str] = None
    """以前のメッセージコンテキスト"""
    
    previous_msgid: Optional[str] = None
    """以前のメッセージID"""
    
    previous_msgid_plural: Optional[str] = None
    """以前の複数形メッセージID"""
    
    linenum: Optional[int] = None
    """ファイル内の行番号""" 