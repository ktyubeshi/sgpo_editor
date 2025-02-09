# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations
from typing import Any, cast

import unittest
from unittest.mock import MagicMock, patch, call

from PySide6.QtWidgets import QTableWidgetItem, QApplication
from PySide6.QtCore import Qt
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.models.entry import EntryModel
import sys
from pathlib import Path
import logging
from sgpo_editor.gui.widgets.search import SearchCriteria

app = QApplication([])

class TestMainWindow(unittest.TestCase):
    """メインウィンドウのテスト"""

    def setUp(self) -> None:
        """テストの前準備"""
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        self.main_window = MainWindow()
        # StatsWidgetのメソッドをモック
        self.main_window.stats_widget.update_stats = MagicMock()

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

    @patch("sgpo_editor.gui.main_window.ViewerPOFile")
    def test_search_filter(self, mock_viewer_po_file: Any) -> None:
        """検索/フィルタリング機能のテスト"""
        # SearchWidgetのメソッドをモック（get_search_criteriaに統一）
        self.main_window.search_widget.get_search_criteria = MagicMock(return_value=SearchCriteria(filter="test_filter", search_text="test_search", match_mode="部分一致"))

        # ViewerPOFileのモックを設定
        self.main_window.current_po = mock_viewer_po_file.return_value
        mock_entry = EntryModel(msgid="test", msgstr="テスト")
        self.main_window.current_po.get_filtered_entries.return_value = [mock_entry]

        # テスト実行
        self.main_window._update_table()

        # 検証
        self.main_window.current_po.get_filtered_entries.assert_called_with(
            filter_text="test_filter",
            search_text="test_search",
            sort_column=None,
            sort_order=None
        )

    def test_sort_entries(self) -> None:
        """ソート機能のテスト"""
        self.main_window.table.horizontalHeader().sortIndicatorOrder = MagicMock(return_value=Qt.SortOrder.AscendingOrder)
        self.main_window._update_table = MagicMock()
        self.main_window._on_header_clicked(2)  # msgidカラムをクリック
        self.main_window._update_table.assert_called_with(2, Qt.SortOrder.DescendingOrder)

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

    def test_table_update_with_sort(self) -> None:
        """ソート付きのテーブル更新テスト"""
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

        # テスト実行
        self.main_window._update_table(sort_column=2, sort_order=Qt.SortOrder.AscendingOrder)

        # 検証
        self.assertEqual(self.main_window.table.rowCount(), 3)
        for i, entry in enumerate(mock_entries):
            item = self.main_window.table.item(i, 0)
            self.assertIsNotNone(item, f"Row {i} item not found")
            item = cast(QTableWidgetItem, item)
            self.assertEqual(item.text(), str(i + 1))

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
        self.main_window.table.selectRow(1)
        second_entry = mock_entries[1]
        self.assertIsNotNone(second_entry)
        self.assertNotEqual(first_entry.key, second_entry.key)

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
        mock_entry = EntryModel(msgid="test", msgstr="テスト", position={"invalid": "type"})
        mock_po.get_filtered_entries.side_effect = TypeError("unsupported operand type(s) for +: 'dict' and 'int'")
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        self.main_window._update_table()

        # エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with(
            "テーブルの更新でエラー: unsupported operand type(s) for +: 'dict' and 'int'",
            3000
        )

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
        """ナビゲーションエラーのテスト"""
        # 不正な状態を設定
        self.main_window.current_entry_index = "invalid"  # 型エラーを発生させる
        self.main_window.total_entries = 10

        # ナビゲーションを実行
        with self.assertRaises(Exception):
            self.main_window.next_entry()

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
        self.main_window.current_po = None
        self.main_window.current_entry_index = 100
        self.main_window.total_entries = 0

        # テスト実行
        self.main_window._show_current_entry()

        # 検証（エラーが発生しないことを確認）
        self.assertTrue(True)

    def test_update_progress_invalid_state(self) -> None:
        """無効な状態での内部カウンター更新テスト"""
        # 無効な状態を設定
        self.main_window.current_entry_index = "invalid"
        self.main_window.total_entries = None

        # テスト実行
        self.main_window._update_progress()

        # 検証
        self.assertEqual(self.main_window.current_entry_index, 0)
        self.assertEqual(self.main_window.total_entries, 0)

    def test_validate_counters_invalid_state(self) -> None:
        """無効な状態でのカウンター検証テスト"""
        # 無効な状態を設定
        self.main_window.current_entry_index = "invalid"
        self.main_window.total_entries = "invalid"

        # テスト実行
        with self.assertRaises(ValueError):
            self.main_window._validate_counters()

        # 検証
        self.assertEqual(self.main_window.current_entry_index, 0)
        self.assertEqual(self.main_window.total_entries, 0)

    def test_entry_changed_no_number(self) -> None:
        """エントリ番号なしでのエントリ変更テスト"""
        # テスト実行
        self.main_window._on_entry_changed(-1)

        # 検証
        self.assertEqual(self.main_window.entry_editor_dock.windowTitle(), "エントリ編集")

    def test_table_update_error_with_invalid_entry(self) -> None:
        """無効なエントリでのテーブル更新エラーテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entry = MagicMock(spec=['msgid', 'msgstr', 'position'])  # keyを除外
        mock_entry.msgid = None  # 無効なmsgidを設定
        mock_entry.msgstr = None  # 無効なmsgstrを設定
        mock_entry.position = None  # 無効なpositionを設定
        mock_po.get_filtered_entries.return_value = [mock_entry]
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        self.main_window._update_table()

        # エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_any_call(
            "エントリの表示でエラー: 'NoneType' object has no attribute 'key'",
            3000
        )

    def test_save_file_with_path_attribute(self) -> None:
        """POファイルのパス属性アクセスのテスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po._path = Path("test.po")
        mock_po.path = property(lambda self: self._path)  # pathプロパティを追加
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        self.main_window._save_file()

        # 検証
        mock_po.save.assert_called_once()
        mock_status_bar.showMessage.assert_called_with("ファイルを保存しました", 5000)

    def test_save_file_without_path_attribute(self) -> None:
        """POファイルのパス属性がない場合のテスト"""
        # POファイルをモック（pathプロパティなし）
        mock_po = MagicMock()
        mock_po.file_path = None
        self.main_window.current_po = mock_po

        # 名前を付けて保存が呼ばれることを確認
        self.main_window._save_file_as = MagicMock()
        self.main_window._save_file()
        self.main_window._save_file_as.assert_called_once()

    def test_save_file_with_error(self) -> None:
        """ファイル保存エラーのテスト（詳細）"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_po.path = Path("test.po")
        mock_po.save.side_effect = PermissionError("Access denied")
        self.main_window.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        self.main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # テスト実行
        with self.assertRaises(PermissionError):
            self.main_window._save_file()

        # エラーメッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with("保存に失敗しました", 3000)

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
        expected_widths = [80, 120, 150, 150, 100]
        for i, expected_width in enumerate(expected_widths):
            width = table.columnWidth(i)
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
        # 1: 翻訳済み（msgstrがあり、fuzzyフラグなし）
        entry1 = EntryModel(msgid="a1", msgstr="hello", flags=[])
        # 2: 未翻訳（msgstrが空）
        entry2 = EntryModel(msgid="b1", msgstr="", flags=[])
        # 3: Fuzzy（fuzzyフラグあり）
        entry3 = EntryModel(msgid="c1", msgstr="world", flags=["fuzzy"])
        # 4: 翻訳済み
        entry4 = EntryModel(msgid="d1", msgstr="done", flags=[])
        entries = [entry1, entry2, entry3, entry4]

        # フィルタ条件と期待される件数の定義
        filters = {
            "すべて": 4,
            "翻訳済み": 2,    # entry1とentry4
            "未翻訳": 1,      # entry2
            "Fuzzy": 1,       # entry3
            "要確認": 2       # 未翻訳またはFuzzy: entry2とentry3
        }

        def fake_get_filtered_entries(filter_text: str, search_text: str, sort_column: str | None, sort_order: str | None):
            def state_filter(entry: EntryModel) -> bool:
                if filter_text == "すべて":
                    return True
                elif filter_text == "翻訳済み":
                    return bool(entry.msgstr and not entry.fuzzy)
                elif filter_text == "未翻訳":
                    return not entry.msgstr
                elif filter_text == "Fuzzy":
                    return entry.fuzzy
                elif filter_text == "要確認":
                    return (not entry.msgstr) or entry.fuzzy
                return True
            return [e for e in entries if state_filter(e)]

        # 各状態フィルタ条件でテスト
        for state, expected_count in filters.items():
            from sgpo_editor.gui.widgets.search import SearchCriteria
            self.main_window.search_widget.get_search_criteria = lambda: SearchCriteria(filter=state, search_text="", match_mode="部分一致")
            self.main_window.current_po = MagicMock()
            self.main_window.current_po.get_filtered_entries = fake_get_filtered_entries

            self.main_window._update_table()
            self.assertEqual(self.main_window.table.rowCount(), expected_count, f"フィルタ '{state}' での件数が期待通りでない")

    def test_keyword_based_filtering(self) -> None:
        """キーワードベースのフィルタ機能のテスト"""
        # キーワード検索用のエントリを作成
        entry1 = EntryModel(msgid="apple", msgstr="red", flags=[])
        entry2 = EntryModel(msgid="application", msgstr="blue", flags=[])
        entry3 = EntryModel(msgid="banana", msgstr="yellow", flags=[])
        entry4 = EntryModel(msgid="pineapple", msgstr="green", flags=[])
        entry5 = EntryModel(msgid="apricot", msgstr="orange", flags=[])
        entries = [entry1, entry2, entry3, entry4, entry5]

        # fake_get_filtered_entries：状態フィルタは常に『すべて』とする
        def fake_get_filtered_entries(filter_text: str, search_text: str, sort_column: str | None, sort_order: str | None):
            # Retrieve match_mode from the search criteria
            criteria = self.main_window.search_widget.get_search_criteria()
            match_mode = criteria.match_mode
            def keyword_filter(entry: EntryModel) -> bool:
                target = entry.msgid
                if not search_text:
                    return True
                if match_mode == "部分一致":
                    return search_text in target
                elif match_mode == "前方一致":
                    return target.startswith(search_text)
                elif match_mode == "後方一致":
                    return target.endswith(search_text)
                elif match_mode == "完全一致":
                    return target == search_text
                return True
            return [e for e in entries if keyword_filter(e)]

        from sgpo_editor.gui.widgets.search import SearchCriteria
        # 部分一致: キーワード "app" -> "apple", "application", "pineapple"
        self.main_window.search_widget.get_search_criteria = lambda: SearchCriteria(filter="すべて", search_text="app", match_mode="部分一致")
        self.main_window.current_po = MagicMock()
        self.main_window.current_po.get_filtered_entries = fake_get_filtered_entries
        self.main_window._update_table()
        self.assertEqual(self.main_window.table.rowCount(), 3, "部分一致フィルタでの件数が正しくない")

        # 前方一致: キーワード "app" -> "apple", "application"
        self.main_window.search_widget.get_search_criteria = lambda: SearchCriteria(filter="すべて", search_text="app", match_mode="前方一致")
        self.main_window._update_table()
        self.assertEqual(self.main_window.table.rowCount(), 2, "前方一致フィルタでの件数が正しくない")

        # 後方一致: キーワード "ple" -> "apple", "pineapple"
        self.main_window.search_widget.get_search_criteria = lambda: SearchCriteria(filter="すべて", search_text="ple", match_mode="後方一致")
        self.main_window._update_table()
        self.assertEqual(self.main_window.table.rowCount(), 2, "後方一致フィルタでの件数が正しくない")

        # 完全一致: キーワード "apple" -> "apple"
        self.main_window.search_widget.get_search_criteria = lambda: SearchCriteria(filter="すべて", search_text="apple", match_mode="完全一致")
        self.main_window._update_table()
        self.assertEqual(self.main_window.table.rowCount(), 1, "完全一致フィルタでの件数が正しくない")

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

if __name__ == "__main__":
    unittest.main()
