"""型定義モジュール

このモジュールは、アプリケーション全体で使用される共通の型エイリアスを定義します。
複雑な型に分かりやすい名前を付けることで、コードの可読性と保守性を向上させます。
"""

from typing import Any, Dict, List, Optional, TypeAlias, Union

from sgpo_editor.models.entry import EntryModel

# POエントリの辞書表現
EntryDict: TypeAlias = Dict[str, Any]

# POエントリの辞書のリスト
EntryDictList: TypeAlias = List[EntryDict]

# キーからEntryModelへのマッピング
EntryModelMap: TypeAlias = Dict[str, EntryModel]

# EntryModelのリスト
EntryModelList: TypeAlias = List[EntryModel]

# フィルタリング済みEntryModelのリスト
FilteredEntriesList: TypeAlias = List[EntryModel]

# フラグ条件を表す辞書
FlagConditions: TypeAlias = Dict[str, Any]

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

# チェック結果の辞書
CheckResults: TypeAlias = Dict[str, Any]
