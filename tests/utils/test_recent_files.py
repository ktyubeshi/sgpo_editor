"""最近使用したファイル機能のテスト"""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
from PySide6.QtCore import QCoreApplication, QSettings

from sgpo_editor.gui.main_window import MainWindow


class TestRecentFiles:
    """最近使用したファイル機能のテスト"""

    @pytest.fixture(scope="class", autouse=True)
    def setup_qt_settings(self):
        """QSettingsの初期設定を行う"""
        # テスト用の設定
        QCoreApplication.setOrganizationName("SGPO-Test")
        QCoreApplication.setApplicationName("POEditor-Test")
        yield

    @pytest.fixture
    def setup_settings(self):
        """テスト用の設定をセットアップ"""
        # テスト前に既存の設定をクリア
        settings = QSettings()
        settings.setValue("recent_files_str", "")
        settings.setValue("recent_files", [])
        settings.sync()  # 確実に保存
        yield
        # テスト後にもクリア
        settings.setValue("recent_files_str", "")
        settings.setValue("recent_files", [])
        settings.sync()  # 確実に保存

    @pytest.fixture
    def temp_po_file(self):
        """テスト用の一時POファイル"""
        fd, filepath = tempfile.mkstemp(suffix=".po")
        with os.fdopen(fd, "w") as f:
            f.write('msgid "test"\nmsgstr "テスト"')
        yield filepath
        if os.path.exists(filepath):
            os.unlink(filepath)

    def test_qsettings_string_list(self, setup_settings):
        """QSettingsの文字列リスト保存・取得テスト"""
        # 準備
        settings = QSettings()
        test_paths = ["test_path1", "test_path2"]
        test_paths_str = ";".join(test_paths)

        # 実行
        settings.setValue("test_paths_str", test_paths_str)
        settings.sync()  # 確実に保存

        # 検証
        retrieved_value = settings.value("test_paths_str", "", type=str)
        retrieved_paths = retrieved_value.split(";") if retrieved_value else []

        print(f"保存した値: {test_paths_str}")
        print(f"取得した値: {retrieved_value}")
        print(f"分割後: {retrieved_paths}")

        assert retrieved_value == test_paths_str
        assert retrieved_paths == test_paths

    def test_add_recent_file(self, qtbot, setup_settings, temp_po_file):
        """ファイルを開いた後に最近使用したファイルが設定に保存されるかテスト"""
        # 準備
        window = MainWindow()
        qtbot.addWidget(window)

        # 検証: 最初は最近使用したファイルが空
        settings = QSettings()
        initial_files_str = settings.value("recent_files_str", "", type=str)
        print(f"初期値: {initial_files_str}")
        assert not initial_files_str  # 空文字列であること

        # ファイルハンドラのadd_recent_fileを直接呼び出す
        with mock.patch.object(window.file_handler, "open_file", return_value=True):
            window.file_handler.add_recent_file(temp_po_file)

            # 保存される値を直接確認
            handler_files = window.file_handler.recent_files
            print(f"ハンドラ内の値: {handler_files}")

            # 最近使用したファイルメニューを更新
            window.ui_manager.update_recent_files_menu(window._open_recent_file)

        # 検証: 設定に最近使用したファイルが保存されている
        settings.sync()  # 確実に読み込み
        recent_files_str = settings.value("recent_files_str", "", type=str)
        print(f"保存後の値: {recent_files_str}")
        assert recent_files_str  # 空でないこと

        # 文字列から復元したリスト
        recent_files = recent_files_str.split(";") if recent_files_str else []
        assert temp_po_file in recent_files

    def test_recent_files_menu_update(self, qtbot, setup_settings, temp_po_file):
        """ファイルを開いた後に最近使用したファイルメニューが更新されるかテスト"""
        # 準備
        window = MainWindow()
        qtbot.addWidget(window)

        # 最初はメニューに項目がないことを確認
        recent_menu = window.ui_manager.recent_files_menu
        assert recent_menu is not None
        # 「最近使用した項目はありません」という無効なアクションがある
        assert recent_menu.actions()[0].text() == "最近使用した項目はありません"
        assert not recent_menu.actions()[0].isEnabled()

        # ファイルを開く操作をシミュレート
        window.file_handler.add_recent_file(temp_po_file)
        window.ui_manager.update_recent_files_menu(window._open_recent_file)

        # 検証: メニューに項目が追加されている
        assert len(recent_menu.actions()) >= 2  # ファイル + セパレータ + クリア
        # 最初のアクションはファイル名を表示している
        assert Path(temp_po_file).name == recent_menu.actions()[0].text()
        # アクションのデータにファイルパスが設定されている
        assert temp_po_file == recent_menu.actions()[0].data()

    def test_open_file_updates_menu(
        self, qtbot, setup_settings, temp_po_file, monkeypatch
    ):
        """_open_fileメソッドを呼び出すと最近使用したファイルメニューが更新されるかテスト"""
        # 準備
        window = MainWindow()
        qtbot.addWidget(window)

        # ファイルハンドラのopen_fileをモック
        def mock_open_file(*args, **kwargs):
            # 最近使用したファイルに追加する処理をシミュレート
            window.file_handler.add_recent_file(temp_po_file)
            return True

        monkeypatch.setattr(window.file_handler, "open_file", mock_open_file)

        # 実行: _open_fileメソッドを呼び出す
        window._open_file()

        # 検証: メニューに項目が追加されている
        recent_menu = window.ui_manager.recent_files_menu
        assert len(recent_menu.actions()) >= 2
        assert Path(temp_po_file).name == recent_menu.actions()[0].text()
