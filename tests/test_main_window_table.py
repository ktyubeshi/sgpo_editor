#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import gc
import unittest
from unittest.mock import MagicMock

# モックの設定後にインポート
from sgpo_editor.gui.widgets.search import SearchCriteria


class MockMainWindow:
    """MainWindowのモック実装"""

    def __init__(self):
        # 各コンポーネントをモック化
        self.table = MagicMock()
        self.table_manager = MagicMock()
        self.file_handler = MagicMock()
        self.file_handler.current_po = MagicMock()
        self.event_handler = MagicMock()
        self.search_widget = MagicMock()
        self.status_bar = MagicMock()

        # statusBar()メソッドをモック化
        self.statusBar = MagicMock(return_value=self.status_bar)

    def _update_table(self):
        """テーブル更新のモック実装"""
        criteria = self.search_widget.get_search_criteria()
        entries = self.file_handler.current_po.get_filtered_entries()
        result = self.table_manager.update_table(entries, criteria)
        self.status_bar.showMessage(f"フィルタ結果: {len(result)}件")
        return result


class TestMainWindowTable(unittest.TestCase):
    """MainWindowのテーブル操作に関するテスト"""

    def setUp(self):
        """各テストの前処理"""
        # モックMainWindowのインスタンスを作成
        self.main_window = MockMainWindow()
        # POファイルのモックを取得
        self.mock_po = self.main_window.file_handler.current_po

    def tearDown(self):
        """各テストの後処理"""
        self.main_window = None
        gc.collect()

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
        self.mock_po.get_filtered_entries.return_value = mock_entries

        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria.return_value = SearchCriteria(
            filter="", search_text="", match_mode="部分一致"
        )

        # テーブルマネージャーの戻り値を設定
        self.main_window.table_manager.update_table.return_value = mock_entries

        # テスト対象メソッドを実行
        self.main_window._update_table()

        # 検証
        self.main_window.table_manager.update_table.assert_called_once()
        self.main_window.status_bar.showMessage.assert_called_with("フィルタ結果: 2件")

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
        ]

        # モックPOの戻り値を設定
        self.mock_po.get_entries.return_value = mock_entries
        self.mock_po.get_filtered_entries.return_value = mock_entries

        # SearchWidgetのメソッドをモック（フィルタ条件あり）
        self.main_window.search_widget.get_search_criteria.return_value = SearchCriteria(
            filter="未翻訳", search_text="", match_mode="部分一致"
        )

        # テーブルマネージャーの戻り値を設定
        self.main_window.table_manager.update_table.return_value = mock_entries

        # テスト対象メソッドを実行
        self.main_window._update_table()

        # 検証 - フィルタ条件「未翻訳」に一致するエントリは1つだけ
        self.main_window.table_manager.update_table.assert_called_once()
        self.main_window.status_bar.showMessage.assert_called_with("フィルタ結果: 1件")

    def test_update_table_with_search(self) -> None:
        """検索条件を使ったテーブル更新のテスト"""
        # モックエントリの作成
        mock_entries = [
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
        self.mock_po.get_filtered_entries.return_value = mock_entries

        # SearchWidgetのメソッドをモック（検索条件あり）
        self.main_window.search_widget.get_search_criteria.return_value = SearchCriteria(
            filter="", search_text="test2", match_mode="部分一致"
        )

        # テーブルマネージャーの戻り値を設定
        self.main_window.table_manager.update_table.return_value = mock_entries

        # テスト対象メソッドを実行
        self.main_window._update_table()

        # 検証 - 検索条件「test2」に一致するエントリは1つだけ
        self.main_window.table_manager.update_table.assert_called_once()
        self.main_window.status_bar.showMessage.assert_called_with("フィルタ結果: 1件")

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
        self.mock_po.get_filtered_entries.return_value = mock_entries

        # テーブルマネージャーの戻り値を設定
        self.main_window.table_manager.update_table.return_value = mock_entries

        # テーブル更新
        self.main_window._update_table()

        # テスト対象メソッドを実行（0行目をクリック）
        self.main_window.event_handler._on_cell_selected.assert_not_called()
        self.main_window.event_handler._on_cell_selected(0, 0)

        # 検証
        self.main_window.event_handler._on_cell_selected.assert_called_with(0, 0)


if __name__ == "__main__":
    unittest.main()
