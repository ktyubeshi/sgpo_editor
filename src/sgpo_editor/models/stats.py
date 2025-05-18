"""統計情報のデータモデル"""

from typing import Any, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StatsModel(BaseModel):
    """統計情報のデータモデル"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    total: int = Field(0, description="全エントリ数")
    translated: int = Field(0, description="翻訳済みエントリ数")
    untranslated: int = Field(0, description="未翻訳エントリ数")
    fuzzy: int = Field(0, description="ファジーエントリ数")
    progress: float = Field(0.0, description="翻訳の進捗率（%）")
    file_name: str = Field("", description="POファイル名")

    @field_validator("total", "translated", "untranslated", "fuzzy", mode="before")
    @classmethod
    def validate_int_fields(cls, v: Union[int, str, Any]) -> int:
        """整数フィールドのバリデーション"""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v)
            except (ValueError, TypeError):
                return 0
        return 0

    @field_validator("progress", mode="before")
    @classmethod
    def validate_float_fields(cls, v: Union[float, int, str, Any]) -> float:
        """浮動小数点フィールドのバリデーション"""
        if isinstance(v, float):
            return v
        if isinstance(v, (int, str)):
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0
        return 0.0

    @field_validator("file_name", mode="before")
    @classmethod
    def validate_str_fields(cls, v: Any) -> str:
        """文字列フィールドのバリデーション"""
        if v is None:
            return ""
        return str(v)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        self.update_progress()

    def __getitem__(self, key: str) -> object:
        """辞書形式でのアクセスをサポート"""
        return getattr(self, key)

    def update_progress(self) -> None:
        """進捗率を更新（パーセント表示）"""
        if self.total > 0:
            self.progress = (self.translated / self.total) * 100
        else:
            self.progress = 0.0
