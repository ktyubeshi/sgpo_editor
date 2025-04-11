"""統計情報のデータモデル"""

from typing import Dict, cast

from pydantic import BaseModel, ConfigDict, Field

from sgpo_editor.types import StatsDataDict


class StatsModel(BaseModel):
    """統計情報のデータモデル"""

    model_config = ConfigDict()

    total: int = Field(0, description="全エントリ数")
    translated: int = Field(0, description="翻訳済みエントリ数")
    untranslated: int = Field(0, description="未翻訳エントリ数")
    fuzzy: int = Field(0, description="ファジーエントリ数")
    progress: float = Field(0.0, description="翻訳の進捗率（%）")
    file_name: str = Field("", description="POファイル名")

    def __init__(self, **data: StatsDataDict):
        super().__init__(**cast(Dict[str, object], data))
        self.update_progress()

    def update_progress(self) -> None:
        """進捗率を更新（パーセント表示）"""
        if self.total > 0:
            self.progress = (self.translated / self.total) * 100
        else:
            self.progress = 0.0
