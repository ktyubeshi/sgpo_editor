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
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.models.entry import EntryModel
from sgpo_editor.gui.widgets.search import SearchCriteria


class TestMainWindowTable(TestBase):
    """MainWindowのテーブル操作に関するテスト"""

    def setUp(self) -> None:
        """各テストの前処理"""
        # MainWindowのインスタンスを作成
        with patch('sgpo_editor.gui.main_window.QApplication'):
            self.main_window = MainWindow()
            
            # POファイルのモック
            self.mock_po = MagicMock()
            self.main_window.current_po = self.mock_po

    def test_update_table(self) -> None:
        """テーブル更新のテスト"""
        # モックエントリの作成
        mock_entries = [
            {
                "msgid": "test1",
                "msgstr": "テスト1",
                "locations": ["file1.py:10"],
                "flags": ["fuzzy"],
                "status": "未翻訳",
            },
            {
                "msgid": "test2",
                "msgstr": "テスト2",
                "locations": ["file2.py:20"],
                "flags": [],
                "status": "翻訳済み",
            },
        ]
        
        # モックPOの戻り値を設定
        self.mock_po.get_entries.return_value = mock_entries
        
        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria = MagicMock(
            return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致")
        )

        # テスト対象メソッドを実行
        self.main_window._update_table()
        
        # 検証
        self.main_window.table.setRowCount.assert_called_with(2)
        self.assertEqual(self.main_window.table.setItem.call_count, 10)  # 5項目 × 2エントリ

    def test_update_table_with_filter(self) -> None:
        """フィルタ条件を使ったテーブル更新のテスト"""
        # モックエントリの作成
        mock_entries = [
            {
                "msgid": "test1",
                "msgstr": "テスト1",
                "locations": ["file1.py:10"],
                "flags": ["fuzzy"],
                "status": "未翻訳",
            },
            {
                "msgid": "test2",
                "msgstr": "テスト2",
                "locations": ["file2.py:20"],
                "flags": [],
                "status": "翻訳済み",
            },
        ]
        
        # モックPOの戻り値を設定
        self.mock_po.get_entries.return_value = mock_entries
        
        # SearchWidgetのメソッドをモック（フィルタ条件あり）
        self.main_window.search_widget.get_search_criteria = MagicMock(
            return_value=SearchCriteria(filter="未翻訳", search_text="", match_mode="部分一致")
        )

        # テスト対象メソッドを実行
        self.main_window._update_table()
        
        # 検証 - フィルタ条件「未翻訳」に一致するエントリは1つだけ
        self.main_window.table.setRowCount.assert_called_with(1)
        self.assertEqual(self.main_window.table.setItem.call_count, 5)  # 5項目 × 1エントリ

    def test_update_table_with_search(self) -> None:
        """検索条件を使ったテーブル更新のテスト"""
        # モックエントリの作成
        mock_entries = [
            {
                "msgid": "test1",
                "msgstr": "テスト1",
                "locations": ["file1.py:10"],
                "flags": ["fuzzy"],
                "status": "未翻訳",
            },
            {
                "msgid": "test2",
                "msgstr": "テスト2",
                "locations": ["file2.py:20"],
                "flags": [],
                "status": "翻訳済み",
            },
        ]
        
        # モックPOの戻り値を設定
        self.mock_po.get_entries.return_value = mock_entries
        
        # SearchWidgetのメソッドをモック（検索条件あり）
        self.main_window.search_widget.get_search_criteria = MagicMock(
            return_value=SearchCriteria(filter="", search_text="test2", match_mode="部分一致")
        )

        # テスト対象メソッドを実行
        self.main_window._update_table()
        
        # 検証 - 検索条件「test2」に一致するエントリは1つだけ
        self.main_window.table.setRowCount.assert_called_with(1)
        self.assertEqual(self.main_window.table.setItem.call_count, 5)  # 5項目 × 1エントリ

    def test_table_cell_clicked(self) -> None:
        """テーブルセルクリック時の処理のテスト"""
        # モックエントリの作成
        mock_entries = [
            {
                "msgid": "test1",
                "msgstr": "テスト1",
                "locations": ["file1.py:10"],
                "flags": ["fuzzy"],
                "status": "未翻訳",
            },
            {
                "msgid": "test2",
                "msgstr": "テスト2",
                "locations": ["file2.py:20"],
                "flags": [],
                "status": "翻訳済み",
            },
        ]
        
        # モックPOの戻り値を設定
        self.mock_po.get_entries.return_value = mock_entries
        
        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria = MagicMock(
            return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致")
        )

        # テーブル更新
        self.main_window._update_table()
        
        # EntryEditorのメソッドをモック
        self.main_window.entry_editor.set_entry = MagicMock()
        
        # テスト対象メソッドを実行（0行目をクリック）
        self.main_window._table_cell_clicked(0, 0)
        
        # 検証
        self.main_window.entry_editor.set_entry.assert_called_with(mock_entries[0])


if __name__ == "__main__":
    unittest.main()
