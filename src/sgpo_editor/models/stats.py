"""統計情報のデータモデル"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any


class StatsModel(BaseModel):
    """統計情報のデータモデル"""
    model_config = ConfigDict()
    
    total: int = Field(0, description="全エントリ数")
    translated: int = Field(0, description="翻訳済みエントリ数")
    untranslated: int = Field(0, description="未翻訳エントリ数")
    fuzzy: int = Field(0, description="ファジーエントリ数")
    progress: float = Field(0.0, description="翻訳の進捗率（%）")
    file_name: str = Field("", description="POファイル名")

    def __init__(self, **data: Dict[str, Any]):
        super().__init__(**data)
        self.update_progress()

    def update_progress(self) -> None:
        """進捗率を更新（パーセント表示）"""
        if self.total > 0:
            self.progress = (self.translated / self.total) * 100
        else:
            self.progress = 0.0
