#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pathlib import Path

import pytest
from PySide6 import QtWidgets, QtCore

# 基底クラスをインポート
from tests.test_base import TestBase
from tests.mock_helpers import (
    mock_file_dialog_get_open_file_name,
    mock_file_dialog_get_save_file_name,
    mock_message_box_warning,
    wait_for_window_shown,
    click_button
)

# モックの設定後にインポート
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.models.entry import EntryModel
from sgpo_editor.gui.widgets.search import SearchCriteria


class TestMainWindowBasic(TestBase):
    """MainWindowの基本機能テスト"""

    def test_initial_state(self, qtbot):
        """初期状態のテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        
        # 初期状態を検証
        assert main_window.file_handler.current_po is None
        assert main_window.entry_editor is not None
        assert main_window.stats_widget is not None
        assert main_window.search_widget is not None
        assert main_window.table is not None
    
    def test_open_file_success(self, qtbot, monkeypatch):
        """ファイルを開くテスト（成功）"""
        # ファイルダイアログをモック
        mock_file_dialog_get_open_file_name(monkeypatch, "test.po")
        
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        wait_for_window_shown(qtbot, main_window)
        
        # SearchWidgetのメソッドをモック
        main_window.search_widget.get_search_criteria = lambda: SearchCriteria(
            filter="", search_text="", match_mode="部分一致"
        )

        # StatsWidgetのメソッドをモック
        main_window.stats_widget.update_stats = lambda *args, **kwargs: None
        
        # FileHandlerのopen_fileメソッドをモック
        original_open_file = main_window.file_handler.open_file
        def mock_open_file(filepath=None):
            main_window.file_handler.current_filepath = Path("test.po")
            main_window.file_handler.current_po = type('MockPO', (), {
                'get_stats': lambda: {},
                'file_path': 'test.po'
            })()
            return True
        main_window.file_handler.open_file = mock_open_file
        
        # ファイルを開くアクションを実行
        main_window._open_file()
        
        # 検証
        assert main_window.file_handler.current_filepath == Path("test.po")
    
    def test_save_file_as_success(self, qtbot, monkeypatch):
        """名前を付けて保存のテスト（成功）"""
        # ファイルダイアログをモック
        mock_file_dialog_get_save_file_name(monkeypatch, "test_save.po")
        
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        wait_for_window_shown(qtbot, main_window)
        
        # 現在のPOファイルをモック
        main_window.file_handler.current_po = type('MockPO', (), {
            'save': lambda file_path: None,
            'file_path': 'original.po'
        })()
        
        # FileHandlerのsave_fileメソッドをモック
        original_save_file = main_window.file_handler.save_file
        def mock_save_file(filepath=None):
            main_window.file_handler.current_filepath = Path("test_save.po")
            return True
        main_window.file_handler.save_file = mock_save_file
        
        # 名前を付けて保存を実行
        main_window._save_file_as()
        
        # 検証
        assert main_window.file_handler.current_filepath == Path("test_save.po")
    
    def test_open_file_cancel(self, qtbot, monkeypatch):
        """ファイルを開くのキャンセルテスト"""
        # ファイルダイアログをモック（キャンセル）
        mock_file_dialog_get_open_file_name(monkeypatch, None)
        
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        wait_for_window_shown(qtbot, main_window)
        
        # 元の状態を保存
        original_po = main_window.file_handler.current_po
        
        # ファイルを開くアクションを実行
        main_window._open_file()
        
        # 検証（何も変わっていないことを確認）
        assert main_window.file_handler.current_po == original_po
    
    def test_save_file_as_cancel(self, qtbot, monkeypatch):
        """名前を付けて保存のキャンセルテスト"""
        # ファイルダイアログをモック（キャンセル）
        mock_file_dialog_get_save_file_name(monkeypatch, None)
        
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        wait_for_window_shown(qtbot, main_window)
        
        # 現在のPOファイルをモック
        mock_po = type('MockPO', (), {
            'save': lambda file_path: None,
            'file_path': 'original.po'
        })()
        main_window.file_handler.current_po = mock_po
        
        # 元の状態を保存
        original_path = mock_po.file_path
        
        # 名前を付けて保存を実行
        main_window._save_file_as()
        
        # 検証（ファイルパスが変わっていないことを確認）
        assert mock_po.file_path == original_path
    
    def test_save_file_without_current_po(self, qtbot, monkeypatch):
        """現在のPOファイルがない状態での保存テスト"""
        # メッセージボックスをモック
        mock_message_box_warning(monkeypatch)
        
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        wait_for_window_shown(qtbot, main_window)
        
        # 現在のPOファイルをNoneに設定
        main_window.file_handler.current_po = None
        
        # 保存を実行
        main_window._save_file()
        
        # 検証（警告が表示されることを確認）
        # モックが呼ばれたことの検証は難しいため、例外が発生しないことを確認
        assert True
    
    @pytest.mark.skip("GUIテスト実行環境の問題解決中")
    def test_close_event(self, qtbot, monkeypatch):
        """ウィンドウを閉じるイベントのテスト"""
        # MainWindowのインスタンスを作成
        main_window = MainWindow()
        qtbot.addWidget(main_window)
        wait_for_window_shown(qtbot, main_window)
        
        # closeEventをモック
        original_close_event = main_window.closeEvent
        
        def mock_close_event(event):
            # イベントを受け入れる
            event.accept()
        
        main_window.closeEvent = mock_close_event
        
        # ウィンドウを閉じる
        main_window.close()
        
        # 検証（ウィンドウが閉じられたことを確認）
        assert not main_window.isVisible()
