"""Table Update Issue Test

このモジュールはテーブル更新時の表示に関する問題を特定するためのテストを含みます。
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QTableWidget

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.models.entry import EntryModel

# QApplication インスタンスを作成（テスト用）
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestTableUpdateIssue:
    """テーブル更新時の表示問題テスト"""

    def setup_method(self):
        """各テストメソッド実行前の準備"""
        self.table = QTableWidget()
        self.table.setRowCount(1)
        self.table.setColumnCount(6)
        self.mock_cache_manager = MagicMock(spec=EntryCacheManager)
        self.table_manager = TableManager(self.table, self.mock_cache_manager)

        # テスト用にモックエントリを作成
        self.mock_entry = MagicMock()
        self.mock_entry.position = 0
        self.mock_entry.key = "entry1"
        self.mock_entry.msgctxt = "context1"
        self.mock_entry.msgid = "source1"
        self.mock_entry.msgstr = "target1"
        self.mock_entry.get_status.return_value = "翻訳済み"
        self.mock_entry.overall_quality_score.return_value = 85

    def test_column_visibility_after_update(self):
        """テーブル更新後の列表示状態テスト"""
        # 初期状態ではすべての列が表示されているはず
        for i in range(self.table_manager.get_column_count()):
            self.table.setColumnHidden(i, False)
        self.table_manager._hidden_columns = set()

        # 一部の列を非表示に設定
        columns_to_hide = [1, 3]  # msgctxt列とmsgstr列
        for col in columns_to_hide:
            self.table_manager.toggle_column_visibility(col)

        # この時点で特定の列が非表示になっているはず
        for i in range(self.table_manager.get_column_count()):
            expected_hidden = i in columns_to_hide
            assert self.table.isColumnHidden(i) == expected_hidden

        # テーブル更新
        with patch("sgpo_editor.gui.table_manager.logger"):
            self.table_manager._update_table_contents([self.mock_entry])

        # 更新後も列の表示/非表示状態が維持されているか確認
        for i in range(self.table_manager.get_column_count()):
            expected_hidden = i in columns_to_hide
            assert self.table.isColumnHidden(i) == expected_hidden, (
                f"Column {i} visibility state is incorrect."
            )

        # エントリが正しくテーブルに表示されているか確認
        assert self.table.rowCount() == 1
        assert self.table.item(0, 0).text() == "1"  # Entry Number
        assert self.table.item(0, 2).text() == "source1"  # msgid
        assert self.table.item(0, 4).text() == "翻訳済み"  # Status

    def test_table_contents_after_visibility_toggle(self):
        """列表示切り替え後のテーブル内容テスト"""
        # テーブルにデータを設定
        with patch("sgpo_editor.gui.table_manager.logger"):
            self.table_manager._update_table_contents([self.mock_entry])

        # 初期状態を確認
        assert self.table.rowCount() == 1
        assert self.table.item(0, 0).text() == "1"

        # 列を切り替えてもデータは維持されるはず
        column_to_toggle = 2  # msgid列
        self.table_manager.toggle_column_visibility(column_to_toggle)

        # データの確認
        assert self.table.rowCount() == 1
        assert self.table.item(0, 0).text() == "1"
        assert self.table.item(0, 4).text() == "翻訳済み"
