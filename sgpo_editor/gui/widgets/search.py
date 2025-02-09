"""検索とフィルタリング用ウィジェット"""
from typing import Callable, Optional
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from pydantic import BaseModel


class SearchCriteria(BaseModel):
    filter: str = "すべて"
    search_text: str = ""
    match_mode: str = "部分一致"


class SearchWidget(QWidget):
    """検索とフィルタリング用ウィジェット"""
    def __init__(
        self,
        on_filter_changed: Callable[[], None],
        on_search_changed: Callable[[], None],
        on_open_clicked: Callable[[], None],
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._on_filter_changed: Callable[[], None] = on_filter_changed
        self._on_search_changed: Callable[[], None] = on_search_changed
        self._on_open_clicked: Callable[[], None] = on_open_clicked
        
        # 検索用タイマー
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(500)  # 500ミリ秒のデバウンス時間
        self._search_timer.timeout.connect(self._on_search_changed)
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # POファイルを開くボタン
        open_button = QPushButton("POファイルを開く...")
        open_button.clicked.connect(self._on_open_clicked)
        layout.addWidget(open_button)
        
        # フィルタリング用のコンボボックス
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["すべて", "翻訳済み", "未翻訳", "ファジー"])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        layout.addWidget(self.filter_combo)
        
        # 検索用のテキストボックス
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("検索...")
        self.search_edit.textChanged.connect(self._start_search_timer)
        layout.addWidget(self.search_edit)

    def get_match_mode(self) -> str:
        """現在のマッチモードを取得する（UIにマッチモードのウィジェットがない場合は '部分一致' を返す）"""
        return "部分一致"

    def get_search_criteria(self) -> SearchCriteria:
        """現在の検索条件を SearchCriteria の形で返す"""
        return SearchCriteria(
            filter=self.filter_combo.currentText(),
            search_text=self.search_edit.text(),
            match_mode=self.get_match_mode()
        )

    def _start_search_timer(self) -> None:
        """検索タイマーを開始"""
        self._search_timer.start()

    def get_filter(self) -> str:
        """現在のフィルタを取得"""
        return self.filter_combo.currentText()

    def get_search_text(self) -> str:
        """現在の検索テキストを取得"""
        return self.search_edit.text()
