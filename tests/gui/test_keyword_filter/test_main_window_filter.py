"""MainWindowのキーワードフィルタ処理に関するテスト

このテストでは、MainWindowのキーワードフィルタ処理が正しく動作するかを検証します。
特に、空文字列や空白文字列の処理に焦点を当てています。
"""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.widgets.search import SearchCriteria

# テスト用のQApplicationを作成
app = QApplication.instance()
if not app:
    app = QApplication([])


class TestMainWindowFilter:
    """MainWindowのキーワードフィルタ処理に関するテスト"""

    @pytest.fixture
    def setup_main_window(self):
        """MainWindowとモックを設定"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()

        # ViewerPOFileRefactoredをモック化
        mock_po_file = MagicMock(spec=ViewerPOFileRefactored)
        mock_po_file.get_filtered_entries.return_value = []
        mock_po_file.search_text = None
        mock_po_file.filter_text = ""
        mock_po_file.filtered_entries = []

        # _get_current_poメソッドをパッチしてモックを返すようにする
        main_window._get_current_po = MagicMock(return_value=mock_po_file)

        # テーブルマネージャのupdate_tableメソッドをモック化
        main_window.table_manager.update_table = MagicMock(return_value=[])

        # 検索ウィジェットのget_search_criteriaメソッドをモック化
        main_window.search_widget.get_search_criteria = MagicMock()

        yield main_window, mock_po_file

    def test_on_search_changed_with_none_keyword(self, setup_main_window):
        """キーワードがNoneの場合の_on_search_changedメソッドのテスト"""
        main_window, mock_po_file = setup_main_window

        # SearchCriteriaを設定
        criteria = SearchCriteria()
        criteria.filter_keyword = None
        # デフォルト値は filter="すべて", match_mode="部分一致"

        # get_search_criteriaの戻り値を設定
        main_window.search_widget.get_search_criteria.return_value = criteria

        # _on_search_changedメソッドを呼び出す代わりにシグナルを発行
        main_window.search_widget.filter_changed.emit()

        # update_tableが呼ばれたことを確認
        main_window.entry_list_facade.update_table.assert_called_once()

    def test_on_search_changed_with_empty_keyword(self, setup_main_window):
        """キーワードが空文字列の場合の_on_search_changedメソッドのテスト"""
        main_window, mock_po_file = setup_main_window

        # SearchCriteriaを設定
        criteria = SearchCriteria()
        criteria.filter_keyword = ""
        # デフォルト値は filter="すべて", match_mode="部分一致"

        # get_search_criteriaの戻り値を設定
        main_window.search_widget.get_search_criteria.return_value = criteria

        # _on_search_changedメソッドを呼び出す代わりにシグナルを発行
        main_window.search_widget.filter_changed.emit()

        # update_tableが呼ばれたことを確認
        main_window.entry_list_facade.update_table.assert_called_once()

    def test_on_search_changed_with_whitespace_keyword(self, setup_main_window):
        """キーワードが空白文字のみの場合の_on_search_changedメソッドのテスト"""
        main_window, mock_po_file = setup_main_window

        # SearchCriteriaを設定
        criteria = SearchCriteria()
        criteria.filter_keyword = "   "
        # デフォルト値は filter="すべて", match_mode="部分一致"

        # get_search_criteriaの戻り値を設定
        main_window.search_widget.get_search_criteria.return_value = criteria

        # _on_search_changedメソッドを呼び出す代わりにシグナルを発行
        main_window.search_widget.filter_changed.emit()

        # update_tableが呼ばれたことを確認
        main_window.entry_list_facade.update_table.assert_called_once()

    def test_on_search_changed_with_valid_keyword(self, setup_main_window):
        """有効なキーワードの場合の_on_search_changedメソッドのテスト"""
        main_window, mock_po_file = setup_main_window

        # SearchCriteriaを設定
        criteria = SearchCriteria()
        criteria.filter_keyword = "test"
        # デフォルト値は filter="すべて", match_mode="部分一致"

        # get_search_criteriaの戻り値を設定
        main_window.search_widget.get_search_criteria.return_value = criteria

        mock_entries = [MagicMock() for _ in range(5)]
        # entry_list_facade.update_table 内で呼ばれるメソッドをモック
        main_window.entry_list_facade._get_current_po.return_value.get_filtered_entries.return_value = mock_entries

        # _on_search_changedメソッドを呼び出す代わりにシグナルを発行
        main_window.search_widget.filter_changed.emit()

        # update_tableが呼ばれたことを確認
        main_window.entry_list_facade.update_table.assert_called_once()
        # update_table内でget_filtered_entriesが呼ばれたことを確認
        main_window.entry_list_facade._get_current_po.return_value.get_filtered_entries.assert_called_with(
            criteria
        )
