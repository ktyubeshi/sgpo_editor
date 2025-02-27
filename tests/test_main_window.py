#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations
from typing import Any, cast, Optional

from unittest.mock import MagicMock, patch, call
import unittest
import sys

# モックの設定をテスト実行より先に行うため、importより前に実施
# QApplicationのモック
mock_qapp = MagicMock()
mock_qapp.instance = MagicMock(return_value=mock_qapp)
mock_qapp.exec = MagicMock(return_value=0)

# QtWidgetsのモック化
mock_qt_widgets = MagicMock()
mock_qt_widgets.QApplication = mock_qapp
mock_qt_widgets.QMainWindow = MagicMock()
mock_qt_widgets.QWidget = MagicMock()
mock_qt_widgets.QTableWidget = MagicMock()
mock_qt_widgets.QTableWidgetItem = MagicMock()
mock_qt_widgets.QMessageBox = MagicMock()
mock_qt_widgets.QDialog = MagicMock()
mock_qt_widgets.QFileDialog = MagicMock()
mock_qt_widgets.QMenu = MagicMock()
sys.modules['PySide6.QtWidgets'] = mock_qt_widgets

# QtCoreのモック化
mock_qt_core = MagicMock()
mock_qt_core.Qt = MagicMock()
mock_qt_core.QEvent = MagicMock()
sys.modules['PySide6.QtCore'] = mock_qt_core

# QtGuiのモック化
mock_qt_gui = MagicMock()
mock_qt_gui.QAction = MagicMock()
sys.modules['PySide6.QtGui'] = mock_qt_gui

# モック化された子コンポーネント
mock_entry_editor = MagicMock()
mock_stats_widget = MagicMock()
mock_search_widget = MagicMock()
mock_table_manager = MagicMock()
mock_file_handler = MagicMock()
mock_event_handler = MagicMock()
mock_ui_manager = MagicMock()

# 依存モジュールのモック化
sys.modules['sgpo_editor.gui.widgets.entry_editor'] = MagicMock()
sys.modules['sgpo_editor.gui.widgets.entry_editor'].EntryEditor = MagicMock(return_value=mock_entry_editor)
sys.modules['sgpo_editor.gui.widgets.entry_editor'].LayoutType = MagicMock()

sys.modules['sgpo_editor.gui.widgets.stats'] = MagicMock()
sys.modules['sgpo_editor.gui.widgets.stats'].StatsWidget = MagicMock(return_value=mock_stats_widget)

sys.modules['sgpo_editor.gui.widgets.search'] = MagicMock()
sys.modules['sgpo_editor.gui.widgets.search'].SearchWidget = MagicMock(return_value=mock_search_widget)
sys.modules['sgpo_editor.gui.widgets.search'].SearchCriteria = MagicMock()

sys.modules['sgpo_editor.gui.table_manager'] = MagicMock()
sys.modules['sgpo_editor.gui.table_manager'].TableManager = MagicMock(return_value=mock_table_manager)

sys.modules['sgpo_editor.gui.file_handler'] = MagicMock()
sys.modules['sgpo_editor.gui.file_handler'].FileHandler = MagicMock(return_value=mock_file_handler)

sys.modules['sgpo_editor.gui.event_handler'] = MagicMock()
sys.modules['sgpo_editor.gui.event_handler'].EventHandler = MagicMock(return_value=mock_event_handler)

sys.modules['sgpo_editor.gui.ui_setup'] = MagicMock()
sys.modules['sgpo_editor.gui.ui_setup'].UIManager = MagicMock(return_value=mock_ui_manager)

sys.modules['sgpo_editor.core.viewer_po_file'] = MagicMock()
sys.modules['sgpo_editor.core.viewer_po_file'].ViewerPOFile = MagicMock()

sys.modules['sgpo_editor.gui.models.entry'] = MagicMock()
sys.modules['sgpo_editor.gui.models.entry'].EntryModel = MagicMock()

# モックの設定後にインポート
from PySide6.QtWidgets import QTableWidgetItem, QApplication, QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.models.entry import EntryModel
from pathlib import Path
import logging
from sgpo_editor.gui.widgets.search import SearchCriteria
from sgpo_editor.gui.widgets.entry_editor import LayoutType

# MainWindowクラスのオーバーライド
class MockMainWindow(MainWindow):
    def __init__(self) -> None:
        # 親クラスの__init__は呼び出さず、必要なプロパティを直接設定
        self.current_po = None
        self.entry_editor = mock_entry_editor
        self.stats_widget = mock_stats_widget
        self.search_widget = mock_search_widget
        self.table = MagicMock()
        self.table_manager = mock_table_manager
        self.file_handler = mock_file_handler
        self.event_handler = mock_event_handler
        self.ui_manager = mock_ui_manager

class TestMainWindow(unittest.TestCase):
    """メインウィンドウのテスト"""

    def setUp(self) -> None:
        """テストの前準備"""
        # モック化されたMainWindowを使用
        self.main_window = MockMainWindow()
        # StatsWidgetのメソッドをモック
        self.main_window.stats_widget.update_stats = MagicMock()

    def tearDown(self) -> None:
        """テスト後の後処理"""
        # モックの後処理は特に必要なし
        pass

    def test_initial_state(self) -> None:
        """初期状態のテスト"""
        self.assertIsNone(self.main_window.current_po)
        self.assertIsNotNone(self.main_window.entry_editor)
        self.assertIsNotNone(self.main_window.stats_widget)
        self.assertIsNotNone(self.main_window.search_widget)
        self.assertIsNotNone(self.main_window.table)

    @patch("sgpo_editor.gui.main_window.QFileDialog.getOpenFileName", return_value=("test.po", ""))
    @patch("sgpo_editor.gui.main_window.ViewerPOFile")
    def test_open_file_success(self, mock_viewer_po_file: Any, mock_get_open_file_name: Any) -> None:
        """ファイルを開くテスト（成功）"""
        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria = MagicMock(return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致"))

        # StatsWidgetのメソッドをモック
        self.main_window.stats_widget.update_stats = MagicMock()

        mock_viewer_po_file.return_value.get_entries.return_value = []
        mock_viewer_po_file.return_value.get_stats.return_value = {}
        mock_viewer_po_file.return_value.load = MagicMock()

        self.main_window._open_file()

        mock_viewer_po_file.assert_called_once()
        self.assertIsInstance(self.main_window.current_po, MagicMock)
        self.assertEqual(self.main_window.windowTitle(), "PO Viewer - test.po")
        self.assertEqual(self.main_window.table.rowCount(), 0)

    @patch("sgpo_editor.gui.main_window.QFileDialog.getSaveFileName", return_value=("test_save.po", ""))
    @patch("sgpo_editor.gui.main_window.ViewerPOFile")
    def test_save_file_as_success(self, mock_viewer_po_file: Any, mock_get_save_file_name: Any) -> None:
        """名前を付けて保存のテスト（成功）"""
        self.main_window.current_po = mock_viewer_po_file.return_value
        mock_viewer_po_file.return_value.save = MagicMock()

        # ステータスバーのモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        self.main_window._save_file_as()

        mock_status_bar.showMessage.assert_called_with("保存しました", 3000)

    def test_update_table_no_po_file(self) -> None:
        """POファイルがない場合のテスト"""
        self.main_window.current_po = None
        self.main_window._update_table()
        self.assertEqual(self.main_window.table.rowCount(), 0)

    @patch("sgpo_editor.gui.main_window.ViewerPOFile")
    def test_update_table_with_entries(self, mock_viewer_po_file: Any) -> None:
        """エントリがある場合のテスト"""
        # SearchWidgetのメソッドをモック（get_search_criteriaに統一）
        self.main_window.search_widget.get_search_criteria = MagicMock(return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致"))

        # テスト用のエントリを作成
        mock_entry = EntryModel(
            msgid="test_msgid",
            msgstr="test_msgstr"
        )

        # ViewerPOFileのモックを設定
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_filtered_entries.return_value = [mock_entry]

        # テスト実行
        self.main_window._update_table()

        # 検証
        self.assertEqual(self.main_window.table.rowCount(), 1)
        item0 = self.main_window.table.item(0, 0)
        self.assertIsNotNone(item0, "エントリ番号が表示されていません")
        item0 = cast(QTableWidgetItem, item0)
        self.assertEqual(item0.data(Qt.ItemDataRole.UserRole), mock_entry.key)
        self.assertEqual(item0.text(), "1")

    @patch("sgpo_editor.gui.main_window.ViewerPOFile")
    def test_on_selection_changed_no_item(self, mock_viewer_po_file: Any) -> None:
        """選択なしの場合のテスト"""
        self.main_window.entry_editor.set_entry = MagicMock()
        mock_viewer_po_file.return_value.get_entries.return_value = []
        self.main_window.current_po = mock_viewer_po_file.return_value

        self.main_window._on_selection_changed()

        self.main_window.entry_editor.set_entry.assert_called_with(None)

    @patch("sgpo_editor.gui.main_window.ViewerPOFile")
    def test_on_selection_changed_with_item(self, mock_viewer_po_file: Any) -> None:
        """選択ありの場合のテスト"""
        self.main_window.entry_editor.set_entry = MagicMock()

        # テスト用のエントリを作成
        mock_entry = EntryModel(
            msgid="test",
            msgstr="テスト"
        )

        # テーブルアイテムを設定
        item = QTableWidgetItem("test_item")
        item.setData(Qt.ItemDataRole.UserRole, mock_entry.key)
        self.main_window.table.setRowCount(1)
        self.main_window.table.setItem(0, 0, item)
        self.main_window.table.selectRow(0)

        # ViewerPOFileのモックを設定
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_entry_by_key.return_value = mock_entry

        # テスト実行
        self.main_window._on_selection_changed()

        # 検証
        self.main_window.current_po.get_entry_by_key.assert_called_with(mock_entry.key)
        self.main_window.entry_editor.set_entry.assert_called_with(mock_entry)

    def test_save_dock_states(self) -> None:
        """ドック状態の保存テスト"""
        with patch("sgpo_editor.gui.main_window.QSettings") as mock_settings:
            mock_instance = mock_settings.return_value
            self.main_window.saveGeometry = MagicMock(return_value=b"geometry")
            self.main_window.saveState = MagicMock(return_value=b"state")

            self.main_window._save_dock_states()

            mock_instance.setValue.assert_any_call("dock_states", b"state")

    def test_restore_dock_states(self) -> None:
        """ドック状態の復元テスト"""
        with patch("sgpo_editor.gui.main_window.QSettings") as mock_settings:
            mock_instance = mock_settings.return_value
            mock_instance.value.side_effect = [b"test_data", b"test_data"]

            self.main_window.restoreGeometry = MagicMock()
            self.main_window.restoreState = MagicMock()

            self.main_window._restore_dock_states()

            mock_instance.value.assert_has_calls([
                unittest.mock.call("dock_states"),
            ])
            self.main_window.restoreGeometry.assert_called_once_with(b"test_data")
            self.main_window.restoreState.assert_called_once_with(b"test_data")

    def test_entry_text_changed(self) -> None:
        """エントリテキスト変更時の処理のテスト"""
        # エントリを設定
        mock_entry = EntryModel(msgid="test", msgstr="テスト")
        self.main_window._display_entries = [mock_entry.key]
        self.main_window.entry_editor.set_entry(mock_entry)

        # ウィンドウタイトルをモック
        self.main_window.entry_editor_dock.windowTitle = MagicMock(return_value="エントリ編集 - #1")
        self.main_window.entry_editor_dock.setWindowTitle = MagicMock()

        # テキスト変更シグナルのハンドラを直接呼び出し
        self.main_window._on_entry_text_changed()

        # 検証
        self.main_window.entry_editor_dock.setWindowTitle.assert_called_with("エントリ編集 - #1*")

    def test_apply_clicked(self) -> None:
        """適用ボタンクリック時の処理のテスト"""
        # エントリを設定
        mock_entry = EntryModel(msgid="test", msgstr="テスト")
        self.main_window._display_entries = [mock_entry.key]
        self.main_window.entry_editor.set_entry(mock_entry)

        # ウィンドウタイトルをモック
        self.main_window.entry_editor_dock.windowTitle = MagicMock(return_value="エントリ編集 - #1*")
        self.main_window.entry_editor_dock.setWindowTitle = MagicMock()

        # Applyボタンクリックのハンドラを直接呼び出し
        self.main_window._on_apply_clicked()

        # 検証
        self.main_window.entry_editor_dock.setWindowTitle.assert_called_with("エントリ編集 - #1")

    def test_search_filter(self) -> None:
        """検索/フィルタリング機能のテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entry = MagicMock(
            key="key1",
            position=1,
            msgid="test_entry",
            msgstr="テストエントリ",
            flags=[]
        )
        mock_po.get_filtered_entries.return_value = [mock_entry]
        self.main_window.file_handler.current_po = mock_po

        # 検索条件を設定
        search_criteria = SearchCriteria(
            filter="test_filter",
            search_text="test_search",
            match_mode="部分一致"
        )
        self.main_window.search_widget.get_search_criteria = MagicMock(
            return_value=search_criteria
        )

        # テスト実行
        self.main_window.table_manager.update_table(mock_po)

        # 検証
        # 1. フィルタリング条件が正しく渡されることを確認
        mock_po.get_filtered_entries.assert_called_with(
            filter_text="test_filter",
            search_text="test_search",
            sort_column=None,
            sort_order=None
        )

        # 2. テーブルが更新されることを確認
        self.assertEqual(self.main_window.table.rowCount(), 1)
        item = self.main_window.table.item(0, 2)  # msgid列
        self.assertIsNotNone(item)
        self.assertEqual(item.text(), "test_entry")

    def test_table_sorting(self) -> None:
        """テーブルのソート機能テスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            MagicMock(key=f"key{i}", position=i, 
                     msgid=f"test{3-i}", msgstr=f"テスト{3-i}", 
                     flags=[], msgctxt=None)
            for i in range(3)
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        self.main_window.file_handler.current_po = mock_po

        # テーブルを初期化
        self.main_window.table_manager.update_table(mock_po)

        # 初期状態の確認（エントリ番号でソート）
        self.assertEqual(self.main_window.table_manager._current_sort_column, 0)
        self.assertEqual(self.main_window.table_manager._current_sort_order, Qt.SortOrder.AscendingOrder)

        # msgid列（2列目）でソート
        self.main_window.table_manager._on_header_clicked(2)

        # ソートインジケータの確認
        self.assertEqual(self.main_window.table_manager._current_sort_column, 2)
        self.assertEqual(self.main_window.table_manager._current_sort_order, Qt.SortOrder.AscendingOrder)

        # 同じ列をもう一度クリックして降順に変更
        self.main_window.table_manager._on_header_clicked(2)
        self.assertEqual(self.main_window.table_manager._current_sort_order, Qt.SortOrder.DescendingOrder)

        # テーブルの内容を確認
        for i in range(3):
            item = self.main_window.table.item(i, 2)  # msgid列
            self.assertIsNotNone(item)
            # 降順なので、大きい数字から順に並ぶ
            self.assertEqual(item.text(), f"test{i}")

    @patch("sgpo_editor.gui.main_window.ViewerPOFile")
    def test_error_handling(self, mock_viewer_po_file: Any) -> None:
        """エラー処理のテスト"""
        # エラーを発生させる
        mock_viewer_po_file.return_value.get_filtered_entries.side_effect = Exception("Test error")
        self.main_window.current_po = mock_viewer_po_file.return_value

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        self.main_window._update_table()

        # エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with(
            "テーブルの更新でエラー: Test error",
            3000
        )

    def test_save_file_error(self) -> None:
        """ファイル保存エラーのテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po.file_path = Path("test.po")  # file_pathプロパティを追加
        mock_po.save.side_effect = Exception("保存に失敗しました")
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        with self.assertRaises(Exception):
            self.main_window._save_file()

        # エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with("保存に失敗しました", 3000)


    def test_entry_navigation(self) -> None:
        """エントリナビゲーションのテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            EntryModel(msgid=f"test{i}", msgstr=f"テスト{i}")
            for i in range(3)
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        mock_po.get_entry_by_key.side_effect = mock_entries  # 異なるエントリを返すように設定
        self.main_window.current_po = mock_po

        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria = MagicMock(return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致"))

        # テーブルを更新
        self.main_window._update_table()

        # 最初のエントリを選択
        self.main_window.table.selectRow(0)
        first_entry = mock_entries[0]
        self.assertIsNotNone(first_entry)

        # 次のエントリに移動
        self.main_window.next_entry()
        self.assertEqual(self.main_window.table.currentRow(), 1)

        # 前のエントリに移動
        self.main_window.previous_entry()
        self.assertEqual(self.main_window.table.currentRow(), 0)

        # 最後のエントリに移動
        self.main_window.last_entry()
        self.assertEqual(self.main_window.table.currentRow(), 2)

        # 最初のエントリに移動
        self.main_window.first_entry()
        self.assertEqual(self.main_window.table.currentRow(), 0)

    def test_entry_editor_text_change(self) -> None:
        """エントリエディタのテキスト変更テスト"""
        # エントリを設定
        mock_entry = EntryModel(msgid="test", msgstr="テスト")
        self.main_window._display_entries = [mock_entry.key]
        self.main_window.entry_editor.set_entry(mock_entry)

        # ウィンドウタイトルをモック
        self.main_window.entry_editor_dock.windowTitle = MagicMock(return_value="エントリ編集 - #1")
        self.main_window.entry_editor_dock.setWindowTitle = MagicMock()

        # テキスト変更シグナルのハンドラを直接呼び出し
        self.main_window._on_entry_text_changed()

        # 検証
        self.main_window.entry_editor_dock.setWindowTitle.assert_called_with("エントリ編集 - #1*")

    def test_table_update_error(self) -> None:
        """テーブル更新エラーのテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po.get_filtered_entries.side_effect = TypeError("unsupported operand type(s) for +: 'dict' and 'int'")
        self.main_window.file_handler.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テーブルの初期状態を記録
        initial_row_count = self.main_window.table.rowCount()

        # テスト実行
        self.main_window.table_manager.update_table(mock_po)

        # 検証
        # 1. エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with(
            "テーブルの更新でエラー: unsupported operand type(s) for +: 'dict' and 'int'",
            3000
        )

        # 2. テーブルが空の状態になっていることを確認
        self.assertEqual(self.main_window.table.rowCount(), 0)

        # 3. テーブルマネージャの内部状態が正しいことを確認
        self.assertEqual(len(self.main_window.table_manager._display_entries), 0)
        self.assertEqual(len(self.main_window.table_manager._entry_cache), 0)

    def test_navigation(self) -> None:
        """ナビゲーション機能のテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            EntryModel(msgid=f"test{i}", msgstr=f"テスト{i}")
            for i in range(3)
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        self.main_window.current_po = mock_po

        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria = MagicMock(return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致"))

        # テーブルを更新
        self.main_window._update_table()

        # 最初のエントリを選択
        self.main_window.table.selectRow(0)

        # 次のエントリに移動
        self.main_window.next_entry()
        self.assertEqual(self.main_window.table.currentRow(), 1)

        # 前のエントリに移動
        self.main_window.previous_entry()
        self.assertEqual(self.main_window.table.currentRow(), 0)

        # 最後のエントリに移動
        self.main_window.last_entry()
        self.assertEqual(self.main_window.table.currentRow(), 2)

        # 最初のエントリに移動
        self.main_window.first_entry()
        self.assertEqual(self.main_window.table.currentRow(), 0)

    def test_navigation_error(self) -> None:
        """ナビゲーションエラー処理のテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            MagicMock(key="key1", position=1, msgid="test1", msgstr="テスト1", flags=[])
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        self.main_window.file_handler.current_po = mock_po

        # テーブルを更新
        self.main_window.table_manager.update_table(mock_po)

        # 1. 範囲外の行選択
        self.main_window.table.selectRow(100)  # 存在しない行
        self.assertEqual(self.main_window.table.currentRow(), -1)  # 選択が無効になる

        # 2. 有効な行を選択
        self.main_window.table.selectRow(0)
        self.assertEqual(self.main_window.table.currentRow(), 0)

        # 3. 無効な型の行番号での選択
        # selectRowは整数以外を受け付けないため、直接内部メソッドをテスト
        self.main_window.table.setCurrentCell("invalid", 0)  # 型エラーが発生するはず
        self.assertEqual(self.main_window.table.currentRow(), 0)  # 前の有効な選択が維持される

    def test_file_operations(self) -> None:
        """ファイル操作のテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po.path = Path("test.po")
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # 保存のテスト
        self.main_window._save_file()
        mock_po.save.assert_called_once()
        mock_status_bar.showMessage.assert_called_with("ファイルを保存しました", 5000)

    def test_file_operations_error(self) -> None:
        """ファイル操作エラーのテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po.file_path = None
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # 保存のテスト（名前を付けて保存にリダイレクト）
        with patch("sgpo_editor.gui.main_window.QFileDialog.getSaveFileName", return_value=("", "")):
            self.main_window._save_file()
            mock_po.save.assert_not_called()

    def test_close_event(self) -> None:
        """ウィンドウを閉じる際の処理のテスト"""
        # QEventをモック
        mock_event = MagicMock()
        mock_event.accept = MagicMock()

        # ドック状態の保存をモック
        self.main_window._save_dock_states = MagicMock()

        # テスト実行
        self.main_window.closeEvent(mock_event)

        # 検証
        self.main_window._save_dock_states.assert_called_once()
        mock_event.accept.assert_called_once()

    def test_show_current_entry_invalid_state(self) -> None:
        """無効な状態での現在のエントリ表示テスト"""
        # 無効な状態を設定
        self.main_window.file_handler.current_po = None

        # エントリエディタのモック
        self.main_window.entry_editor.set_entry = MagicMock()

        # テスト実行
        self.main_window.event_handler._update_detail_view(100)  # 無効な行番号

        # 検証
        self.main_window.entry_editor.set_entry.assert_called_once_with(None)

        # 範囲外の行番号でもエラーが発生しないことを確認
        self.main_window.event_handler._update_detail_view(-1)  # 負の行番号
        self.assertEqual(self.main_window.entry_editor.set_entry.call_count, 2)

    def test_table_progress_tracking(self) -> None:
        """テーブルの進捗状態追跡テスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            MagicMock(key="key1", position=1, msgid="test1", msgstr="テスト1", flags=[]),
            MagicMock(key="key2", position=2, msgid="test2", msgstr="テスト2", flags=[]),
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        self.main_window.file_handler.current_po = mock_po

        # テーブルを更新
        self.main_window.table_manager.update_table(mock_po)

        # 総エントリ数の検証
        self.assertEqual(self.main_window.table.rowCount(), 2)

        # 選択行の検証（デフォルトは未選択）
        self.assertEqual(self.main_window.table.currentRow(), -1)

        # 行を選択
        self.main_window.table.selectRow(0)
        self.assertEqual(self.main_window.table.currentRow(), 0)

        # 無効な行の選択を試みる
        self.main_window.table.selectRow(100)  # 範囲外の行
        # 選択は変更されないはず
        self.assertEqual(self.main_window.table.currentRow(), 0)

    def test_table_entry_count_validation(self) -> None:
        """テーブルのエントリ数検証テスト"""
        # 空のPOファイルでの検証
        self.main_window.file_handler.current_po = None
        self.main_window.table_manager.update_table(None)
        self.assertEqual(self.main_window.table.rowCount(), 0)
        self.assertEqual(len(self.main_window.table_manager._display_entries), 0)

        # 無効なエントリを含むPOファイルでの検証
        mock_po = MagicMock()
        mock_entries = [
            MagicMock(key=None, position=None, msgid=None, msgstr=None, flags=[]),  # 無効なエントリ
            MagicMock(key="key1", position=1, msgid="test1", msgstr="テスト1", flags=[]),  # 有効なエントリ
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        self.main_window.file_handler.current_po = mock_po

        # テーブル更新時に無効なエントリが適切に処理されることを確認
        self.main_window.table_manager.update_table(mock_po)
        # 有効なエントリのみがカウントされることを確認
        self.assertEqual(self.main_window.table.rowCount(), 2)  # 無効なエントリも表示はされる
        self.assertEqual(len(self.main_window.table_manager._display_entries), 2)

    def test_entry_changed_no_number(self) -> None:
        """エントリ番号なしでのエントリ変更テスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            MagicMock(key="key1", position=1, msgid="test1", msgstr="テスト1", flags=[])
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        self.main_window.file_handler.current_po = mock_po

        # テーブルを更新
        self.main_window.table_manager.update_table(mock_po)

        # エントリエディタのタイトルをモック
        self.main_window.entry_editor_dock.setWindowTitle = MagicMock()

        # 無効なエントリ番号でイベントを発生
        self.main_window.event_handler._on_entry_changed(-1)

        # 検証
        self.main_window.entry_editor_dock.setWindowTitle.assert_called_with("エントリ編集")
        self.assertEqual(self.main_window.table.currentRow(), -1)  # 選択が解除されていることを確認

    def test_table_update_error_with_invalid_entry(self) -> None:
        """無効なエントリでのテーブル更新エラーテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entry = MagicMock(spec=['msgid', 'msgstr', 'position', 'key', 'flags'])
        mock_entry.msgid = None  # 無効なmsgidを設定
        mock_entry.msgstr = None  # 無効なmsgstrを設定
        mock_entry.position = None  # 無効なpositionを設定
        mock_entry.key = None
        mock_entry.flags = []
        mock_po.get_filtered_entries.return_value = [mock_entry]
        self.main_window.file_handler.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テーブルの初期状態を記録
        initial_row_count = self.main_window.table.rowCount()

        # テスト実行
        self.main_window.table_manager.update_table(mock_po)

        # 検証
        # 1. エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_any_call(
            "テーブルの更新でエラー: 'NoneType' object has no attribute 'key'",
            3000
        )

        # 2. テーブルが空の状態になっていることを確認
        self.assertEqual(self.main_window.table.rowCount(), 0)

        # 3. テーブルマネージャの内部状態が正しいことを確認
        self.assertEqual(len(self.main_window.table_manager._display_entries), 0)
        self.assertEqual(len(self.main_window.table_manager._entry_cache), 0)

    def test_save_file_with_path_attribute(self) -> None:
        """POファイルのパス属性アクセスのテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po._path = Path("test.po")
        mock_po.path = property(lambda self: self._path)  # pathプロパティを追加
        self.main_window.file_handler.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        self.main_window.file_handler.save_file()

        # 検証
        mock_po.save.assert_called_once()
        mock_status_bar.showMessage.assert_called_with("ファイルを保存しました", 5000)

    def test_save_file_without_path_attribute(self) -> None:
        """POファイルのパス属性がない場合のテスト"""
        # POファイルをモック（pathプロパティなし）
        mock_po = MagicMock()
        mock_po.path = None
        self.main_window.file_handler.current_po = mock_po

        # FileHandlerのメソッドをモック
        self.main_window.file_handler.save_file_as = MagicMock()

        # テスト実行
        self.main_window.file_handler.save_file()

        # 名前を付けて保存が呼ばれることを確認
        self.main_window.file_handler.save_file_as.assert_called_once()

    def test_save_file_with_error(self) -> None:
        """ファイル保存エラーのテスト（詳細）"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po.path = Path("test.po")
        mock_po.save.side_effect = PermissionError("Access denied")
        self.main_window.file_handler.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        with self.assertRaises(PermissionError):
            self.main_window.file_handler.save_file()

        # エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with(
            "ファイルの保存に失敗しました: Access denied",
            3000
        )

    def test_save_file_as_with_error(self) -> None:
        """名前を付けて保存のエラーテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po.save.side_effect = PermissionError("Access denied")
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        with patch("sgpo_editor.gui.main_window.QFileDialog.getSaveFileName", return_value=("test.po", "")):
            with self.assertRaises(PermissionError):
                self.main_window._save_file_as()

        # エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with("保存に失敗しました", 3000)

    def test_next_entry_with_error(self) -> None:
        """次のエントリへの移動エラーテスト"""
        # 無効な状態を設定
        self.main_window.current_entry_index = "invalid"
        self.main_window.total_entries = 10

        # テスト実行
        with self.assertRaises(Exception):
            self.main_window.next_entry()

    def test_entry_selection_display(self) -> None:
        """エントリ選択時の表示テスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            EntryModel(
                msgid=f"test{i}",
                msgstr=f"テスト{i}",
                msgctxt=f"context{i}" if i % 2 == 0 else None
            )
            for i in range(3)
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        mock_po.get_entry_by_key.side_effect = lambda key: next(
            (entry for entry in mock_entries if entry.key == key), None
        )
        self.main_window.current_po = mock_po

        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria = MagicMock(return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致"))

        # テーブルを更新
        self.main_window._update_table()

        # エントリを選択
        self.main_window.table.selectRow(1)
        selected_entry = mock_entries[1]

        # エントリエディタの内容を確認
        self.assertEqual(self.main_window.entry_editor.msgid_edit.toPlainText(), selected_entry.msgid)
        self.assertEqual(self.main_window.entry_editor.msgstr_edit.toPlainText(), selected_entry.msgstr)
        self.assertEqual(self.main_window.entry_editor.fuzzy_checkbox.isChecked(), selected_entry.fuzzy)

    def test_entry_update(self) -> None:
        """エントリ更新機能のテスト"""
        # テスト用のエントリを作成
        mock_entry = EntryModel(
            msgid="test",
            msgstr="テスト",
            msgctxt="context"
        )

        # POファイルをモック
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_entry_by_key.return_value = mock_entry

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # エントリをエディタにセット
        self.main_window.entry_editor.set_entry(mock_entry)

        # エディタの内容を変更
        new_msgstr = "新しいテスト"
        self.main_window.entry_editor.msgstr_edit.setPlainText(new_msgstr)

        # 変更を適用
        self.main_window._on_apply_clicked()

        # 検証
        self.assertEqual(mock_entry.msgstr, new_msgstr)
        mock_status_bar.showMessage.assert_called_with("エントリを更新しました", 3000)

    def test_entry_list_layout(self):
        """エントリリストの列数、ヘッダー、列幅が要件通りであることを確認するテスト"""
        # エントリリストテーブルウィジェットを取得（ここでは entry_table という属性が存在すると仮定）
        table = self.main_window.entry_table

        # 列数が5であることを確認
        assert table.columnCount() == 5, "エントリリストは5列でなければなりません"

        # ヘッダーのテキストを検証
        expected_headers = ["エントリ番号", "msgctxt", "msgid", "msgstr", "状態"]
        for i, expected in enumerate(expected_headers):
            header_item = table.horizontalHeaderItem(i)
            assert header_item is not None, f"列 {i+1} のヘッダーが存在しません"
            assert header_item.text() == expected, f"列 {i+1} のヘッダーが '{expected}' ではなく '{header_item.text()}' です"

        # 予め決められた列幅を検証
        expected_widths = [80, 120, None, None, 100]  # Stretchモードの列はNoneとする
        for i, expected_width in enumerate(expected_widths):
            width = table.columnWidth(i)
            if expected_width is not None:
                assert width == expected_width, f"列 {i+1} の幅が {expected_width} ではなく {width} です"

    def test_entry_list_data(self) -> None:
        """エントリリストの表示されるデータの整合性テスト"""
        from sgpo_editor.gui.models.entry import EntryModel

        # テスト用のエントリを作成
        test_entry = EntryModel(msgid="id_test", msgstr="str_test", msgctxt="ctxt_test", flags=[])
        # 状態は、msgstrが存在し、かつfuzzyがないので「完了」となるはず
        expected_status = test_entry.get_status()

        # ViewerPOFileのモックを設定
        mock_po = MagicMock()
        mock_po.get_filtered_entries.return_value = [test_entry]
        self.main_window.current_po = mock_po

        # SearchWidgetのメソッドをモック
        self.main_window.search_widget.get_search_criteria = MagicMock(return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致"))

        # テーブルを更新
        self.main_window._update_table()

        # テーブルの内容を検証
        table = self.main_window.entry_table
        self.assertEqual(table.rowCount(), 1, "テーブルに1行のエントリが表示されるはずです")

        # 各列の内容を検証
        # 列0: エントリ番号（行番号 + 1）
        item0 = table.item(0, 0)
        self.assertIsNotNone(item0, "エントリ番号が表示されていません")
        item0 = cast(QTableWidgetItem, item0)
        self.assertEqual(item0.text(), "1", "エントリ番号が正しく表示されていません")

        # 列1: msgctxt
        item1 = table.item(0, 1)
        self.assertIsNotNone(item1, "msgctxtが表示されていません")
        item1 = cast(QTableWidgetItem, item1)
        self.assertEqual(item1.text(), "ctxt_test", "msgctxtが正しく表示されていません")

        # 列2: msgid
        item2 = table.item(0, 2)
        self.assertIsNotNone(item2, "msgidが表示されていません")
        item2 = cast(QTableWidgetItem, item2)
        self.assertEqual(item2.text(), "id_test", "msgidが正しく表示されていません")

        # 列3: msgstr
        item3 = table.item(0, 3)
        self.assertIsNotNone(item3, "msgstrが表示されていません")
        item3 = cast(QTableWidgetItem, item3)
        self.assertEqual(item3.text(), "str_test", "msgstrが正しく表示されていません")

        # 列4: 状態
        item4 = table.item(0, 4)
        self.assertIsNotNone(item4, "状態が表示されていません")
        item4 = cast(QTableWidgetItem, item4)
        self.assertEqual(item4.text(), expected_status, "状態が正しく表示されていません")

    def test_state_based_filtering(self) -> None:
        """エントリの状態ベースフィルタ機能のテスト"""
        # 複数の状態のエントリを作成
        entries = {
            "すべて": [
                MagicMock(key="key1", position=1, msgid="a1", msgstr="hello", flags=[]),
                MagicMock(key="key2", position=2, msgid="b1", msgstr="", flags=[]),
                MagicMock(key="key3", position=3, msgid="c1", msgstr="world", flags=["fuzzy"]),
                MagicMock(key="key4", position=4, msgid="d1", msgstr="done", flags=[])
            ],
            "翻訳済み": [
                MagicMock(key="key1", position=1, msgid="a1", msgstr="hello", flags=[]),
                MagicMock(key="key4", position=4, msgid="d1", msgstr="done", flags=[])
            ],
            "未翻訳": [
                MagicMock(key="key2", position=2, msgid="b1", msgstr="", flags=[])
            ],
            "Fuzzy": [
                MagicMock(key="key3", position=3, msgid="c1", msgstr="world", flags=["fuzzy"])
            ],
            "要確認": [
                MagicMock(key="key2", position=2, msgid="b1", msgstr="", flags=[]),
                MagicMock(key="key3", position=3, msgid="c1", msgstr="world", flags=["fuzzy"])
            ]
        }

        # POファイルをモック
        mock_po = MagicMock()

        # 各状態フィルタ条件でテスト
        for state, filtered_entries in entries.items():
            # SearchCriteriaの設定
            self.main_window.search_widget.get_search_criteria = MagicMock(
                return_value=SearchCriteria(filter=state, search_text="", match_mode="部分一致")
            )

            # get_filtered_entriesの戻り値を設定
            mock_po.get_filtered_entries.return_value = filtered_entries
            self.main_window.file_handler.current_po = mock_po

            # テーブルを更新
            self.main_window.table_manager.update_table(mock_po)

            # 行数を検証
            expected_count = len(filtered_entries)
            self.assertEqual(
                self.main_window.table.rowCount(), 
                expected_count, 
                f"フィルタ '{state}' での件数が期待通りでない"
            )

            # 表示内容を検証
            for i, entry in enumerate(filtered_entries):
                msgid_item = self.main_window.table.item(i, 2)  # msgid列
                self.assertIsNotNone(msgid_item)
                self.assertEqual(msgid_item.text(), entry.msgid)

    def test_keyword_based_filtering(self) -> None:
        """キーワードベースのフィルタ機能のテスト"""
        # 検索パターンと期待される結果を定義
        test_cases = {
            ("app", "部分一致"): [
                MagicMock(key="key1", position=1, msgid="apple", msgstr="red", flags=[]),
                MagicMock(key="key2", position=2, msgid="application", msgstr="blue", flags=[]),
                MagicMock(key="key4", position=4, msgid="pineapple", msgstr="green", flags=[])
            ],
            ("app", "前方一致"): [
                MagicMock(key="key1", position=1, msgid="apple", msgstr="red", flags=[]),
                MagicMock(key="key2", position=2, msgid="application", msgstr="blue", flags=[])
            ],
            ("apple", "完全一致"): [
                MagicMock(key="key1", position=1, msgid="apple", msgstr="red", flags=[])
            ],
            ("le", "後方一致"): [
                MagicMock(key="key1", position=1, msgid="apple", msgstr="red", flags=[]),
                MagicMock(key="key4", position=4, msgid="pineapple", msgstr="green", flags=[])
            ]
        }

        # POファイルをモック
        mock_po = MagicMock()

        # 各検索パターンでテスト
        for (search_text, match_mode), expected_entries in test_cases.items():
            # SearchCriteriaの設定
            self.main_window.search_widget.get_search_criteria = MagicMock(
                return_value=SearchCriteria(filter="すべて", search_text=search_text, match_mode=match_mode)
            )

            # get_filtered_entriesの戻り値を設定
            mock_po.get_filtered_entries.return_value = expected_entries
            self.main_window.file_handler.current_po = mock_po

            # テーブルを更新
            self.main_window.table_manager.update_table(mock_po)

            # 行数を検証
            expected_count = len(expected_entries)
            self.assertEqual(
                self.main_window.table.rowCount(),
                expected_count,
                f"{match_mode}での検索 '{search_text}' の結果が期待通りでない"
            )

            # 表示内容を検証
            for i, entry in enumerate(expected_entries):
                msgid_item = self.main_window.table.item(i, 2)  # msgid列
                self.assertIsNotNone(msgid_item)
                self.assertEqual(msgid_item.text(), entry.msgid)

    def test_gui_state_filter_interaction(self) -> None:
        """GUIを介した状態ベースフィルタのテスト"""
        # 複数の状態異なるエントリを作成
        entry1 = EntryModel(msgid="e1", msgstr="translated", flags=[])
        entry2 = EntryModel(msgid="e2", msgstr="", flags=[])
        entry3 = EntryModel(msgid="e3", msgstr="maybe", flags=["fuzzy"])
        entries = [entry1, entry2, entry3]

        # fake_get_filtered_entries は、フィルタ条件に応じたエントリを返す
        def fake_get_filtered_entries(filter_text: str, search_text: str, sort_column: str | None, sort_order: str | None):
            if filter_text == "翻訳済み":
                return [e for e in entries if e.msgstr and not e.fuzzy]
            elif filter_text == "未翻訳":
                return [e for e in entries if not e.msgstr]
            elif filter_text == "Fuzzy":
                return [e for e in entries if e.fuzzy]
            elif filter_text == "要確認":
                return [e for e in entries if (not e.msgstr) or e.fuzzy]
            else:  # "すべて" またはその他
                return entries

        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_filtered_entries = fake_get_filtered_entries

        # GUI上で状態フィルタとして "翻訳済み" を選択
        from sgpo_editor.gui.widgets.search import SearchCriteria
        self.main_window.search_widget.get_search_criteria = lambda: SearchCriteria(filter="翻訳済み", search_text="", match_mode="部分一致")

        self.main_window._update_table()
        # 翻訳済みのエントリは entry1 のみのはず
        self.assertEqual(self.main_window.table.rowCount(), 1, "GUI上の状態フィルタが正しく機能していません")

    def test_gui_keyword_filter_interaction(self) -> None:
        """GUIを介したキーワードフィルタ（部分一致）のテスト"""
        # キーワード検索用のエントリ作成
        entry1 = EntryModel(msgid="apple", msgstr="red", flags=[])
        entry2 = EntryModel(msgid="application", msgstr="blue", flags=[])
        entry3 = EntryModel(msgid="banana", msgstr="yellow", flags=[])
        entry4 = EntryModel(msgid="pineapple", msgstr="green", flags=[])
        entries = [entry1, entry2, entry3, entry4]

        def fake_get_filtered_entries(filter_text: str, search_text: str, sort_column: str | None, sort_order: str | None):
            match_mode = self.main_window.search_widget.get_match_mode() if hasattr(self.main_window.search_widget, "get_match_mode") else "部分一致"
            if not search_text:
                return entries
            if match_mode == "部分一致":
                return [e for e in entries if search_text in e.msgid]
            elif match_mode == "前方一致":
                return [e for e in entries if e.msgid.startswith(search_text)]
            elif match_mode == "後方一致":
                return [e for e in entries if e.msgid.endswith(search_text)]
            elif match_mode == "完全一致":
                return [e for e in entries if e.msgid == search_text]
            return entries

        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_filtered_entries = fake_get_filtered_entries

        from sgpo_editor.gui.widgets.search import SearchCriteria
        self.main_window.search_widget.get_search_criteria = lambda: SearchCriteria(filter="すべて", search_text="app", match_mode="部分一致")

        self.main_window._update_table()
        expected_count = len([e for e in entries if "app" in e.msgid])
        self.assertEqual(self.main_window.table.rowCount(), expected_count, "GUI上の部分一致キーワードフィルタが正しく機能していません")

    def test_view_menu_layout(self) -> None:
        """表示メニューのレイアウト切り替え機能のテスト"""
        # 表示メニューの確認
        menubar = self.main_window.menuBar()
        display_menu = None
        for action in menubar.actions():
            if action.text() == "表示":
                display_menu = action.menu()
                break
        self.assertIsNotNone(display_menu)

        # エントリ編集サニューの確認
        entry_edit_menu = None
        for action in display_menu.actions():
            if action.text() == "エントリ編集":
                entry_edit_menu = action.menu()
                break
        self.assertIsNotNone(entry_edit_menu)

        # レイアウト1とレイアウト2のアクションの確認
        layout_actions = entry_edit_menu.actions()
        self.assertEqual(len(layout_actions), 2)
        layout1_action = layout_actions[0]
        layout2_action = layout_actions[1]

        self.assertEqual(layout1_action.text(), "レイアウト1")
        self.assertEqual(layout2_action.text(), "レイアウト2")
        self.assertTrue(layout1_action.isCheckable())
        self.assertTrue(layout2_action.isCheckable())
        self.assertTrue(layout1_action.isChecked())
        self.assertFalse(layout2_action.isChecked())

    def test_layout_switching(self) -> None:
        """レイアウト切り替えの動作テスト"""
        # 初期状態の確認
        self.assertEqual(self.main_window.entry_editor.get_layout_type(), LayoutType.LAYOUT1)

        # レイアウト2に切り替え
        layout2_action = None
        for action in self.main_window.menuBar().actions():
            if action.text() == "表示":
                display_menu = action.menu()
                for sub_action in display_menu.actions():
                    if sub_action.text() == "エントリ編集":
                        entry_edit_menu = sub_action.menu()
                        layout2_action = entry_edit_menu.actions()[1]
                        break
                break
        self.assertIsNotNone(layout2_action)
        layout2_action.trigger()
        self.assertEqual(self.main_window.entry_editor.get_layout_type(), LayoutType.LAYOUT2)

        # レイアウト1に切り替え
        layout1_action = None
        for action in self.main_window.menuBar().actions():
            if action.text() == "表示":
                display_menu = action.menu()
                for sub_action in display_menu.actions():
                    if sub_action.text() == "エントリ編集":
                        entry_edit_menu = sub_action.menu()
                        layout1_action = entry_edit_menu.actions()[0]
                        break
                break
        self.assertIsNotNone(layout1_action)
        layout1_action.trigger()
        self.assertEqual(self.main_window.entry_editor.get_layout_type(), LayoutType.LAYOUT1)

    def test_layout_with_entry(self) -> None:
        """エントリ表示中のレイアウト切り替えテスト"""
        # テスト用のエントリを作成
        mock_entry = EntryModel(
            msgid="test_msgid",
            msgstr="test_msgstr",
            msgctxt="test_context"
        )

        # エントリのmsgctxtが正しく設定されていることを確認
        self.assertEqual(mock_entry.msgctxt, "test_context", "EntryModelのmsgctxtが正しく設定されていません")

        # エントリを設定
        self.main_window.entry_editor.set_entry(mock_entry)

        # 初期状態でコンテキストが正しく設定されていることを確認
        initial_context = self.main_window.entry_editor.context_edit.text()
        self.assertEqual(initial_context, "test_context", "初期状態でコンテキストが正しく設定されていません")

        # レイアウト2に切り替え
        layout2_action = None
        for action in self.main_window.menuBar().actions():
            if action.text() == "表示":
                display_menu = action.menu()
                for sub_action in display_menu.actions():
                    if sub_action.text() == "エントリ編集":
                        entry_edit_menu = sub_action.menu()
                        layout2_action = entry_edit_menu.actions()[1]
                        break
                break
        self.assertIsNotNone(layout2_action)
        layout2_action.trigger()

        # レイアウト2に切り替わったことを確認
        self.assertEqual(
            self.main_window.entry_editor.get_layout_type(),
            LayoutType.LAYOUT2,
            "レイアウト2への切り替えが失敗しました"
        )

        # レイアウト2でのコンテキストを確認
        layout2_context = self.main_window.entry_editor.context_edit.text()
        self.assertEqual(
            layout2_context,
            "test_context",
            f"レイアウト2でコンテキストが失われました: expected='test_context', actual='{layout2_context}'"
        )

        # エントリの内容が保持されていることを確認
        self.assertEqual(
            self.main_window.entry_editor.msgid_edit.toPlainText(),
            "test_msgid",
            "レイアウト2でmsgidが失われました"
        )
        self.assertEqual(
            self.main_window.entry_editor.msgstr_edit.toPlainText(),
            "test_msgstr",
            "レイアウト2でmsgstrが失われました"
        )

        # レイアウト1に切り替え
        layout1_action = None
        for action in self.main_window.menuBar().actions():
            if action.text() == "表示":
                display_menu = action.menu()
                for sub_action in display_menu.actions():
                    if sub_action.text() == "エントリ編集":
                        entry_edit_menu = sub_action.menu()
                        layout1_action = entry_edit_menu.actions()[0]
                        break
                break
        self.assertIsNotNone(layout1_action)
        layout1_action.trigger()

        # レイアウト1に切り替わったことを確認
        self.assertEqual(
            self.main_window.entry_editor.get_layout_type(),
            LayoutType.LAYOUT1,
            "レイアウト1への切り替えが失敗しました"
        )

        # レイアウト1でのコンテキストを確認
        layout1_context = self.main_window.entry_editor.context_edit.text()
        self.assertEqual(
            layout1_context,
            "test_context",
            f"レイアウト1でコンテキストが失われました: expected='test_context', actual='{layout1_context}'"
        )

        # エントリの内容が保持されていることを確認
        self.assertEqual(
            self.main_window.entry_editor.msgid_edit.toPlainText(),
            "test_msgid",
            "レイアウト1でmsgidが失われました"
        )
        self.assertEqual(
            self.main_window.entry_editor.msgstr_edit.toPlainText(),
            "test_msgstr",
            "レイアウト1でmsgstrが失われました"
        )

if __name__ == "__main__":
    unittest.main()
