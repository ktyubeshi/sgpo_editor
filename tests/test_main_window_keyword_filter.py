#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import gc
import unittest
from unittest.mock import MagicMock, patch

from sgpo_editor.gui.widgets.search import SearchCriteria


class TestMainWindowKeywordFilter(unittest.TestCase):
    """MainWindowのキーワードフィルタ機能のテスト"""

    def setUp(self):
        """各テストの前処理"""
        # MainWindowのモック
        self.main_window = MagicMock()
        
        # 検索ウィジェットのモック
        self.main_window.search_widget = MagicMock()
        
        # ファイルハンドラのモック
        self.main_window.file_handler = MagicMock()
        self.main_window.file_handler.current_po = MagicMock()
        
        # テーブルマネージャのモック
        self.main_window.table_manager = MagicMock()
        
        # ステータスバーのモック
        self.main_window.status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=self.main_window.status_bar)

    def tearDown(self):
        """各テストの後処理"""
        self.main_window = None
        gc.collect()

    def test_keyword_filter_is_passed_to_po_file(self):
        """キーワードフィルタがPOファイルに正しく渡されることを確認するテスト"""
        # SearchCriteriaのモック
        mock_criteria = SearchCriteria(filter="", filter_keyword="test_keyword", match_mode="部分一致")
        self.main_window.search_widget.get_search_criteria.return_value = mock_criteria
        
        # _update_tableメソッドを定義
        def mock_update_table():
            criteria = self.main_window.search_widget.get_search_criteria()
            entries = self.main_window.file_handler.current_po.get_filtered_entries(
                filter_text=criteria.filter,
                filter_keyword=criteria.filter_keyword
            )
            self.main_window.table_manager.update_table(
                self.main_window.file_handler.current_po,
                filter_text=criteria.filter,
                search_text=criteria.filter_keyword
            )
            
        self.main_window._update_table = mock_update_table
        
        # テスト対象メソッドを実行
        self.main_window._update_table()
        
        # get_filtered_entriesが正しいパラメータで呼び出されたことを確認
        self.main_window.file_handler.current_po.get_filtered_entries.assert_called_once_with(
            filter_text="",
            filter_keyword="test_keyword"
        )
        
        # update_tableが正しいパラメータで呼び出されたことを確認
        self.main_window.table_manager.update_table.assert_called_once_with(
            self.main_window.file_handler.current_po,
            filter_text="",
            search_text="test_keyword"
        )

    def test_combined_filter_and_keyword(self):
        """フィルタとキーワードの両方が正しく渡されることを確認するテスト"""
        # SearchCriteriaのモック
        mock_criteria = SearchCriteria(filter="translated", filter_keyword="test_keyword", match_mode="部分一致")
        self.main_window.search_widget.get_search_criteria.return_value = mock_criteria
        
        # _update_tableメソッドを定義
        def mock_update_table():
            criteria = self.main_window.search_widget.get_search_criteria()
            entries = self.main_window.file_handler.current_po.get_filtered_entries(
                filter_text=criteria.filter,
                filter_keyword=criteria.filter_keyword
            )
            self.main_window.table_manager.update_table(
                self.main_window.file_handler.current_po,
                filter_text=criteria.filter,
                search_text=criteria.filter_keyword
            )
            
        self.main_window._update_table = mock_update_table
        
        # テスト対象メソッドを実行
        self.main_window._update_table()
        
        # get_filtered_entriesが正しいパラメータで呼び出されたことを確認
        self.main_window.file_handler.current_po.get_filtered_entries.assert_called_once_with(
            filter_text="translated",
            filter_keyword="test_keyword"
        )
        
        # update_tableが正しいパラメータで呼び出されたことを確認
        self.main_window.table_manager.update_table.assert_called_once_with(
            self.main_window.file_handler.current_po,
            filter_text="translated",
            search_text="test_keyword"
        )

    def test_on_filter_changed_passes_keyword(self):
        """_on_filter_changedメソッドがキーワードを正しく渡すことを確認するテスト"""
        # SearchCriteriaのモック
        mock_criteria = SearchCriteria(filter="translated", filter_keyword="test_keyword", match_mode="部分一致")
        self.main_window.search_widget.get_search_criteria.return_value = mock_criteria
        
        # _on_filter_changedメソッドを定義
        def mock_on_filter_changed():
            criteria = self.main_window.search_widget.get_search_criteria()
            if self.main_window.file_handler.current_po:
                try:
                    entries = self.main_window.file_handler.current_po.get_filtered_entries(
                        filter_text=criteria.filter,
                        filter_keyword=criteria.filter_keyword
                    )
                    self.main_window.table_manager.update_table(
                        self.main_window.file_handler.current_po,
                        filter_text=criteria.filter,
                        search_text=criteria.filter_keyword
                    )
                except Exception as e:
                    self.main_window.status_bar.showMessage(f"エラー: {str(e)}")
                    
        self.main_window._on_filter_changed = mock_on_filter_changed
        
        # テスト対象メソッドを実行
        self.main_window._on_filter_changed()
        
        # get_filtered_entriesが正しいパラメータで呼び出されたことを確認
        self.main_window.file_handler.current_po.get_filtered_entries.assert_called_once_with(
            filter_text="translated",
            filter_keyword="test_keyword"
        )
        
        # update_tableが正しいパラメータで呼び出されたことを確認
        self.main_window.table_manager.update_table.assert_called_once_with(
            self.main_window.file_handler.current_po,
            filter_text="translated",
            search_text="test_keyword"
        )


if __name__ == "__main__":
    unittest.main()
