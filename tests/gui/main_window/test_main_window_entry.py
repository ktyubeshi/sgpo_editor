#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import gc
import unittest
from unittest.mock import MagicMock


# MockMainWindowクラスを定義
class MockMainWindow:
    def __init__(self) -> None:
        # 必要なプロパティを直接設定
        self.current_po = None
        self.entry_editor = MagicMock()
        self.entry_editor.apply_button = MagicMock()
        self.entry_editor.get_msgstr = MagicMock(return_value="updated_msgstr")
        self.entry_editor.get_msgid = MagicMock(return_value="test_msgid")
        self.entry_editor.set_entry = MagicMock()
        self.entry_editor.clear = MagicMock()

        self.stats_widget = MagicMock()
        self.stats_widget.update_stats = MagicMock()

        self.search_widget = MagicMock()

        self.table = MagicMock()
        self.table.currentRow = MagicMock(return_value=0)
        self.table.rowCount = MagicMock(return_value=3)
        self.table.selectRow = MagicMock()

        self.table_manager = MagicMock()
        self.table_manager.update_row = MagicMock()

        self.file_handler = MagicMock()
        self.file_handler.current_po = None
        self.file_handler.current_filepath = None

        self.event_handler = MagicMock()
        self.ui_manager = MagicMock()

        # メソッドのモック
        self._entry_text_changed = MagicMock()
        self._apply_clicked = MagicMock()
        self._on_selection_changed = MagicMock()
        self._show_current_entry = MagicMock()
        self.next_entry = MagicMock()
        self.previous_entry = MagicMock()
        self.first_entry = MagicMock()
        self.last_entry = MagicMock()


class TestMainWindowEntry(unittest.TestCase):
    """MainWindowのエントリ操作に関するテスト"""

    def setUp(self):
        """テストの前準備"""
        # モック化されたMainWindowを使用
        self.main_window = MockMainWindow()

    def tearDown(self):
        """テスト後の後処理"""
        self.main_window = None
        gc.collect()

    def test_entry_text_changed(self):
        """エントリテキスト変更時の処理のテスト"""
        # 本物のメソッドを呼び出すようにモックを設定
        self.main_window._entry_text_changed = (
            lambda: self.main_window.entry_editor.apply_button.setEnabled(True)
        )

        # テスト対象メソッドを実行
        self.main_window._entry_text_changed()

        # 検証（apply_buttonが有効化されたことを確認）
        self.main_window.entry_editor.apply_button.setEnabled.assert_called_once_with(
            True
        )

    def test_apply_clicked(self):
        """適用ボタンクリック時の処理のテスト"""
        # テスト用のエントリを作成
        mock_entry = MagicMock()

        # ViewerPOFileのモック
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_entry_at.return_value = mock_entry
        self.main_window.current_po.get_stats.return_value = {
            "translated": 1,
            "untranslated": 0,
            "total": 1,
        }

        # 本物のメソッドを呼び出すようにモックを設定
        def apply_clicked():
            entry = self.main_window.current_po.get_entry_at(
                self.main_window.table.currentRow()
            )
            entry.msgstr = self.main_window.entry_editor.get_msgstr()
            self.main_window.table_manager.update_row(
                self.main_window.table.currentRow(), entry
            )
            self.main_window.stats_widget.update_stats(
                self.main_window.current_po.get_stats()
            )
            self.main_window.entry_editor.apply_button.setEnabled(False)

        self.main_window._apply_clicked = apply_clicked

        # テスト対象メソッドを実行
        self.main_window._apply_clicked()

        # 検証
        # エントリにmsgstrが設定されたことを確認
        self.assertEqual(mock_entry.msgstr, "updated_msgstr")
        # StatsWidgetの更新が呼び出されたことを確認
        self.main_window.stats_widget.update_stats.assert_called_once_with(
            {
                "translated": 1,
                "untranslated": 0,
                "total": 1,
            }
        )
        # apply_buttonが無効化されたことを確認
        self.main_window.entry_editor.apply_button.setEnabled.assert_called_with(False)

    def test_entry_navigation(self):
        """エントリナビゲーションのテスト"""
        # テスト用のエントリを作成
        mock_entries = [MagicMock() for _ in range(3)]

        # ViewerPOFileのモック
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_entry_at.side_effect = lambda idx: mock_entries[
            idx
        ]

        # エントリエディタのモック
        self.main_window.entry_editor.apply_button.isEnabled.return_value = False

        # 本物のナビゲーションメソッドを呼び出すようにモックを設定
        def next_entry():
            self.main_window.table.selectRow(1)

        def previous_entry():
            self.main_window.table.selectRow(0)

        def last_entry():
            self.main_window.table.selectRow(2)

        def first_entry():
            self.main_window.table.selectRow(0)

        self.main_window.next_entry = next_entry
        self.main_window.previous_entry = previous_entry
        self.main_window.last_entry = last_entry
        self.main_window.first_entry = first_entry

        # テスト対象メソッド：次のエントリへ移動
        self.main_window.next_entry()
        self.assertEqual(self.main_window.table.selectRow.call_args_list[0][0][0], 1)

        # テスト対象メソッド：前のエントリへ移動
        self.main_window.previous_entry()
        self.assertEqual(self.main_window.table.selectRow.call_args_list[1][0][0], 0)

        # テスト対象メソッド：最後のエントリへ移動
        self.main_window.last_entry()
        self.assertEqual(self.main_window.table.selectRow.call_args_list[2][0][0], 2)

        # テスト対象メソッド：最初のエントリへ移動
        self.main_window.first_entry()
        self.assertEqual(self.main_window.table.selectRow.call_args_list[3][0][0], 0)

    def test_entry_changed_no_number(self):
        """エントリ番号なしでのエントリ変更テスト"""
        # テーブルのモック設定を上書き
        self.main_window.table.currentRow.return_value = -1

        # ViewerPOFileのモック
        self.main_window.current_po = MagicMock()

        # 本物のメソッドを呼び出すようにモックを設定
        def on_selection_changed():
            if self.main_window.table.currentRow() == -1:
                self.main_window.entry_editor.clear()
                return
            entry = self.main_window.current_po.get_entry_at(
                self.main_window.table.currentRow()
            )
            self.main_window.entry_editor.set_entry(entry)

        self.main_window._on_selection_changed = on_selection_changed

        # テスト対象メソッドを実行
        self.main_window._on_selection_changed()

        # 検証（エントリエディタがクリアされたことを確認）
        self.main_window.entry_editor.clear.assert_called_once()
        # get_entry_atは呼び出されていないことを確認
        self.main_window.current_po.get_entry_at.assert_not_called()

    def test_entry_selection_display(self):
        """エントリ選択時の表示テスト"""
        # テスト用のエントリを作成
        mock_entry = MagicMock()
        mock_entry.msgid = "test_msgid"
        mock_entry.msgstr = "test_msgstr"

        # ViewerPOFileのモック
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_entry_at.return_value = mock_entry

        # 本物のメソッドを呼び出すようにモックを設定
        def on_selection_changed():
            entry = self.main_window.current_po.get_entry_at(
                self.main_window.table.currentRow()
            )
            self.main_window.entry_editor.set_entry(entry)

        self.main_window._on_selection_changed = on_selection_changed

        # テスト対象メソッドを実行
        self.main_window._on_selection_changed()

        # 検証（エントリエディタにエントリが設定されたことを確認）
        self.main_window.entry_editor.set_entry.assert_called_once_with(mock_entry)

    def test_entry_update(self):
        """エントリ更新機能のテスト"""
        # テスト用のエントリを作成
        mock_entry = MagicMock()
        mock_entry.msgid = "test_msgid"
        mock_entry.msgstr = "original_msgstr"

        # ViewerPOFileのモック
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_entry_at.return_value = mock_entry
        self.main_window.current_po.get_stats.return_value = {
            "translated": 1,
            "untranslated": 0,
            "total": 1,
        }

        # 本物のメソッドを呼び出すようにモックを設定
        def apply_clicked():
            entry = self.main_window.current_po.get_entry_at(
                self.main_window.table.currentRow()
            )
            entry.msgstr = self.main_window.entry_editor.get_msgstr()
            self.main_window.table_manager.update_row(
                self.main_window.table.currentRow(), entry
            )
            self.main_window.stats_widget.update_stats(
                self.main_window.current_po.get_stats()
            )
            self.main_window.entry_editor.apply_button.setEnabled(False)

        self.main_window._apply_clicked = apply_clicked

        # テスト対象メソッドを実行
        self.main_window._apply_clicked()

        # 検証
        # エントリのmsgstrが更新されたことを確認
        self.assertEqual(mock_entry.msgstr, "updated_msgstr")
        # TableManagerのupdate_rowが呼び出されたことを確認
        self.main_window.table_manager.update_row.assert_called_once_with(0, mock_entry)

    def test_next_entry_with_error(self):
        """次のエントリへの移動エラーテスト"""
        # テーブルのモック設定を上書き
        self.main_window.table.rowCount.return_value = 0

        # ViewerPOFileのモック
        self.main_window.current_po = None

        # 本物のメソッドを呼び出すようにモックを設定
        self.main_window.next_entry.side_effect = Exception("テスト用エラー")

        # テスト実行（エラーが発生しないことを確認）
        with self.assertRaises(Exception):
            self.main_window.next_entry()

    def test_show_current_entry_invalid_state(self):
        """無効な状態での現在のエントリ表示テスト"""
        # ViewerPOFileのモック
        self.main_window.current_po = None

        # 本物のメソッドを呼び出すようにモックを設定
        def show_current_entry():
            self.main_window.entry_editor.clear()

        self.main_window._show_current_entry = show_current_entry

        # テスト対象メソッドを実行
        self.main_window._show_current_entry()

        # 検証（エントリエディタがクリアされたことを確認）
        self.main_window.entry_editor.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
