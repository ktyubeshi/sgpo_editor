"""フィルタリング用ウィジェット"""
from typing import Callable, Optional
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Qt, QTimer
from pydantic import BaseModel


class SearchCriteria(BaseModel):
    filter: str = "すべて"
    filter_keyword: str = ""
    match_mode: str = "部分一致"


class SearchWidget(QWidget):
    """フィルタリング用ウィジェット"""
    def __init__(
        self,
        on_filter_changed: Callable[[], None],
        on_search_changed: Callable[[], None],
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._on_filter_changed: Callable[[], None] = on_filter_changed
        self._on_search_changed: Callable[[], None] = on_search_changed
        
        # フィルタ用タイマー
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(100)  # 100ミリ秒のデバウンス時間
        self._search_timer.timeout.connect(self._on_criteria_changed)
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # POファイルを開くボタンを削除
        
        # フィルタリング用のラベルとコンボボックス
        layout.addWidget(QLabel("表示:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["すべて", "翻訳済み", "未翻訳", "ファジー"])
        self.filter_combo.currentTextChanged.connect(self._on_criteria_changed)
        layout.addWidget(self.filter_combo)
        
        # フィルタ用のラベルとテキストボックス
        layout.addWidget(QLabel("フィルタ:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("キーワードを入力...")
        self.search_edit.textChanged.connect(self._start_search_timer)
        layout.addWidget(self.search_edit)
        
        # クリアボタン
        clear_button = QPushButton("クリア")
        clear_button.clicked.connect(self._clear_filter)
        layout.addWidget(clear_button)

    def get_match_mode(self) -> str:
        """現在のマッチモードを取得する（UIにマッチモードのウィジェットがない場合は '部分一致' を返す）"""
        return "部分一致"

    def get_search_criteria(self) -> SearchCriteria:
        """現在のフィルタ条件を SearchCriteria の形で返す"""
        return SearchCriteria(
            filter=self.filter_combo.currentText(),
            filter_keyword=self.search_edit.text(),
            match_mode=self.get_match_mode()
        )

    def _start_search_timer(self) -> None:
        """フィルタタイマーを開始"""
        self._search_timer.start()

    def _on_criteria_changed(self) -> None:
        """フィルタ条件が変更されたときの処理"""
        self._on_filter_changed()

    def _clear_filter(self) -> None:
        """フィルタ条件をクリア"""
        self.search_edit.clear()
        self.filter_combo.setCurrentText("すべて")
        self._on_criteria_changed()

    def get_filter(self) -> str:
        """現在のフィルタを取得"""
        return self.filter_combo.currentText()

    def get_filter_keyword(self) -> str:
        """現在のフィルタキーワードを取得"""
        return self.search_edit.text()
