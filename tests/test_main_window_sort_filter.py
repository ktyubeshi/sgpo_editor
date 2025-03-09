#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import gc
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.widgets.search import SearchCriteria


class TestMainWindowSortFilter(unittest.TestCase):
    """テーブルのソートとフィルタの連携テスト"""

    def setUp(self):
        """各テストの前処理"""
        # テーブルウィジェットのモック
        self.table = MagicMock()
        self.table.horizontalHeader().setSortIndicator = MagicMock()
        
        # POファイル取得用コールバックのモック
        self.get_current_po = MagicMock()
        self.mock_po = MagicMock()
        self.get_current_po.return_value = self.mock_po
        
        # フィルタ条件
        self.filter_text = "translated"
        self.search_text = "keyword"
        
        # テスト対象のテーブルマネージャー
        self.table_manager = TableManager(self.table, self.get_current_po)
        
        # メインウィンドウのモック
        self.main_window = MagicMock()
        self.main_window.search_widget = MagicMock()
        self.main_window.search_widget.get_search_criteria.return_value = SearchCriteria(
            filter=self.filter_text,
            filter_keyword=self.search_text,
            match_mode="部分一致"
        )

    def tearDown(self):
        """各テストの後処理"""
        self.table = None
        self.get_current_po = None
        self.mock_po = None
        self.table_manager = None
        self.main_window = None
        gc.collect()

    def test_sort_preserves_filter(self):
        """ソート実行時にフィルタ条件が保持されることを確認するテスト"""
        # 初期状態でフィルタを適用
        self.table_manager.update_table(
            self.mock_po,
            filter_text=self.filter_text,
            search_text=self.search_text
        )
        
        # モックのリセット
        self.mock_po.get_filtered_entries.reset_mock()
        
        # ヘッダークリックイベントをシミュレート
        self.table_manager._on_header_clicked(2)  # 2列目（msgid）をクリック
        
        # フィルタ条件が保持されていることを確認
        self.mock_po.get_filtered_entries.assert_called_once_with(
            filter_text=self.filter_text,
            filter_keyword=self.search_text
        )

    def test_sort_with_main_window_filter(self):
        """MainWindowと連携したソート時のフィルタ保持テスト"""
        # MainWindowのモックメソッドを設定
        def mock_update_table():
            criteria = self.main_window.search_widget.get_search_criteria()
            self.table_manager.update_table(
                self.mock_po,
                filter_text=criteria.filter,
                search_text=criteria.filter_keyword
            )
        
        self.main_window._update_table = mock_update_table
        
        # 初期状態でフィルタを適用
        self.main_window._update_table()
        
        # モックのリセット
        self.mock_po.get_filtered_entries.reset_mock()
        
        # ヘッダークリックイベントをシミュレート
        self.table_manager._on_header_clicked(2)  # 2列目（msgid）をクリック
        
        # フィルタ条件が保持されていることを確認
        self.mock_po.get_filtered_entries.assert_called_once_with(
            filter_text=self.filter_text,
            filter_keyword=self.search_text
        )


if __name__ == "__main__":
    unittest.main()
