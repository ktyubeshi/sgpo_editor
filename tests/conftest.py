"""pytestの設定ファイル

このファイルはpytestの実行時に自動的に読み込まれ、
テスト環境のセットアップやフィクスチャの定義を行います。
"""

import os
import pytest
from PySide6 import QtWidgets, QtCore

# QApplicationのグローバルインスタンス
_qapp = None


def pytest_configure(config):
    """pytestの設定時に呼び出される関数"""
    # QApplicationのインスタンスを作成
    global _qapp
    if _qapp is None:
        # 既存のQApplicationがあるかチェック
        _qapp = QtWidgets.QApplication.instance()
        if _qapp is None:
            # なければ新しく作成
            _qapp = QtWidgets.QApplication([])
            _qapp.setQuitOnLastWindowClosed(False)


def pytest_unconfigure(config):
    """pytestの終了時に呼び出される関数"""
    global _qapp
    if _qapp is not None:
        # QApplicationを終了
        _qapp.quit()
        _qapp = None


@pytest.fixture(scope="session")
def qapp():
    """QApplicationのフィクスチャ"""
    global _qapp
    if _qapp is None:
        pytest_configure(None)
    return _qapp


@pytest.fixture(scope="function")
def cleanup_windows():
    """テスト後にすべてのウィンドウをクリーンアップするフィクスチャ"""
    yield
    # テスト後にすべてのウィンドウを閉じる
    for window in QtWidgets.QApplication.topLevelWidgets():
        window.close()
        window.deleteLater()
    # イベントループを処理して、ウィンドウが確実に閉じられるようにする
    QtCore.QCoreApplication.processEvents() 