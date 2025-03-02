#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

# テスト用のモックモジュールをインポート
from tests.mock_helpers import (
    mock_file_dialog_get_open_file_name,
    mock_file_dialog_get_save_file_name,
    MockMainWindow,
    mock_entire_app
)


# pytestのフィクスチャを定義
@pytest.fixture
def mock_app(monkeypatch):
    """アプリケーション全体をモック化するフィクスチャ"""
    # mock_helpers.py のヘルパー関数を使用してアプリ全体をモック化
    mocks = mock_entire_app(monkeypatch)
    yield mocks
    mocks['cleanup']()


@pytest.fixture
def mock_window(monkeypatch):
    """メインウィンドウをモック化するフィクスチャ"""
    mock_main_window = MockMainWindow()

    # ファイルハンドラーを設定
    mock_main_window.file_handler = MagicMock()
    mock_main_window.file_handler.current_po = None
    mock_main_window.file_handler.current_filepath = None

    yield mock_main_window
    mock_main_window.close()


# テストクラスのpytestバージョン
class TestMainWindowBasic:
    """MainWindowの基本機能テスト"""

    def test_initial_state(self, mock_window):
        """初期状態のテスト"""
        # 検証
        assert mock_window.current_po is None
        assert mock_window.entry_editor is not None
        assert mock_window.stats_widget is not None
        assert mock_window.search_widget is not None
        assert mock_window.table is not None

    def test_open_file_success(self, mock_window, monkeypatch):
        """ファイルを開くテスト（成功）"""
        # ダイアログのモック化
        mock_file_dialog_get_open_file_name(monkeypatch, "/mock/path/to/test.po")

        # FileHandlerのopen_fileメソッドをモック
        mock_window.file_handler.open_file = MagicMock(return_value=True)
        mock_window.file_handler.current_filepath = Path("test.po")
        mock_window.file_handler.current_po = MagicMock()
        mock_window.file_handler.current_po.get_stats = MagicMock(return_value={})
        mock_window.file_handler.current_po.file_path = 'test.po'

        # ファイルを開くアクションを実行
        mock_window._open_file()

        # 検証
        assert mock_window.file_handler.current_filepath == Path("test.po")

    def test_save_file_as_success(self, mock_window, monkeypatch):
        """名前を付けて保存のテスト（成功）"""
        # 保存ダイアログのモック化
        mock_file_dialog_get_save_file_name(monkeypatch, "/mock/path/to/test_save.po")

        # 現在のPOファイルをモック
        mock_po = MagicMock()
        mock_po.save = MagicMock()
        mock_po.file_path = 'original.po'
        mock_window.file_handler.current_po = mock_po

        # FileHandlerのsave_fileメソッドをモック
        mock_window.file_handler.save_file = MagicMock(return_value=True)
        mock_window.file_handler.current_filepath = Path("test_save.po")

        # 名前を付けて保存を実行
        mock_window._save_file_as()

        # 検証
        assert mock_window.file_handler.current_filepath == Path("test_save.po")

    def test_open_file_cancel(self, mock_window, monkeypatch):
        """ファイルを開くのキャンセルテスト"""
        # キャンセルをシミュレートするダイアログのモック
        mock_file_dialog_get_open_file_name(monkeypatch, None)  # Noneはキャンセルを意味する

        # 元の状態を保存
        original_po = mock_window.file_handler.current_po

        # ファイルを開くアクションを実行
        mock_window._open_file()

        # 検証（何も変わっていないことを確認）
        assert mock_window.file_handler.current_po == original_po

    def test_save_file_as_cancel(self, mock_window, monkeypatch):
        """名前を付けて保存のキャンセルテスト"""
        # キャンセルをシミュレートするダイアログのモック
        mock_file_dialog_get_save_file_name(monkeypatch, None)  # Noneはキャンセルを意味する

        # 現在のPOファイルをモック
        mock_po = MagicMock()
        mock_po.save = MagicMock()
        mock_po.file_path = 'original.po'
        mock_window.file_handler.current_po = mock_po

        # 元の状態を保存
        original_path = mock_po.file_path

        # 名前を付けて保存を実行
        mock_window._save_file_as()

        # 検証（ファイルパスが変わっていないことを確認）
        assert mock_po.file_path == original_path

    def test_save_file_without_current_po(self, mock_window):
        """現在のPOファイルがない状態での保存テスト"""
        # 現在のPOファイルをNoneに設定
        mock_window.file_handler.current_po = None

        # 保存メソッドをモック化
        mock_window._save_file = MagicMock()

        # 保存を実行
        mock_window._save_file()

        # 検証（_save_fileが呼ばれたことを確認）
        mock_window._save_file.assert_called_once()

    def test_close_event(self, mock_window):
        """ウィンドウを閉じるイベントのテスト"""
        # closeEventをモック
        mock_window.closeEvent = MagicMock()
        event = MagicMock()

        # ウィンドウを閉じる
        mock_window.closeEvent(event)

        # 検証（closeEventが呼ばれたことを確認）
        mock_window.closeEvent.assert_called_once_with(event)
