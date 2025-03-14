#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
from pathlib import Path
import pytest
from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import QApplication, QMainWindow, QTableView
from PySide6.QtTest import QTest

from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.ui_setup import UIManager


@pytest.fixture
def app():
    """Create and return QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    
    # クリーンアップ: テスト用の設定を削除
    settings = QSettings("SGPOEditor", "TableSettings")
    settings.clear()
    settings.sync()


@pytest.fixture
def main_window(app):
    """Create and return MainWindow instance."""
    # 設定をクリアしてからメインウィンドウを作成
    settings = QSettings("SGPOEditor", "TableSettings")
    settings.clear()
    settings.sync()
    
    window = MainWindow()
    # テスト用に明示的にすべての列を表示状態に設定
    for i in range(window.table_manager.table.columnCount()):
        window.table_manager.table.setColumnHidden(i, False)
    yield window
    window.close()


class TestColumnVisibilityGUI:
    """列の表示・非表示機能のGUIテスト"""
    
    def test_initial_column_visibility(self, main_window):
        """初期状態では全ての列が表示されているか確認"""
        # 初期状態ではすべての列が表示されているはず
        table_manager = main_window.table_manager
        table = table_manager.table
        
        # すべての列が表示されているか確認
        for i in range(table.columnCount()):
            assert not table.isColumnHidden(i), f"列 {i} が初期状態で非表示になっています"
            assert table_manager.is_column_visible(i), f"列 {i} のis_column_visible()がFalseを返しました"
            
        # 列の表示状態を直接確認し、メニューのチェック状態と整合しているか確認
        for i, action in enumerate(main_window.ui_manager.column_visibility_actions):
            assert action.isChecked() == (not table.isColumnHidden(i)), \
                f"列 {i} のメニュー項目のチェック状態が実際の表示状態と一致しません"
    
    def test_toggle_column_visibility(self, main_window):
        """列の表示・非表示を切り替える機能のテスト"""
        table_manager = main_window.table_manager
        table = table_manager.table
        
        # 列番号1（msgctxt）を非表示にする
        column_index = 1
        column_name = table_manager.get_column_name(column_index)
        print(f"テスト: 列 {column_index} ({column_name}) を非表示にします")
        
        # メニュー経由で表示・非表示を切り替える（直接APIを呼び出し）
        main_window._toggle_column_visibility(column_index)
        
        # 列が非表示になっているか確認
        assert table.isColumnHidden(column_index), f"列 {column_index} ({column_name}) が非表示になっていません"
        assert not table_manager.is_column_visible(column_index), f"列 {column_index} のis_column_visible()がTrueを返しました"
        assert not main_window.ui_manager.column_visibility_actions[column_index].isChecked(), \
            f"列 {column_index} のメニュー項目が正しくチェック解除されていません"
        
        # 再度表示に戻す
        main_window._toggle_column_visibility(column_index)
        
        # 列が表示されているか確認
        assert not table.isColumnHidden(column_index), f"列 {column_index} ({column_name}) が再表示されていません"
        assert table_manager.is_column_visible(column_index), f"列 {column_index} のis_column_visible()がFalseを返しました"
        assert main_window.ui_manager.column_visibility_actions[column_index].isChecked(), \
            f"列 {column_index} のメニュー項目が正しくチェックされていません"
    
    def test_menu_action_triggers_toggle(self, main_window):
        """メニューのアクションが列の表示・非表示を正しく切り替えるか確認"""
        table_manager = main_window.table_manager
        table = table_manager.table
        
        # 列番号2（msgid）を対象にする
        column_index = 2
        column_name = table_manager.get_column_name(column_index)
        print(f"テスト: メニューアクションで列 {column_index} ({column_name}) の表示状態を切り替えます")
        
        # 初期状態を確認
        initial_hidden = table.isColumnHidden(column_index)
        
        # メニューのアクションをトリガー
        action = main_window.ui_manager.column_visibility_actions[column_index]
        action.trigger()
        
        # 列の状態が切り替わったか確認
        assert table.isColumnHidden(column_index) != initial_hidden, \
            f"列 {column_index} ({column_name}) の表示状態が切り替わっていません"
        
        # 再度トリガーして元に戻す
        action.trigger()
        
        # 元の状態に戻ったか確認
        assert table.isColumnHidden(column_index) == initial_hidden, \
            f"列 {column_index} ({column_name}) の表示状態が元に戻っていません"
    
    def test_settings_persistence(self, main_window, app):
        """列の表示・非表示設定が保存・復元されるかテスト"""
        table_manager = main_window.table_manager
        table = table_manager.table
        
        # 列番号0と3（Entry Numberとmsgstrのみを表示）
        visible_columns = [0, 3]
        
        # すべての列を一度非表示に
        for i in range(table.columnCount()):
            if not table.isColumnHidden(i):
                main_window._toggle_column_visibility(i)
        
        # 指定した列だけ表示に
        for i in visible_columns:
            if table.isColumnHidden(i):
                main_window._toggle_column_visibility(i)
        
        # 状態を確認
        for i in range(table.columnCount()):
            if i in visible_columns:
                assert not table.isColumnHidden(i), f"列 {i} が表示されていません"
            else:
                assert table.isColumnHidden(i), f"列 {i} が非表示になっていません"
        
        # 設定を明示的に保存（通常は_toggle_column_visibilityで自動的に保存されるはず）
        table_manager._save_column_visibility()
        
        # 新しいウィンドウで設定が反映されるか確認
        main_window.close()
        new_window = MainWindow()
        
        # 新しいウィンドウで列の表示状態を確認
        new_table = new_window.table_manager.table
        for i in range(new_table.columnCount()):
            if i in visible_columns:
                assert not new_table.isColumnHidden(i), f"新ウィンドウで列 {i} が表示されていません"
            else:
                assert new_table.isColumnHidden(i), f"新ウィンドウで列 {i} が非表示になっていません"
        
        new_window.close()


if __name__ == "__main__":
    # スタンドアロンで実行するときのデバッグコード
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # デバッグのため一部の列を非表示にしてみる
    window._toggle_column_visibility(1)  # msgctxtを非表示
    
    sys.exit(app.exec())
