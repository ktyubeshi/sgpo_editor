"""エントリエディタのテスト"""

from unittest.mock import Mock, patch

import pytest

from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.models import EntryModel
from sgpo_editor.models.database import Database


@pytest.fixture
def entry_editor(qtbot):
    """エントリエディタのフィクスチャ"""
    editor = EntryEditor()
    qtbot.addWidget(editor)
    editor.show()
    return editor


@pytest.fixture
def mock_entry():
    """モックエントリ"""
    entry = Mock(spec=EntryModel)
    entry.msgctxt = "context"
    entry.msgid = "source text"
    entry.msgstr = "translated text"
    entry.fuzzy = False
    return entry


@pytest.fixture
def mock_database():
    """モックデータベース"""
    database = Mock(spec=Database)
    return database


def test_entry_editor_initialization(entry_editor):
    """エントリエディタの初期化を確認"""
    assert entry_editor.current_entry is None
    assert entry_editor.current_entry_number is None
    assert entry_editor.database is None
    assert entry_editor.get_layout_type() == LayoutType.LAYOUT1
    assert not entry_editor.isEnabled()


def test_entry_editor_set_entry(entry_editor, mock_entry):
    """エントリの設定を確認"""
    entry_editor.set_entry(mock_entry)

    assert entry_editor.current_entry == mock_entry
    assert entry_editor.context_edit.text() == mock_entry.msgctxt
    assert entry_editor.msgid_edit.toPlainText() == mock_entry.msgid
    assert entry_editor.msgstr_edit.toPlainText() == mock_entry.msgstr
    assert entry_editor.fuzzy_checkbox.isChecked() == mock_entry.fuzzy
    assert entry_editor.isEnabled()


def test_entry_editor_text_changes(entry_editor, mock_entry):
    """テキスト変更の処理を確認"""
    entry_editor.set_entry(mock_entry)

    # コンテキストの変更
    entry_editor.context_edit.setText("new context")
    assert entry_editor.context_edit.text() == "new context"

    # msgstrの変更
    entry_editor.msgstr_edit.setPlainText("new translation")
    assert entry_editor.msgstr_edit.toPlainText() == "new translation"


def test_entry_editor_fuzzy_changes(entry_editor, mock_entry):
    """Fuzzy状態の変更を確認"""
    entry_editor.set_entry(mock_entry)

    # Fuzzyチェックボックスの状態変更
    entry_editor.fuzzy_checkbox.setChecked(True)
    assert entry_editor.fuzzy_checkbox.isChecked()


def test_entry_editor_layout_changes(entry_editor):
    """レイアウト変更を確認"""
    # LAYOUT2に変更
    entry_editor.set_layout_type(LayoutType.LAYOUT2)
    assert entry_editor.get_layout_type() == LayoutType.LAYOUT2

    # LAYOUT1に戻す
    entry_editor.set_layout_type(LayoutType.LAYOUT1)
    assert entry_editor.get_layout_type() == LayoutType.LAYOUT1


def test_entry_editor_database_setter(entry_editor, mock_database):
    """データベース設定を確認"""
    entry_editor.database = mock_database
    assert entry_editor.database == mock_database


def test_entry_editor_apply_button(entry_editor, mock_entry):
    """Applyボタンの動作を確認"""
    entry_editor.set_entry(mock_entry)

    # シグナルをモック
    with patch.object(entry_editor, "apply_clicked") as mock_signal:
        entry_editor.apply_button.click()
        mock_signal.emit.assert_called_once()


def test_entry_editor_review_dialogs(entry_editor, mock_entry, mock_database):
    """レビューダイアログの表示を確認"""
    entry_editor.set_entry(mock_entry)
    entry_editor.database = mock_database

    dialog_types = [
        "translator_comment",
        "review_comment",
        "quality_score",
        "check_result",
        "debug",
    ]

    for dialog_type in dialog_types:
        with patch("PySide6.QtWidgets.QDialog") as mock_dialog:
            entry_editor._show_review_dialog(dialog_type)
            mock_dialog.assert_called_once()


def test_entry_editor_error_handling(entry_editor, mock_entry):
    """エラーハンドリングを確認"""
    # 無効なエントリを設定
    entry_editor.set_entry(None)
    assert not entry_editor.isEnabled()

    # 正常なエントリを設定
    entry_editor.set_entry(mock_entry)
    assert entry_editor.isEnabled()

    # 無効なデータベースを設定
    entry_editor.database = None
    assert entry_editor.database is None
