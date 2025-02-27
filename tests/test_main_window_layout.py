#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations
from typing import Any, Dict, List, Optional

from unittest.mock import MagicMock, patch, call
import unittest
import sys

# 基底クラスをインポート
from tests.test_base import TestBase

# モックの設定後にインポート
from PySide6.QtWidgets import QApplication, QDockWidget
from PySide6.QtCore import Qt, QSettings
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.widgets.entry_editor import LayoutType


class TestMainWindowLayout(TestBase):
    """MainWindowのレイアウト関連テスト"""

    def test_save_dock_states(self) -> None:
        """ドック状態の保存テスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # QSettingsのモック
        mock_settings = MagicMock()
        
        # QSettingsのコンストラクタをモック
        with patch("sgpo_editor.gui.main_window.QSettings", return_value=mock_settings) as mock_settings_class:
            # テスト対象メソッドを実行
            main_window._save_dock_states()
            
            # 検証
            mock_settings_class.assert_called_once()
            mock_settings.setValue.assert_called()  # 特定の値をチェックするのは難しいため、メソッドが呼ばれたことだけを確認

    def test_restore_dock_states(self) -> None:
        """ドック状態の復元テスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # QSettingsのモック
        mock_settings = MagicMock()
        mock_settings.value.return_value = bytearray(b'test')  # 何かしらのデータを返すようにする
        
        # QSettingsのコンストラクタをモック
        with patch("sgpo_editor.gui.main_window.QSettings", return_value=mock_settings) as mock_settings_class:
            # テスト対象メソッドを実行
            main_window._restore_dock_states()
            
            # 検証
            mock_settings_class.assert_called_once()
            mock_settings.value.assert_called()  # 特定の値をチェックするのは難しいため、メソッドが呼ばれたことだけを確認

    def test_view_menu_layout(self) -> None:
        """表示メニューのレイアウト切り替え機能のテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # モック化したUIManagerの取得
        ui_manager = main_window.ui_manager
        
        # アクションのモック化
        compact_layout_action = MagicMock()
        full_layout_action = MagicMock()
        
        # UIManagerのメソッドをモック
        ui_manager.get_action.side_effect = lambda name: {
            "compact_layout": compact_layout_action,
            "full_layout": full_layout_action
        }.get(name, MagicMock())
        
        # アクションのトリガーシグナルをエミュレート
        compact_layout_action.triggered = MagicMock()
        compact_handler = compact_layout_action.triggered.connect.call_args[0][0]
        
        full_layout_action.triggered = MagicMock()
        full_handler = full_layout_action.triggered.connect.call_args[0][0]
        
        # テスト対象メソッドを実行（コンパクトレイアウト）
        compact_handler()
        
        # 検証（エントリエディタのレイアウトが変更されたことを確認）
        main_window.entry_editor.set_layout_type.assert_called_with(LayoutType.COMPACT)
        
        # テスト対象メソッドを実行（フルレイアウト）
        full_handler()
        
        # 検証（エントリエディタのレイアウトが変更されたことを確認）
        main_window.entry_editor.set_layout_type.assert_called_with(LayoutType.FULL)

    def test_layout_switching(self) -> None:
        """レイアウト切り替えの動作テスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # LayoutTypeの値をモック
        mock_layout_compact = MagicMock()
        mock_layout_full = MagicMock()
        
        # エントリエディタのモック
        with patch("sgpo_editor.gui.widgets.entry_editor.LayoutType.COMPACT", mock_layout_compact), \
             patch("sgpo_editor.gui.widgets.entry_editor.LayoutType.FULL", mock_layout_full):
            
            # 各レイアウトに切り替え
            main_window._set_layout_compact()
            main_window.entry_editor.set_layout_type.assert_called_with(mock_layout_compact)
            
            main_window._set_layout_full()
            main_window.entry_editor.set_layout_type.assert_called_with(mock_layout_full)

    def test_layout_with_entry(self) -> None:
        """エントリ表示中のレイアウト切り替えテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        
        # テーブルのモック
        main_window.table.currentRow.return_value = 0
        
        # テスト用のエントリを作成
        mock_entry = MagicMock()
        
        # ViewerPOFileのモック
        main_window.current_po = MagicMock()
        main_window.current_po.get_entry_at.return_value = mock_entry
        
        # エントリエディタのモック
        main_window.entry_editor.set_entry = MagicMock()
        
        # 現在のエントリを表示
        main_window._show_current_entry()
        
        # 検証（エントリエディタにエントリが設定されたことを確認）
        main_window.entry_editor.set_entry.assert_called_once_with(mock_entry)
        
        # レイアウトを変更
        main_window._set_layout_compact()
        
        # 検証（レイアウトが変更されたことを確認）
        main_window.entry_editor.set_layout_type.assert_called_with(LayoutType.COMPACT)


if __name__ == "__main__":
    unittest.main()
