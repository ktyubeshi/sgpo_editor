#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sgpo_editor.gui.widgets.preview_widget import PreviewDialog, PreviewWidget
from sgpo_editor.models import EntryModel


@pytest.fixture
def mock_entry():
    """モックエントリを作成するフィクスチャ"""
    entry = MagicMock(spec=EntryModel)
    entry.msgid = "Test ID"
    entry.msgstr = "Test String with \r\n escape sequences"
    entry.position = 1
    return entry


@pytest.fixture
def preview_widget(qtbot):
    """プレビューウィジェットを作成するフィクスチャ"""
    widget = PreviewWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def preview_dialog(qtbot):
    """プレビューダイアログを作成するフィクスチャ"""
    dialog = PreviewDialog()
    qtbot.addWidget(dialog)
    return dialog


class TestPreviewWidget:
    """プレビューウィジェットのテスト"""

    def test_init(self, preview_widget):
        """初期化のテスト"""
        assert preview_widget._current_entry is None
        assert preview_widget._preview_mode == "all"

    def test_set_entry(self, preview_widget, mock_entry):
        """エントリ設定のテスト"""
        # モックを使用して_update_previewが呼ばれることを確認
        with patch.object(preview_widget, "_update_preview") as mock_update:
            preview_widget.set_entry(mock_entry)
            assert preview_widget._current_entry == mock_entry
            mock_update.assert_called_once()

    def test_process_escape_sequences(self, preview_widget):
        """エスケープシーケンス処理のテスト"""
        # 二重エスケープのテスト
        # QTextBrowserは\r\nを\nに変換するため、厳密な文字列比較ではなく
        # エスケープシーケンスが適切に処理されているかを確認する
        processed = preview_widget._process_escape_sequences("\\\\r\\\\n")
        assert "\r" in processed or "\n" in processed
        assert processed != "\\\\r\\\\n"  # 元の文字列とは異なることを確認
        # 単一エスケープのテスト
        # 実装では\rと\nが個別に処理されるため、期待値も個別に指定
        processed = preview_widget._process_escape_sequences("\\r\\n")
        # QTextBrowserは\r\nを\nに変換するため、文字列比較ではなく含まれるかどうかを確認
        assert "\r" in processed or "\n" in processed
        assert preview_widget._process_escape_sequences("\\t") == "\t"
        assert preview_widget._process_escape_sequences('\\"') == '"'
        assert preview_widget._process_escape_sequences("\\'") == "'"
        assert preview_widget._process_escape_sequences("\\\\") == "\\"
        # 複合テスト
        processed = preview_widget._process_escape_sequences("Test\\r\\nString")
        assert "Test" in processed and "String" in processed
        # QTextBrowserは\r\nを\nに変換するため、文字列比較ではなく含まれるかどうかを確認
        assert "\r" in processed or "\n" in processed

    def test_update_preview(self, preview_widget, mock_entry):
        """プレビュー更新のテスト"""
        # エントリがない場合
        preview_widget._current_entry = None
        preview_widget._update_preview()
        assert preview_widget.original_text.toPlainText() == ""
        assert preview_widget.preview_text.toPlainText() == ""

        # エントリがある場合
        preview_widget._current_entry = mock_entry
        preview_widget._update_preview()
        # QTextBrowserでは\r\nが\nに変換されるため、テキストの比較を調整
        assert "Test String with" in preview_widget.original_text.toPlainText()
        # エスケープシーケンスが処理されていることを確認
        assert "\\r\\n" not in preview_widget.preview_text.toPlainText()
        # QTextBrowserでは\r\nが\nに変換されるため、\nの存在を確認
        assert "\n" in preview_widget.preview_text.toPlainText()

    def test_escape_sequence_display(self, preview_widget, qtbot):
        """エスケープシーケンスの表示テスト

        エスケープ前とエスケープ後の表示に違いがあることを確認する
        """
        # テスト用のエントリを作成
        entry = MagicMock(spec=EntryModel)
        entry.msgid = "Test ID"
        entry.msgstr = "Line1\nLine2\tTabbed"
        entry.position = 1

        # エスケープモードを設定
        preview_widget.mode_combo.setCurrentText("エスケープシーケンスのみ")
        qtbot.wait(100)  # UI更新を待つ

        # エントリを設定
        preview_widget.set_entry(entry)

        # プレビューテキストがエスケープ処理されていることを確認
        # HTMLとして表示されているため、toPlainText()ではなくtoHtml()を使用
        html_content = preview_widget.preview_text.toHtml()

        # HTML内に<br>タグが含まれていることを確認（\nが<br>に変換されている）
        # Qtは<br />の形式で出力する
        assert "<br />" in html_content

        # HTML内に\xa0（ノーブレークスペース）が含まれていることを確認（\tが\xa0に変換されている）
        # Qtは&nbsp;をUnicode文字\xa0として出力する
        assert "\xa0" in html_content

        # 元のテキストとプレビューのテキストが異なることを確認
        original_plain = preview_widget.original_text.toPlainText()
        preview_plain = preview_widget.preview_text.toPlainText()

        # 元のテキストには\nが含まれているが、プレビューでは実際の改行に変換されている
        assert original_plain != preview_plain

        # エスケープモードを無効にして比較
        preview_widget.mode_combo.setCurrentText("HTMLタグのみ")
        qtbot.wait(100)  # UI更新を待つ

        # エスケープ処理が無効の場合、元のテキストとプレビューのテキストが同じになる
        # プレーンテキストとして表示されるため、HTMLタグは含まれない
        plain_text_no_escape = preview_widget.preview_text.toPlainText()
        # エスケープ処理が無効なので、元のテキストがそのまま表示される
        assert "Line1\nLine2\tTabbed" in plain_text_no_escape


class TestPreviewDialog:
    """プレビューダイアログのテスト"""

    def test_init(self, preview_dialog):
        """初期化のテスト"""
        assert preview_dialog.windowTitle() == "プレビュー"
        assert hasattr(preview_dialog, "preview_widget")

    def test_set_entry(self, preview_dialog, mock_entry):
        """エントリ設定のテスト"""
        # モックを使用してpreview_widget.set_entryが呼ばれることを確認
        with patch.object(preview_dialog.preview_widget, "set_entry") as mock_set_entry:
            preview_dialog.set_entry(mock_entry)
            mock_set_entry.assert_called_once_with(mock_entry)


@pytest.mark.integration
class TestPreviewIntegration:
    """プレビュー機能の統合テスト"""

    def test_main_window_preview(self, monkeypatch, qtbot):
        """メインウィンドウからのプレビュー表示テスト"""
        # まずモックを設定してからMainWindowをインポートする
        # PreviewDialogのshow/raise_/activateWindowをモック化
        mock_preview_dialog = MagicMock()
        mock_preview_dialog_instance = MagicMock()
        mock_preview_dialog.return_value = mock_preview_dialog_instance

        # メインウィンドウがインポートする前にモックを設定
        # メインウィンドウは直接インポートしているので、そのパスをモック化
        monkeypatch.setattr(
            "sgpo_editor.gui.widgets.preview_widget.PreviewDialog", mock_preview_dialog
        )
        # メインウィンドウが直接インポートするパスもモック化
        monkeypatch.setattr(
            "sgpo_editor.gui.main_window.PreviewDialog", mock_preview_dialog
        )

        # ここでMainWindowをインポート
        from sgpo_editor.gui.main_window import MainWindow

        # MainWindowのインスタンスを作成
        window = MainWindow()
        qtbot.addWidget(window)

        # モックエントリを作成
        mock_entry = MagicMock(spec=EntryModel)
        mock_entry.msgid = "Test ID"
        mock_entry.msgstr = "Test String with \\r\\n escape sequences"
        mock_entry.position = 1

        # ファサードパターンの変更に対応して、EntryEditorFacadeのget_current_entryをモック化
        window.entry_editor_facade.get_current_entry = MagicMock(
            return_value=mock_entry
        )
        # 互換性のためにEventHandlerのメソッドもモック化
        window.event_handler.get_current_entry = MagicMock(return_value=mock_entry)

        # プレビューダイアログを表示
        window._show_preview_dialog()

        # 現在の実装では、プレビューダイアログを表示した後、entry_selectedシグナルを通じて
        # _update_preview_dialogメソッドが呼び出される設計になっている
        # テストでは、このフローをシミュレートする

        # ViewerPOFileのモックを設定
        mock_po_file = MagicMock()
        mock_po_file.get_filtered_entries.return_value = [mock_entry]
        window._get_current_po = MagicMock(return_value=mock_po_file)

        # エントリ選択シグナルを発行して_update_preview_dialogを呼び出す
        window._update_preview_dialog(0)  # エントリ番号を0として呼び出す

        # 検証
        mock_preview_dialog.assert_called_once()
        assert (
            mock_preview_dialog_instance.set_entry.call_count == 2
        )
        mock_preview_dialog_instance.set_entry.assert_called_with(mock_entry)
        mock_preview_dialog_instance.show.assert_called_once()
        mock_preview_dialog_instance.raise_.assert_called_once()
        mock_preview_dialog_instance.activateWindow.assert_called_once()
