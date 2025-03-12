"""pytestの設定ファイル

このファイルはpytestの実行時に自動的に読み込まれ、
テスト環境のセットアップやフィクスチャの定義を行います。
"""

import gc
from unittest.mock import MagicMock

import pytest
from PySide6 import QtCore, QtWidgets

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
        # テスト終了時にすべてのウィンドウをクリーンアップ
        for window in QtWidgets.QApplication.topLevelWidgets():
            window.close()
            window.deleteLater()

        # イベントループを処理して、ウィンドウが確実に閉じられるようにする
        QtCore.QCoreApplication.processEvents()

        # QApplicationを終了
        _qapp.quit()
        _qapp = None

        # 明示的にガベージコレクションを実行
        gc.collect()


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

    # 明示的にガベージコレクションを実行してメモリリークを防止
    gc.collect()


@pytest.fixture(scope="function")
def mock_qt_dialogs(monkeypatch):
    """Qt対話型ダイアログをモック化するフィクスチャ

    テストガイドラインに従い、ファイル選択やメッセージボックスなどのダイアログを
    モック化してテストの一時停止を防ぎます。
    """
    # ファイル選択ダイアログのモック
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: ("/mock/path/to/test.po", "All Files (*)"),
    )

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: ("/mock/path/to/save.po", "All Files (*)"),
    )

    # メッセージボックスのモック
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Yes,
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "information",
        lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Ok,
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "warning",
        lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Ok,
    )

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "critical",
        lambda *args, **kwargs: QtWidgets.QMessageBox.StandardButton.Ok,
    )

    yield


@pytest.fixture(scope="function")
def mock_main_window_components(monkeypatch):
    """MainWindowのコンポーネントをモック化するフィクスチャ

    テストガイドラインのMockMainWindowパターンに従い、
    MainWindowの依存コンポーネントをモック化します。
    """
    # モックオブジェクトの作成
    mock_entry_editor = MagicMock()
    mock_stats_widget = MagicMock()
    mock_search_widget = MagicMock()
    mock_table_manager = MagicMock()

    # 検索条件のモック
    mock_search_criteria = MagicMock()
    mock_search_criteria.filter = ""
    mock_search_criteria.search_text = ""
    mock_search_criteria.match_mode = "部分一致"

    # SearchWidgetのget_search_criteriaメソッドのモック
    mock_search_widget.get_search_criteria.return_value = mock_search_criteria

    # モックの適用
    monkeypatch.setattr(
        "sgpo_editor.gui.widgets.entry_editor.EntryEditor",
        lambda *args, **kwargs: mock_entry_editor,
    )

    monkeypatch.setattr(
        "sgpo_editor.gui.widgets.stats.StatsWidget",
        lambda *args, **kwargs: mock_stats_widget,
    )

    monkeypatch.setattr(
        "sgpo_editor.gui.widgets.search.SearchWidget",
        lambda *args, **kwargs: mock_search_widget,
    )

    monkeypatch.setattr(
        "sgpo_editor.gui.table_manager.TableManager",
        lambda *args, **kwargs: mock_table_manager,
    )

    return {
        "entry_editor": mock_entry_editor,
        "stats_widget": mock_stats_widget,
        "search_widget": mock_search_widget,
        "table_manager": mock_table_manager,
    }


# テスト間で共有されるメモック化された値のクリーンアップ
@pytest.fixture(autouse=True, scope="function")
def reset_qt_mocks():
    """すべてのテストの前後でQtモックをリセットするフィクスチャ"""
    yield
    # テスト後にガベージコレクションを実行
    gc.collect()
