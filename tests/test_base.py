#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations
import pytest
from typing import Any, Dict, List, Optional
from PySide6 import QtWidgets, QtCore


class TestBase:
    """すべてのテストの基底クラス"""

    @pytest.fixture(autouse=True)
    def setup_method(self, monkeypatch, cleanup_windows):
        """各テスト実行前の前処理"""
        # 特定のパッチは必要に応じてテスト内で適用する
        pass

    @pytest.fixture
    def mock_file_dialog(self, monkeypatch):
        """QFileDialogをモックするフィクスチャ"""
        def mock_get_open_file_name(*args, **kwargs):
            return ("/mock/path/to/file.po", "All Files (*)")
        
        def mock_get_save_file_name(*args, **kwargs):
            return ("/mock/path/to/save.po", "All Files (*)")
        
        monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", mock_get_open_file_name)
        monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", mock_get_save_file_name)
    
    @pytest.fixture
    def mock_message_box(self, monkeypatch):
        """QMessageBoxをモックするフィクスチャ"""
        def mock_question(*args, **kwargs):
            return QtWidgets.QMessageBox.Yes
        
        def mock_information(*args, **kwargs):
            pass
        
        def mock_warning(*args, **kwargs):
            pass
        
        def mock_critical(*args, **kwargs):
            pass
        
        monkeypatch.setattr(QtWidgets.QMessageBox, "question", mock_question)
        monkeypatch.setattr(QtWidgets.QMessageBox, "information", mock_information)
        monkeypatch.setattr(QtWidgets.QMessageBox, "warning", mock_warning)
        monkeypatch.setattr(QtWidgets.QMessageBox, "critical", mock_critical)
