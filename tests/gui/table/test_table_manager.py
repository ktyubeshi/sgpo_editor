"""Table Manager Tests

This module contains tests for the TableManager class.
"""

import json
import sys
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
)

from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.core.cache_manager import EntryCacheManager

# QApplication インスタンスを作成（テスト用）
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestTableManager:
    """TableManager class tests"""

    def setup_method(self):
        """各テストメソッド実行前の準備"""
        self.table = QTableWidget()
        # EntryCacheManager のモックを作成して渡す
        self.mock_cache_manager = MagicMock(spec=EntryCacheManager)
        self.table_manager = TableManager(self.table, self.mock_cache_manager)

        # テスト用に列幅を明示的に設定
        for i in range(6):
            self.table.setColumnWidth(i, 100)

    def test_initialization(self):
        """初期化のテスト"""
        # 列数が正しく設定されているか
        assert self.table.columnCount() == 6

        # ヘッダーラベルが正しく設定されているか
        expected_headers = [
            "Entry Number",
            "msgctxt",
            "msgid",
            "msgstr",
            "Status",
            "Score",
        ]
        for i, expected in enumerate(expected_headers):
            assert self.table.horizontalHeaderItem(i).text() == expected

        # デフォルト列幅の長さが列数と一致しているか確認
        assert (
            len(self.table_manager._default_column_widths) == self.table.columnCount()
        )

        # ResizeModeがInteractiveに設定されているか
        for i in range(6):
            assert (
                self.table.horizontalHeader().sectionResizeMode(i)
                == QHeaderView.ResizeMode.Interactive
            )

        # 選択モードが行単位になっているか確認
        assert (
            self.table.selectionBehavior()
            == QAbstractItemView.SelectionBehavior.SelectRows
        )

    @patch("sgpo_editor.gui.table_manager.QSettings")
    def test_save_column_widths(self, mock_settings):
        """列幅の保存機能のテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance

        # sectionResizedシグナルを一時的に切断して、自動保存を防止
        self.table.horizontalHeader().sectionResized.disconnect()

        # テーブルの列数を確認
        assert self.table.columnCount() == 6

        # 列幅の保存メソッドを呼び出す
        self.table_manager._save_column_widths()

        # QSettingsのsetValueが正しく呼び出されたか確認
        mock_settings_instance.setValue.assert_called_once()
        args = mock_settings_instance.setValue.call_args[0]
        assert args[0] == "column_widths"

        # 保存されたJSON文字列が有効な形式か確認
        saved_widths = json.loads(args[1])
        assert len(saved_widths) == 6

    @patch("sgpo_editor.gui.table_manager.QSettings")
    def test_load_column_widths(self, mock_settings):
        """列幅の読み込み機能のテスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance

        # テーブルの列数を確認
        assert self.table.columnCount() == 6

        # テスト用の保存済み列幅データを設定
        test_widths = {"0": 110, "1": 160, "2": 210, "3": 260, "4": 130, "5": 140}
        mock_settings_instance.value.return_value = json.dumps(test_widths)

        # 列幅の読み込みメソッドを呼び出す
        self.table_manager._load_column_widths()

        # QSettingsのvalueメソッドが呼び出されたか確認
        mock_settings_instance.value.assert_called_once_with("column_widths", "")

    @patch("sgpo_editor.gui.table_manager.QSettings")
    def test_apply_default_column_widths(self, mock_settings):
        """デフォルト列幅の適用テスト"""
        # モックの設定
        mock_settings_instance = MagicMock()
        mock_settings.return_value = mock_settings_instance
        mock_settings_instance.value.return_value = ""  # 保存されたデータなし

        # テーブルの列数を確認
        assert self.table.columnCount() == 6

        # デフォルト値を設定
        self.table_manager._default_column_widths = [90, 130, 180, 180, 110, 100]

        # デフォルト列幅を適用
        self.table_manager._apply_default_column_widths()

        # デフォルト列幅の長さが列数と一致しているか確認
        assert (
            len(self.table_manager._default_column_widths) == self.table.columnCount()
        )

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
