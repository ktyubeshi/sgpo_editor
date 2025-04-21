"""型定義モジュール

このモジュールは、アプリケーション全体で使用される共通の型エイリアスを定義します。
複雑な型に分かりやすい名前を付けることで、コードの可読性と保守性を向上させます。
"""

from typing import (
    Any,
    Dict,
    List,
    TypeAlias,
    Union,
    Tuple,
    Callable,
    Optional,
    Literal,
    TypedDict,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from sgpo_editor.models.entry import EntryModel
    from sgpo_editor.core.constants import TranslationStatus


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
    id: Optional[int]


# POエントリの辞書表現
EntryDict: TypeAlias = EntryDictType

# POエントリの辞書のリスト
EntryDictList: TypeAlias = List[EntryDict]

# キーからEntryModelへのマッピング
if TYPE_CHECKING:
    EntryModelMap: TypeAlias = Dict[str, "EntryModel"]
    # EntryModelのリスト
    EntryModelList: TypeAlias = List["EntryModel"]
    # フィルタリング済みEntryModelのリスト
    FilteredEntriesList: TypeAlias = List["EntryModel"]
else:
    EntryModelMap: TypeAlias = Dict[str, Any]
    # EntryModelのリスト
    EntryModelList: TypeAlias = List[Any]
    # フィルタリング済みEntryModelのリスト
    FilteredEntriesList: TypeAlias = List[Any]


class FlagConditionsType(TypedDict, total=False):
    """フラグ条件を表す辞書の型定義"""

    fuzzy: bool
    obsolete: bool
    translated: bool
    untranslated: bool
    fuzzy_or_untranslated: bool
    msgstr_empty: bool
    msgstr_not_empty: bool
    fuzzy_or_msgstr_empty: bool
    include_flags: List[str]
    exclude_flags: List[str]
    only_fuzzy: bool
    obsolete_only: bool


# フラグ条件を表す辞書
FlagConditions: TypeAlias = FlagConditionsType

# 辞書またはEntryModelのいずれか
if TYPE_CHECKING:
    EntryInput: TypeAlias = Union[EntryDict, "EntryModel"]
else:
    EntryInput: TypeAlias = Union[EntryDict, Any]

# キーからエントリ（辞書またはEntryModel）へのマッピング
EntryInputMap: TypeAlias = Dict[str, EntryInput]

# メタデータ辞書
MetadataDict: TypeAlias = Dict[str, str]

# 評価指標スコアの辞書
MetricScores: TypeAlias = Dict[str, float]

# カテゴリ品質スコアの辞書
CategoryScores: TypeAlias = Dict[str, float]


class CheckResultType(TypedDict, total=False):
    """チェック結果の型定義"""

    code: Union[str, int]
    message: str
    severity: Literal["error", "warning", "info"]
    timestamp: str
    details: Optional[str]


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


class CacheEfficiencyType(TypedDict, total=False):
    """キャッシュ効率情報の型定義"""

    complete_entry_cache_size: int
    basic_info_cache_size: int
    filtered_entries_cache_size: int
    cache_enabled: bool
    force_filter_update: bool
    row_key_map_size: int


CacheEfficiency: TypeAlias = CacheEfficiencyType


class CacheStatsType(TypedDict):
    """キャッシュ統計情報の型定義"""

    hits: int
    misses: int
    hit_rate: float
    size: int


class CachePerformanceType(TypedDict):
    """キャッシュパフォーマンス指標の型定義"""

    complete_cache: CacheStatsType
    basic_cache: CacheStatsType
    filter_cache: CacheStatsType
    cache_enabled: bool
    force_filter_update: bool


CachePerformance: TypeAlias = CachePerformanceType


class StatsDataDict(TypedDict, total=False):
    """統計情報データの型定義"""

    total: Union[int, str]
    translated: Union[int, str]
    untranslated: Union[int, str]
    fuzzy: Union[int, str]
    progress: Union[float, str]
    file_name: str


class FilterConditionsType(TypedDict, total=False):
    """フィルタ条件の型定義"""

    search_text: Optional[str]
    search_fields: Optional[List[str]]
    sort_column: Optional[str]
    sort_order: Optional[str]
    flag_conditions: Optional[FlagConditions]
    translation_status: Optional[str]
    exact_match: Optional[bool]
    case_sensitive: Optional[bool]
    limit: Optional[int]
    offset: Optional[int]


FilterConditions: TypeAlias = FilterConditionsType


class StatsDict(TypedDict):
    """統計情報の辞書型定義"""

    total: Union[int, str]
    translated: Union[int, str]
    untranslated: Union[int, str]
    fuzzy: Union[int, str]
    progress: Union[float, str]
    file_name: str


MetadataValueType = Union[str, int, float, bool, List[Any], Dict[str, Any]]


class StatisticsInfoType(TypedDict, total=False):
    """POファイル統計情報の型定義"""

    total: int
    translated: int
    untranslated: int
    fuzzy: int
    obsolete: int
    percent_translated: float


StatisticsInfo: TypeAlias = StatisticsInfoType


class ReviewCommentType(TypedDict, total=False):
    """レビューコメントの型定義"""

    id: str
    author: str
    comment: str
    created_at: str
    language: Optional[str]


class ReviewDataDict(TypedDict, total=False):
    """レビューデータの型定義"""

    review_comments: List[Dict[str, Any]]
    quality_score: Optional[float]
    category_scores: Dict[str, float]
    check_results: List[Dict[str, Any]]


LLMResponseMetricScores: TypeAlias = Dict[str, float]
LLMResponseComments: TypeAlias = Dict[str, str]


class EvaluationResultType(TypedDict):
    """翻訳評価結果の型定義"""

    overall_score: int
    metric_scores: LLMResponseMetricScores
    comments: Optional[LLMResponseComments]
    raw_response: Optional[str]


EvaluationResult: TypeAlias = EvaluationResultType
