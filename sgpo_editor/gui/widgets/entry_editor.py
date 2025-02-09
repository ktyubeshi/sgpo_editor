"""エントリ編集用ウィジェット"""

import logging
from typing import Optional, cast
from enum import Enum, auto

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QFrame,
    QComboBox,
    QSizePolicy,
    QCheckBox,
)
from PySide6.QtCore import Signal, Qt

from ..models.entry import EntryModel

logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """レイアウトタイプ"""

    LAYOUT1 = auto()  # msgctxt上部、msgid/msgstr下部横並び
    LAYOUT2 = auto()  # 前のレイアウト（左右分割）


class EditBox(QWidget):
    """編集ボックス"""

    text_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._placeholder = ""
        self._current_entry = None

        # エディタの設定
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(self._placeholder)
        self.editor.textChanged.connect(self._on_text_changed)

        # レイアウトの設定
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def _on_text_changed(self) -> None:
        """テキストが変更されたときの処理"""
        current_text = self.editor.toPlainText()
        self.text_changed.emit(current_text)

    def setText(self, text: str) -> None:
        """テキストを設定"""
        self.editor.setPlainText(text)

    def text(self) -> str:
        """テキストを取得"""
        return self.editor.toPlainText()


class EntryEditor(QWidget):
    """POエントリ編集用ウィジェット"""

    text_changed = Signal()
    apply_clicked = Signal()
    entry_changed = Signal(int)  # エントリが変更されたときのシグナル

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry = None

        # メインレイアウト
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # エディタウィジェット
        editor_widget = QWidget()
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)

        # コンテキスト
        self.context_edit = EditBox(self)
        self.context_edit.text_changed.connect(self._on_text_changed)
        editor_layout.addWidget(self.context_edit)

        # msgid
        self.msgid_edit = QPlainTextEdit(self)
        self.msgid_edit.setReadOnly(True)
        editor_layout.addWidget(self.msgid_edit)

        # msgstr
        self.msgstr_edit = QPlainTextEdit(self)
        self.msgstr_edit.textChanged.connect(self._on_text_changed)
        editor_layout.addWidget(self.msgstr_edit)

        # fuzzyチェックボックス
        self.fuzzy_checkbox = QCheckBox("Fuzzy", self)
        self.fuzzy_checkbox.stateChanged.connect(self._on_fuzzy_changed)
        editor_layout.addWidget(self.fuzzy_checkbox)

        editor_widget.setLayout(editor_layout)
        main_layout.addWidget(editor_widget)
        self.setLayout(main_layout)
        self.setEnabled(False)  # 初期状態では無効化

    @property
    def current_entry(self) -> Optional[EntryModel]:
        """現在のエントリを取得"""
        return self._current_entry

    @property
    def current_entry_number(self) -> Optional[int]:
        """現在のエントリ番号を取得"""
        if not self._current_entry:
            return None

        # MainWindowを取得
        main_window = self.parent()
        while main_window and not hasattr(main_window, "_display_entries"):
            main_window = main_window.parent()

        if not main_window or not hasattr(main_window, "_display_entries"):
            return None

        # 現在のエントリのインデックスを取得
        try:
            entries = getattr(main_window, "_display_entries", [])
            if not entries:
                return None
            return entries.index(self._current_entry.key)
        except (ValueError, AttributeError):
            return None

    def _on_apply_clicked(self) -> None:
        """適用ボタンクリック時の処理"""
        if not self.current_entry:
            return

        # エントリを更新
        entry = self.current_entry
        entry.msgstr = self.msgstr_edit.toPlainText()
        entry.fuzzy = self.fuzzy_checkbox.isChecked()
        self.text_changed.emit()

    def _on_text_changed(self) -> None:
        """テキストが変更されたときの処理"""
        if not self._current_entry:
            return

        # エントリを更新
        if self.msgstr_edit:
            self._current_entry.msgstr = self.msgstr_edit.toPlainText()
        if self.context_edit:
            self._current_entry.msgctxt = self.context_edit.text() or None

        self.text_changed.emit()

    def _on_fuzzy_changed(self, state: int) -> None:
        """Fuzzyチェックボックスの状態が変更されたときの処理"""
        if self.fuzzy_checkbox:
            self.fuzzy_checkbox.setChecked(state == Qt.CheckState.Checked)
            self.text_changed.emit()

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定"""
        self._current_entry = entry
        if entry is None:
            if self.msgid_edit:
                self.msgid_edit.setPlainText("")
            if self.msgstr_edit:
                self.msgstr_edit.setPlainText("")
            if self.fuzzy_checkbox:
                self.fuzzy_checkbox.setChecked(False)
            if self.context_edit:
                self.context_edit.setText("")
            self.setEnabled(False)
            return

        self.setEnabled(True)
        if self.msgid_edit:
            self.msgid_edit.setPlainText(entry.msgid)
        if self.msgstr_edit:
            self.msgstr_edit.setPlainText(entry.msgstr)
        if self.fuzzy_checkbox:
            self.fuzzy_checkbox.setChecked(entry.fuzzy)
        if self.context_edit:
            self.context_edit.setText(entry.msgctxt or "")
        self.entry_changed.emit(self.current_entry_number or -1)
