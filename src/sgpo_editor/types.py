"""型定義モジュール

このモジュールは、アプリケーション全体で使用される共通の型エイリアスを定義します。
複雑な型に分かりやすい名前を付けることで、コードの可読性と保守性を向上させます。
"""

from typing import Any, Dict, List, TypeAlias, Union, Tuple, Callable, Optional, Literal, TypedDict, Set

from sgpo_editor.models.entry import EntryModel

class EntryDictType(TypedDict, total=False):
    """POエントリの辞書表現の型定義"""
    key: str
    msgid: str
    msgstr: str
    msgctxt: Optional[str]
    obsolete: bool
    position: int
    flags: List[str]
    previous_msgid: Optional[str]
    previous_msgid_plural: Optional[str]
    previous_msgctxt: Optional[str]
    comment: Optional[str]
    tcomment: Optional[str]
    references: List[str]
    score: Optional[float]
    fuzzy: bool
    is_translated: bool
    is_untranslated: bool
    review_comments: List[Dict[str, str]]
    metric_scores: Dict[str, float]
    check_results: List[Dict[str, str]]
    metadata: Dict[str, str]
    overall_quality_score: Optional[float]
    category_quality_scores: Dict[str, float]

# POエントリの辞書表現
EntryDict: TypeAlias = EntryDictType

# POエントリの辞書のリスト
EntryDictList: TypeAlias = List[EntryDict]

# キーからEntryModelへのマッピング
EntryModelMap: TypeAlias = Dict[str, EntryModel]

# EntryModelのリスト
EntryModelList: TypeAlias = List[EntryModel]

# フィルタリング済みEntryModelのリスト
FilteredEntriesList: TypeAlias = List[EntryModel]

class FlagConditionsType(TypedDict, total=False):
    """フラグ条件を表す辞書の型定義"""
    fuzzy: bool
    obsolete: bool
    translated: bool
    untranslated: bool
    fuzzy_or_untranslated: bool

# フラグ条件を表す辞書
FlagConditions: TypeAlias = FlagConditionsType

# 辞書またはEntryModelのいずれか
EntryInput: TypeAlias = Union[EntryDict, EntryModel]

# キーからエントリ（辞書またはEntryModel）へのマッピング
EntryInputMap: TypeAlias = Dict[str, EntryInput]

# メタデータ辞書
MetadataDict: TypeAlias = Dict[str, str]

# 評価指標スコアの辞書
MetricScores: TypeAlias = Dict[str, float]

# カテゴリ品質スコアの辞書
CategoryScores: TypeAlias = Dict[str, float]

class CheckResultType(TypedDict):
    """チェック結果の型定義"""
    id: str
    type: str
    severity: Literal["error", "warning", "info"]
    message: str
    details: Optional[str]
    timestamp: str

CheckResults: TypeAlias = List[CheckResultType]

# ソートカラム名と順序のタプル
SortInfo: TypeAlias = Tuple[str, str]

class FilterSettingsType(TypedDict, total=False):
    """フィルタ設定の型定義"""
    search_text: Optional[str]
    translation_status: Optional[str]
    flag_conditions: FlagConditions
    sort_column: Optional[str]
    sort_order: Optional[str]
    keyword: Optional[str]
    limit: Optional[int]
    offset: Optional[int]

# フィルタ設定の辞書
FilterSettings: TypeAlias = FilterSettingsType

# イベントハンドラコールバック
EventCallback: TypeAlias = Callable[..., None]

class POEntryKwargsType(TypedDict, total=False):
    """POエントリ作成時の引数の型定義"""
    msgid: str
    msgstr: str
    msgctxt: Optional[str]
    flags: List[str]
    obsolete: bool
    comment: Optional[str]
    tcomment: Optional[str]
    occurrences: List[Union[str, tuple]]
    fuzzy: bool
    msgid_plural: Optional[str]
    msgstr_plural: Dict[int, str]
    previous_msgid: Optional[str]
    previous_msgid_plural: Optional[str]
    previous_msgctxt: Optional[str]

POEntryKwargs: TypeAlias = POEntryKwargsType
