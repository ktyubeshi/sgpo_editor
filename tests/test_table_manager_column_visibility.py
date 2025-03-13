"""Table Manager Column Visibility Tests

This module contains tests for the column visibility functionality of the TableManager class.
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QHeaderView, QTableWidget

from sgpo_editor.gui.table_manager import TableManager

# QApplication インスタンスを作成（テスト用）
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestTableManagerColumnVisibility:
    """TableManager column visibility functionality tests"""

    def setup_method(self):
        """各テストメソッド実行前の準備"""
        self.table = QTableWidget()
        self.table_manager = TableManager(self.table)
        
        # テストのために列の表示/非表示状態を初期化
        self.table_manager._hidden_columns = set()
        for i in range(self.table_manager.get_column_count()):
            self.table.setColumnHidden(i, False)

    def test_column_visibility_initial_state(self):
        """列の表示/非表示の初期状態のテスト"""
        # 初期状態ではすべての列が表示されているはず
        for i in range(self.table_manager.get_column_count()):
            assert self.table_manager.is_column_visible(i) is True
            assert self.table.isColumnHidden(i) is False

    def test_toggle_column_visibility(self):
        """列の表示/非表示切り替え機能のテスト"""
        # 初期状態を確認
        column_index = 1  # msgctxt列
        assert self.table_manager.is_column_visible(column_index) is True
        assert not self.table.isColumnHidden(column_index)
        
        # 列を非表示にする
        self.table_manager.toggle_column_visibility(column_index)
        
        # 非表示になっているか確認
        assert self.table_manager.is_column_visible(column_index) is False
        assert self.table.isColumnHidden(column_index) is True
        
        # 再度トグルして表示に戻す
        self.table_manager.toggle_column_visibility(column_index)
        
        # 表示に戻っているか確認
        assert self.table_manager.is_column_visible(column_index) is True
        assert self.table.isColumnHidden(column_index) is False

    def test_multiple_column_visibility_toggle(self):
        """複数列の表示/非表示切り替えテスト"""
        # 初期状態を確認
        for i in range(self.table_manager.get_column_count()):
            assert self.table_manager.is_column_visible(i) is True
            assert not self.table.isColumnHidden(i)
            
        # 複数の列を非表示にする
        columns_to_hide = [1, 3]  # msgctxt列とmsgstr列
        
        for col in columns_to_hide:
            self.table_manager.toggle_column_visibility(col)
        
        # すべての列の状態を確認
        for i in range(self.table_manager.get_column_count()):
            if i in columns_to_hide:
                assert self.table_manager.is_column_visible(i) is False
                assert self.table.isColumnHidden(i) is True
            else:
                assert self.table_manager.is_column_visible(i) is True
                assert self.table.isColumnHidden(i) is False

    @patch('sgpo_editor.gui.table_manager.QSettings')
    def test_save_column_visibility(self, mock_settings):
        """列の表示/非表示設定の保存機能のテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        
        # 既存の非表示列をクリア
        self.table_manager._hidden_columns = set()
        
        # 初期状態を確認
        column_index = 2  # msgid列
        assert self.table_manager.is_column_visible(column_index) is True
        
        # 列を非表示にする
        self.table_manager.toggle_column_visibility(column_index)
        
        # 設定が保存されたか確認
        # 最後の呼び出しを確認
        mock_settings_instance.setValue.assert_called_with(
            "hidden_columns", json.dumps([column_index])
        )

    @patch('sgpo_editor.gui.table_manager.QSettings')
    def test_load_column_visibility(self, mock_settings):
        """列の表示/非表示設定の読み込み機能のテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        
        # 初期状態ではすべての列が表示されているように設定
        for i in range(self.table_manager.get_column_count()):
            self.table.setColumnHidden(i, False)
        self.table_manager._hidden_columns = set()
        
        # 保存されている非表示列の設定
        hidden_columns = [0, 4]  # Entry Number列とStatus列
        mock_settings_instance.value.return_value = json.dumps(hidden_columns)
        
        # 設定を読み込む
        self.table_manager._load_column_visibility()
        
        # 正しく列が非表示になっているか確認
        for i in range(self.table_manager.get_column_count()):
            if i in hidden_columns:
                assert self.table_manager.is_column_visible(i) is False
                assert self.table.isColumnHidden(i) is True
            else:
                assert self.table_manager.is_column_visible(i) is True
                assert not self.table.isColumnHidden(i)

    def test_get_column_name(self):
        """列名取得機能のテスト"""
        expected_names = [
            "Entry Number",
            "msgctxt",
            "msgid",
            "msgstr",
            "Status",
        ]
        
        for i, expected in enumerate(expected_names):
            assert self.table_manager.get_column_name(i) == expected
        
        # 範囲外のインデックスの場合は空文字列を返す
        assert self.table_manager.get_column_name(10) == ""

    def test_get_column_count(self):
        """列数取得機能のテスト"""
        assert self.table_manager.get_column_count() == 5

    @patch('sgpo_editor.gui.table_manager.QSettings')
    def test_load_column_visibility_with_invalid_data(self, mock_settings):
        """無効なデータでの列の表示/非表示設定の読み込み機能のテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        
        # 初期状態ではすべての列が表示されているように設定
        for i in range(self.table_manager.get_column_count()):
            self.table.setColumnHidden(i, False)
        self.table_manager._hidden_columns = set()
        
        # 無効なJSONデータ
        mock_settings_instance.value.return_value = "invalid json"
        
        # 設定を読み込む（例外が発生しないことを確認）
        self.table_manager._load_column_visibility()
        
        # すべての列が表示されていることを確認
        for i in range(self.table_manager.get_column_count()):
            assert self.table_manager.is_column_visible(i) is True
            # 列が非表示になっていないことを確認
            assert not self.table.isColumnHidden(i)
