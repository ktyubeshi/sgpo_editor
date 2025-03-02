"""統計情報表示用ウィジェット"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

from sgpo_editor.models import StatsModel


class StatsWidget(QWidget):
    """統計情報表示用ウィジェット"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # 統計情報ラベル
        self.total_label = QLabel()
        self.translated_label = QLabel()
        self.untranslated_label = QLabel()
        self.fuzzy_label = QLabel()
        self.progress_label = QLabel()
        
        layout.addWidget(self.total_label)
        layout.addWidget(self.translated_label)
        layout.addWidget(self.untranslated_label)
        layout.addWidget(self.fuzzy_label)
        layout.addWidget(self.progress_label)
        
        # 下部にスペースを追加
        layout.addStretch()

    def update_stats(self, stats: StatsModel) -> None:
        """統計情報を更新"""
        self.total_label.setText(f"全エントリ数: {stats.total}")
        self.translated_label.setText(f"翻訳済み: {stats.translated}")
        self.untranslated_label.setText(f"未翻訳: {stats.untranslated}")
        self.fuzzy_label.setText(f"ファジー: {stats.fuzzy}")
        self.progress_label.setText(f"進捗率: {stats.progress:.1f}%")
