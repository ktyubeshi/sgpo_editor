"""エントリエディタのイベント処理テスト"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt

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


def test_entry_editor_text_change_events(entry_editor, mock_entry):
    """テキスト変更イベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

    # シグナルをモック
    with patch.object(entry_editor, "text_changed") as mock_signal:
        # コンテキストの変更
        entry_editor.context_edit.setText("new context")
        assert entry_editor._text_change_timer.isActive()

        # タイマーの発火を待つ
        entry_editor._text_change_timer.timeout.emit()
        mock_signal.emit.assert_called_once()

        # msgstrの変更
        entry_editor.msgstr_edit.setPlainText("new translation")
        assert entry_editor._text_change_timer.isActive()

        # タイマーの発火を待つ
        entry_editor._text_change_timer.timeout.emit()
        assert mock_signal.emit.call_count == 2


def test_entry_editor_apply_button_events(entry_editor, mock_entry):
    """Applyボタンイベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

    # シグナルをモック
    with patch.object(entry_editor, "apply_clicked") as mock_signal:
        # Applyボタンを押す
        entry_editor.apply_button.click()
        mock_signal.emit.assert_called_once()


def test_entry_editor_fuzzy_change_events(entry_editor, mock_entry):
    """Fuzzy状態変更イベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

    # シグナルをモック
    with patch.object(entry_editor, "text_changed") as mock_signal:
        # Fuzzyチェックボックスの状態変更
        entry_editor.fuzzy_checkbox.setChecked(True)
        assert entry_editor._text_change_timer.isActive()

        # タイマーの発火を待つ
        entry_editor._text_change_timer.timeout.emit()
        mock_signal.emit.assert_called_once()


def test_entry_editor_entry_change_events(entry_editor, mock_entry):
    """エントリ変更イベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

    # シグナルをモック
    with patch.object(entry_editor, "entry_changed") as mock_signal:
        # 新しいエントリを作成
        new_entry = Mock(spec=EntryModel)
        new_entry.msgctxt = "new context"
        new_entry.msgid = "new source text"
        new_entry.msgstr = "new translated text"
        new_entry.fuzzy = True

        # エントリを変更
        entry_editor.set_entry(new_entry)
        mock_signal.emit.assert_called_once()


def test_entry_editor_review_dialog_events(entry_editor, mock_entry):
    """レビューダイアログイベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

    dialog_types = [
        "translator_comment",
        "review_comment",
        "quality_score",
        "check_result",
        "debug",
    ]

    for dialog_type in dialog_types:
        with patch("PySide6.QtWidgets.QDialog") as mock_dialog:
            # ダイアログを表示
            entry_editor._show_review_dialog(dialog_type)
            mock_dialog.assert_called_once()

            # ダイアログが表示されていることを確認
            assert dialog_type in entry_editor._review_dialogs
            assert entry_editor._review_dialogs[dialog_type].isVisible()


def test_entry_editor_keyboard_events(entry_editor, mock_entry):
    """キーボードイベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

    # Applyボタンのシグナルをモック
    with patch.object(entry_editor, "apply_clicked") as mock_signal:
        # Ctrl+ReturnでApply
        qtbot.keyClick(
            entry_editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier
        )
        mock_signal.emit.assert_called_once()


def test_entry_editor_timer_events(entry_editor, mock_entry):
    """タイマーイベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

    # シグナルをモック
    with patch.object(entry_editor, "text_changed") as mock_signal:
        # テキストを変更
        entry_editor.msgstr_edit.setPlainText("new translation")
        assert entry_editor._text_change_timer.isActive()

        # タイマーを停止
        entry_editor._text_change_timer.stop()
        assert not entry_editor._text_change_timer.isActive()

        # タイマーを再起動
        entry_editor._text_change_timer.start()
        assert entry_editor._text_change_timer.isActive()

        # タイマーの発火を待つ
        entry_editor._text_change_timer.timeout.emit()
        mock_signal.emit.assert_called_once()


def test_entry_editor_error_events(entry_editor, mock_entry):
    """エラーイベントの処理を確認"""
    entry_editor.set_entry(mock_entry)

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


def test_apply_shortcut(entry_editor, qtbot):
    """Ctrl+ReturnでApplyが実行されることをテスト"""
    # Applyボタンのシグナルをモック
    with patch.object(entry_editor, "apply_clicked") as mock_signal:
        # Ctrl+ReturnでApply
        qtbot.keyClick(
            entry_editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier
        )
        mock_signal.emit.assert_called_once()
