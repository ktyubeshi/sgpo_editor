"""エントリエディタの状態管理テスト"""

from unittest.mock import Mock, patch

import pytest

from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.models import EntryModel


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


def test_entry_editor_state_initialization(entry_editor):
    """初期状態の確認"""
    assert entry_editor.current_entry is None
    assert entry_editor.current_entry_number is None
    assert not entry_editor.isEnabled()
    assert entry_editor._text_change_timer.isActive() is False


def test_entry_editor_state_after_set_entry(entry_editor, mock_entry):
    """エントリ設定後の状態確認"""
    entry_editor.set_entry(mock_entry)

    assert entry_editor.current_entry == mock_entry
    assert entry_editor.isEnabled()
    assert entry_editor.context_edit.text() == mock_entry.msgctxt
    assert entry_editor.msgid_edit.toPlainText() == mock_entry.msgid
    assert entry_editor.msgstr_edit.toPlainText() == mock_entry.msgstr
    assert entry_editor.fuzzy_checkbox.isChecked() == mock_entry.fuzzy


def test_entry_editor_state_text_changes(entry_editor, mock_entry):
    """テキスト変更時の状態確認"""
    entry_editor.set_entry(mock_entry)

    # コンテキストの変更
    entry_editor.context_edit.setText("new context")
    assert entry_editor.context_edit.text() == "new context"
    assert entry_editor._text_change_timer.isActive()

    # タイマーの発火を待つ
    entry_editor._text_change_timer.timeout.emit()
    assert not entry_editor._text_change_timer.isActive()


def test_entry_editor_state_fuzzy_changes(entry_editor, mock_entry):
    """Fuzzy状態変更時の状態確認"""
    entry_editor.set_entry(mock_entry)

    # Fuzzyチェックボックスの状態変更
    entry_editor.fuzzy_checkbox.setChecked(True)
    assert entry_editor.fuzzy_checkbox.isChecked()
    assert mock_entry.fuzzy is True


def test_entry_editor_state_apply_changes(entry_editor, mock_entry):
    """Applyボタン押下時の状態確認"""
    entry_editor.set_entry(mock_entry)

    # テキストを変更
    entry_editor.msgstr_edit.setPlainText("new translation")

    # Applyボタンを押す
    entry_editor.apply_button.click()

    # 変更が反映されていることを確認
    assert mock_entry.msgstr == "new translation"


def test_entry_editor_state_review_dialogs(entry_editor, mock_entry):
    """レビューダイアログ表示時の状態確認"""
    entry_editor.set_entry(mock_entry)

    dialog_types = [
        "translator_comment",
        "review_comment",
        "quality_score",
        "check_result",
        "debug",
    ]

    for dialog_type in dialog_types:
        assert dialog_type not in entry_editor._review_dialogs
        entry_editor._show_review_dialog(dialog_type)
        assert dialog_type in entry_editor._review_dialogs
        assert entry_editor._review_dialogs[dialog_type].isVisible()


def test_entry_editor_state_entry_changes(entry_editor, mock_entry):
    """エントリ変更時の状態確認"""
    entry_editor.set_entry(mock_entry)

    # 新しいエントリを作成
    new_entry = Mock(spec=EntryModel)
    new_entry.msgctxt = "new context"
    new_entry.msgid = "new source text"
    new_entry.msgstr = "new translated text"
    new_entry.fuzzy = True

    # エントリを変更
    entry_editor.set_entry(new_entry)

    # 状態が更新されていることを確認
    assert entry_editor.current_entry == new_entry
    assert entry_editor.context_edit.text() == new_entry.msgctxt
    assert entry_editor.msgid_edit.toPlainText() == new_entry.msgid
    assert entry_editor.msgstr_edit.toPlainText() == new_entry.msgstr
    assert entry_editor.fuzzy_checkbox.isChecked() == new_entry.fuzzy


def test_entry_editor_state_error_handling(entry_editor, mock_entry):
    """エラー発生時の状態確認"""
    # 無効なエントリを設定
    entry_editor.set_entry(None)
    assert not entry_editor.isEnabled()
    assert entry_editor.current_entry is None

    # 正常なエントリを設定
    entry_editor.set_entry(mock_entry)
    assert entry_editor.isEnabled()
    assert entry_editor.current_entry == mock_entry

    # エラーを発生させる
    with patch.object(
        entry_editor, "_show_review_dialog", side_effect=Exception("Test error")
    ):
        try:
            entry_editor._show_review_dialog("test")
        except Exception:
            pass
        # エラー後も状態が維持されていることを確認
        assert entry_editor.isEnabled()
        assert entry_editor.current_entry == mock_entry
