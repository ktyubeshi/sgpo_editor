#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import gc

import pytest
from PySide6 import QtWidgets, QtCore

from tests.mock_helpers import (
    mock_file_dialog_get_open_file_name,
    mock_file_dialog_get_save_file_name,
    mock_message_box_warning,
    mock_message_box_question
)


class TestBase:
    """すべてのGUIテストの基底クラス"""

    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch, qtbot, qapp, request):
        """テスト実行前の共通セットアップ（自動実行）"""
        # QApplicationが存在することを確認
        assert QtWidgets.QApplication.instance() is not None

        # モックを設定
        self._setup_mocks(monkeypatch)

        # テスト終了時に自動クリーンアップを実行するための設定
        request.addfinalizer(self._cleanup)

    def _setup_mocks(self, monkeypatch):
        """モックの設定"""
        # ファイルダイアログのモック
        mock_file_dialog_get_open_file_name(monkeypatch)
        mock_file_dialog_get_save_file_name(monkeypatch)

        # メッセージボックスのモック
        mock_message_box_warning(monkeypatch)
        mock_message_box_question(monkeypatch)

    def _cleanup(self):
        """テスト終了時のクリーンアップ処理"""
        # テスト終了時にすべてのウィンドウをクリーンアップ
        for window in QtWidgets.QApplication.topLevelWidgets():
            window.close()
            window.deleteLater()

        # イベントループを処理して、ウィンドウが確実に閉じられるようにする
        QtCore.QCoreApplication.processEvents()

        # 明示的にガベージコレクションを実行
        gc.collect()


class MockMainWindow:
    """MainWindowのモッククラス"""

    def __init__(self, *args, **kwargs):
        # モックの属性を初期化
        self.file_handler = type('MockFileHandler', (), {'current_po': None})()
        self.entry_editor = type('MockEntryEditor', (), {'update_entry': lambda *args, **kwargs: None})()
        self.stats_widget = type('MockStatsWidget', (), {'update_stats': lambda *args, **kwargs: None})()
        self.search_widget = type('MockSearchWidget', (), {
            'get_search_criteria': lambda: type('SearchCriteria', (), {
                'filter': '',
                'search_text': '',
                'match_mode': '部分一致'
            })()
        })()
        self.table = type('MockTable', (), {'update_table': lambda *args, **kwargs: None})()
        self.mock_po = type('MockPO', (), {'get_entries': lambda *args, **kwargs: []})()

        # モックのシグナル
        self.file_opened = type('Signal', (), {'emit': lambda: None})()
        self.file_saved = type('Signal', (), {'emit': lambda: None})()

    def closeEvent(self, event):
        """閉じるイベントのモック"""
        event.accept()

    def update_table(self, *args, **kwargs):
        """テーブル更新のモック"""
        pass
