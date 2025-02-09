"""POEntryの型定義"""
from typing import List, Optional, Tuple, Protocol, runtime_checkable, Any, Sequence, Union, TypeVar, Generic, Iterator

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)


@runtime_checkable
class POEntry(Protocol):
    """POEntryのプロトコル定義"""

    msgid: str
    msgstr: str
    msgctxt: Optional[str]
    occurrences: List[Tuple[str, str]]
    flags: List[str]
    obsolete: bool
    comment: Optional[str]
    tcomment: Optional[str]
    previous_msgid: Optional[str]
    previous_msgid_plural: Optional[str]
    previous_msgctxt: Optional[str]

    def __getitem__(self, key: Union[str, int]) -> Any:
        """キーによる値の取得"""
        ...

    def __setitem__(self, key: Union[str, int], value: Any) -> None:
        """キーによる値の設定"""
        ...

    def __contains__(self, key: Union[str, int]) -> bool:
        """キーの存在確認"""
        ...

    def __iter__(self) -> Iterator[str]:
        """イテレータ"""
        ...

    def __len__(self) -> int:
        """長さ"""
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """キーによる値の取得（デフォルト値付き）"""
        ...

    def append(self, item: Any) -> None:
        """アイテムの追加"""
        ...

    def extend(self, items: Sequence[Any]) -> None:
        """アイテムの一括追加"""
        ...

    def remove(self, item: Any) -> None:
        """アイテムの削除"""
        ...

    def clear(self) -> None:
        """全アイテムの削除"""
        ...

    def copy(self) -> "POEntry":
        """エントリのコピー"""
        ...

    def save(self, path: Optional[str] = None) -> None:
        """エントリの保存"""
        ...

    @property
    def fuzzy(self) -> bool:
        """fuzzyフラグの状態を取得"""
        ... 