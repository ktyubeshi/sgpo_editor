#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import gc
import unittest
from unittest.mock import MagicMock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget

from sgpo_editor.core.cache_manager import EntryCacheManager


class TestMainWindowKeyboard(unittest.TestCase):
    """キーボード操作に関するテスト"""

    def setUp(self):
        """各テストの前処理"""
        # テーブルウィジェットのモック
        self.table = MagicMock(spec=QTableWidget)
        self.table.rowCount.return_value = 5

        # エントリエディタのモック
        self.entry_editor = MagicMock()

        # EntryCacheManagerのモック
        self.mock_cache_manager = MagicMock(spec=EntryCacheManager)

        # 現在のPOファイル取得用コールバックのモック
        self.get_current_po = MagicMock()
        mock_po = MagicMock()
        mock_entry = MagicMock()
        mock_po.get_entry_by_key.return_value = mock_entry
        self.get_current_po.return_value = mock_po

        # テーブル更新用コールバックのモック
        self.update_table = MagicMock()

        # ステータス表示用コールバックのモック
        self.show_status = MagicMock()

        # テスト対象のイベントハンドラーをインポート
        from sgpo_editor.gui.event_handler import EventHandler

        # イベントハンドラーのインスタンス作成
        self.event_handler = EventHandler(
            self.table,
            self.entry_editor,
            self.mock_cache_manager,
            self.get_current_po,
            self.show_status,
        )

        # テーブルアイテムのモック
        self.mock_item = MagicMock()
        self.mock_item.data.return_value = "test_key"
        self.table.item.return_value = self.mock_item

    def tearDown(self):
        """各テストの後処理"""
        self.event_handler = None
        self.table = None
        self.entry_editor = None
        self.get_current_po = None
        self.update_table = None
        self.show_status = None
        gc.collect()

    def test_keyboard_navigation(self):
        """キーボードナビゲーションのテスト"""
        # イベント接続を設定
        self.event_handler.setup_connections()

        # currentCellChangedシグナルが接続されていることを確認
        # 注：このテストはイベントハンドラーの実装が修正された後に成功する
        self.table.currentCellChanged.connect.assert_called_once()

        # キーボード操作をシミュレート（currentCellChangedシグナルを発火）
        # 現在の実装では接続されていないため、直接メソッドを呼び出す
        self.event_handler._on_current_cell_changed(1, 0, 0, 0)

        # 詳細ビューが更新されたことを確認
        self.entry_editor.set_entry.assert_called_once()

    def test_keyboard_navigation_updates_detail_view(self):
        """キーボードナビゲーションで詳細ビューが更新されることを確認するテスト"""
        # イベント接続を設定
        self.event_handler.setup_connections()

        # キーボード操作をシミュレート（currentCellChangedシグナルを発火）
        # 現在の実装では接続されていないため、直接メソッドを呼び出す
        self.event_handler._on_current_cell_changed(2, 0, 1, 0)

        # 詳細ビューが更新されたことを確認
        self.table.item.assert_called_with(2, 0)
        self.mock_item.data.assert_called_with(Qt.ItemDataRole.UserRole)
        self.get_current_po().get_entry_by_key.assert_called_with("test_key")
        self.entry_editor.set_entry.assert_called_once()


if __name__ == "__main__":
    unittest.main()
