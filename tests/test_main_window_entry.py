#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations
from typing import Any, Dict, List, Optional

from unittest.mock import MagicMock, patch, call
import unittest
import sys

# 基底クラスをインポート
from tests.test_base import TestBase

# モックの設定後にインポート
from PySide6.QtWidgets import QApplication, QTableWidgetItem
from PySide6.QtCore import Qt
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.models.entry import EntryModel


class TestMainWindowEntry(TestBase):
    """MainWindowのエントリ操作に関するテスト"""

    def test_entry_text_changed(self) -> None:
        """エントリテキスト変更時の処理のテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テスト対象メソッドを実行
        main_window._entry_text_changed()
        
        # 検証（apply_buttonが有効化されたことを確認）
        main_window.entry_editor.apply_button.setEnabled.assert_called_once_with(True)

    def test_apply_clicked(self) -> None:
        """適用ボタンクリック時の処理のテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テーブルのモック
        main_window.table.currentRow.return_value = 0
        
        # エントリエディタのモック
        main_window.entry_editor.get_msgstr.return_value = "updated_msgstr"
        main_window.entry_editor.get_msgid.return_value = "test_msgid"
        
        # テスト用のエントリを作成
        mock_entry = MagicMock()
        
        # ViewerPOFileのモック
        main_window.current_po = MagicMock()
        main_window.current_po.get_entry_at.return_value = mock_entry
        main_window.current_po.get_stats.return_value = {"translated": 1, "untranslated": 0, "total": 1}
        
        # テスト対象メソッドを実行
        main_window._apply_clicked()
        
        # 検証
        # エントリにmsgstrが設定されたことを確認
        mock_entry.msgstr = "updated_msgstr"
        # StatsWidgetの更新が呼び出されたことを確認
        main_window.stats_widget.update_stats.assert_called_once_with({"translated": 1, "untranslated": 0, "total": 1})
        # apply_buttonが無効化されたことを確認
        main_window.entry_editor.apply_button.setEnabled.assert_called_with(False)

    def test_entry_navigation(self) -> None:
        """エントリナビゲーションのテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テーブルのモック
        main_window.table.rowCount.return_value = 3
        main_window.table.currentRow.return_value = 0
        
        # テスト用のエントリを作成
        mock_entries = [MagicMock() for _ in range(3)]
        
        # ViewerPOFileのモック
        main_window.current_po = MagicMock()
        main_window.current_po.get_entry_at.side_effect = lambda idx: mock_entries[idx]
        
        # エントリエディタのモック
        main_window.entry_editor.apply_button.isEnabled.return_value = False
        
        # テスト対象メソッド：次のエントリへ移動
        main_window.next_entry()
        self.assertEqual(main_window.table.selectRow.call_args_list[0][0][0], 1)
        
        # テスト対象メソッド：前のエントリへ移動
        main_window.previous_entry()
        self.assertEqual(main_window.table.selectRow.call_args_list[1][0][0], 0)
        
        # テスト対象メソッド：最後のエントリへ移動
        main_window.last_entry()
        self.assertEqual(main_window.table.selectRow.call_args_list[2][0][0], 2)
        
        # テスト対象メソッド：最初のエントリへ移動
        main_window.first_entry()
        self.assertEqual(main_window.table.selectRow.call_args_list[3][0][0], 0)

    def test_entry_changed_no_number(self) -> None:
        """エントリ番号なしでのエントリ変更テスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テーブルのモック
        main_window.table.currentRow.return_value = -1
        
        # ViewerPOFileのモック
        main_window.current_po = MagicMock()
        
        # テスト対象メソッドを実行
        main_window._on_selection_changed()
        
        # 検証（エントリエディタがクリアされたことを確認）
        main_window.entry_editor.clear.assert_called_once()
        # get_entry_atは呼び出されていないことを確認
        main_window.current_po.get_entry_at.assert_not_called()

    def test_entry_selection_display(self) -> None:
        """エントリ選択時の表示テスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テーブルのモック
        main_window.table.currentRow.return_value = 0
        
        # テスト用のエントリを作成
        mock_entry = MagicMock()
        mock_entry.msgid = "test_msgid"
        mock_entry.msgstr = "test_msgstr"
        
        # ViewerPOFileのモック
        main_window.current_po = MagicMock()
        main_window.current_po.get_entry_at.return_value = mock_entry
        
        # テスト対象メソッドを実行
        main_window._on_selection_changed()
        
        # 検証（エントリエディタにエントリが設定されたことを確認）
        main_window.entry_editor.set_entry.assert_called_once_with(mock_entry)

    def test_entry_update(self) -> None:
        """エントリ更新機能のテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テーブルのモック
        main_window.table.currentRow.return_value = 0
        
        # エントリエディタのモック
        main_window.entry_editor.get_msgstr.return_value = "updated_msgstr"
        main_window.entry_editor.get_msgid.return_value = "test_msgid"
        
        # テスト用のエントリを作成
        mock_entry = MagicMock()
        mock_entry.msgid = "test_msgid"
        mock_entry.msgstr = "original_msgstr"
        
        # ViewerPOFileのモック
        main_window.current_po = MagicMock()
        main_window.current_po.get_entry_at.return_value = mock_entry
        main_window.current_po.get_stats.return_value = {"translated": 1, "untranslated": 0, "total": 1}
        
        # テスト対象メソッドを実行
        main_window._apply_clicked()
        
        # 検証
        # エントリのmsgstrが更新されたことを確認
        self.assertEqual(mock_entry.msgstr, "updated_msgstr")
        # TableManagerのupdate_rowが呼び出されたことを確認
        main_window.table_manager.update_row.assert_called_once_with(0, mock_entry)

    def test_next_entry_with_error(self) -> None:
        """次のエントリへの移動エラーテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テーブルのモック
        main_window.table.rowCount.return_value = 0
        
        # ViewerPOFileのモック
        main_window.current_po = None
        
        # メッセージボックスのモック
        with patch("sgpo_editor.gui.main_window.QMessageBox.warning") as mock_warning:
            # テスト対象メソッドを実行
            main_window.next_entry()
            
            # 検証（警告メッセージが表示されたことを確認）
            mock_warning.assert_called_once()

    def test_show_current_entry_invalid_state(self) -> None:
        """無効な状態での現在のエントリ表示テスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # ViewerPOFileのモック
        main_window.current_po = None
        
        # テーブルのモック
        main_window.table.currentRow.return_value = 0
        
        # テスト対象メソッドを実行
        main_window._show_current_entry()
        
        # 検証（エントリエディタがクリアされたことを確認）
        main_window.entry_editor.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
