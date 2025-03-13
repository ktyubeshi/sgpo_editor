"""Table Manager Tests

This module contains tests for the TableManager class.
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


class TestTableManager:
    """TableManager class tests"""

    def setup_method(self):
        """各テストメソッド実行前の準備"""
        self.table = QTableWidget()
        self.table_manager = TableManager(self.table)

    def test_initialization(self):
        """初期化のテスト"""
        # 列数が正しく設定されているか
        assert self.table.columnCount() == 5

        # ヘッダーラベルが正しく設定されているか
        expected_headers = ["Entry Number", "msgctxt", "msgid", "msgstr", "Status"]
        for i, expected in enumerate(expected_headers):
            assert self.table.horizontalHeaderItem(i).text() == expected

        # 列幅が設定されているか（デフォルト値または保存された値）
        for i in range(5):
            assert self.table.columnWidth(i) > 0

        # ResizeModeがInteractiveに設定されているか
        for i in range(5):
            assert (
                self.table.horizontalHeader().sectionResizeMode(i)
                == QHeaderView.ResizeMode.Interactive
            )

    @patch("sgpo_editor.gui.table_manager.QSettings")
    def test_save_column_widths(self, mock_settings):
        """列幅の保存機能のテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance

        # sectionResizedシグナルを一時的に切断して、自動保存を防止
        self.table.horizontalHeader().sectionResized.disconnect()

        # テスト用の列幅を設定
        test_widths = [100, 150, 200, 250, 120]
        for i, width in enumerate(test_widths):
            self.table.setColumnWidth(i, width)

        # 列幅の保存メソッドを呼び出す
        self.table_manager._save_column_widths()

        # QSettingsのsetValueが正しく呼び出されたか確認
        mock_settings_instance.setValue.assert_called_once()
        args = mock_settings_instance.setValue.call_args[0]
        assert args[0] == "column_widths"
        
        # 保存されたJSON文字列をパースして内容を確認
        saved_widths = json.loads(args[1])
        for i, width in enumerate(test_widths):
            assert int(saved_widths[str(i)]) == width

    @patch("sgpo_editor.gui.table_manager.QSettings")
    def test_load_column_widths(self, mock_settings):
        """列幅の読み込み機能のテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        
        # テスト用の保存済み列幅データを設定
        test_widths = {"0": 110, "1": 160, "2": 210, "3": 260, "4": 130}
        mock_settings_instance.value.return_value = json.dumps(test_widths)
        
        # 列幅の読み込みメソッドを呼び出す
        self.table_manager._load_column_widths()
        
        # テーブルの列幅が正しく設定されたか確認
        for col_idx, width in test_widths.items():
            assert self.table.columnWidth(int(col_idx)) == width

    @patch("sgpo_editor.gui.table_manager.QSettings")
    def test_apply_default_column_widths(self, mock_settings):
        """デフォルト列幅の適用テスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        mock_settings_instance.value.return_value = ""  # 保存されたデータなし
        
        # デフォルト値を設定
        self.table_manager._default_column_widths = [90, 130, 180, 180, 110]
        
        # デフォルト列幅を適用
        self.table_manager._apply_default_column_widths()
        
        # テーブルの列幅がデフォルト値に設定されたか確認
        for i, width in enumerate(self.table_manager._default_column_widths):
            assert self.table.columnWidth(i) == width

    @patch("sgpo_editor.gui.table_manager.QSettings")
    def test_section_resized_event(self, mock_settings):
        """列幅変更イベントのテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        
        # sectionResizedシグナルを一時的に切断
        self.table.horizontalHeader().sectionResized.disconnect()
        
        # _save_column_widthsメソッドをモック化
        self.table_manager._save_column_widths = MagicMock()
        
        # 列幅変更イベントをシミュレート
        self.table_manager._on_section_resized(1, 100, 150)
        
        # _save_column_widthsが呼び出されたか確認
        self.table_manager._save_column_widths.assert_called_once()
