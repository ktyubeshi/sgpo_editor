"""エントリ編集用ウィジェット"""
import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QFrame,
)
from PySide6.QtCore import Signal

from ..models.entry import EntryModel

logger = logging.getLogger(__name__)


class EditBox(QFrame):
    """編集ボックスウィジェット"""
    text_changed = Signal(str)

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # ラベル
        label = QLabel(title)
        layout.addWidget(label)
        
        # エディタ
        self.editor = QPlainTextEdit()
        self.editor.setFixedHeight(60)  # 4行分程度
        self.editor.textChanged.connect(
            lambda: self.text_changed.emit(self.editor.toPlainText())
        )
        layout.addWidget(self.editor)

    def setText(self, text: str) -> None:
        """テキストを設定"""
        self.editor.setPlainText(text)

    def text(self) -> str:
        """テキストを取得"""
        return self.editor.toPlainText()


class EntryEditorWidget(QWidget):
    """POエントリ編集用ウィジェット"""
    text_changed = Signal()
    apply_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_entry: Optional[EntryModel] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        layout = QVBoxLayout(self)
        
        # コンテキスト
        self.context_edit = EditBox("コンテキスト")
        layout.addWidget(self.context_edit)
        
        # 翻訳元
        self.msgid_edit = EditBox("翻訳元")
        layout.addWidget(self.msgid_edit)
        
        # 翻訳文
        self.msgstr_edit = EditBox("翻訳文")
        self.msgstr_edit.text_changed.connect(self.text_changed)
        layout.addWidget(self.msgstr_edit)
        
        # Applyボタン
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_clicked)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリの内容を表示"""
        self._current_entry = entry
        if entry is None:
            self.context_edit.setText("")
            self.msgid_edit.setText("")
            self.msgstr_edit.setText("")
            return

        self.context_edit.setText(str(entry.msgctxt or ""))
        self.msgid_edit.setText(entry.msgid)
        self.msgstr_edit.setText(entry.msgstr)
