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

        assert retrieved_value == test_paths_str
        assert retrieved_paths == test_paths

    def test_load_recent_files(self, setup_settings):
        """最近使用したファイルのリストが正しく読み込まれるかテスト"""
        # 準備
        settings = QSettings()
        test_paths = ["/path/to/file1.po", "/path/to/file2.po"]
        test_paths_str = ";".join(test_paths)
        settings.setValue("recent_files_str", test_paths_str)
        settings.sync()  # 確実に保存

        # 実行
        window = MainWindow()
        loaded_files = window.file_handler.recent_files

        # 検証
        assert loaded_files == test_paths

    def test_settings_consistency(self, setup_settings):
        """recent_files_strとrecent_filesの設定値が一致するかテスト"""
        # 準備
        window = MainWindow()
        test_path = "/path/to/test.po"

        # 実行：ファイルを追加
        window.file_handler.add_recent_file(test_path)

        # 検証：両方の設定値が一致していること
        settings = QSettings()
        recent_files_str = settings.value("recent_files_str", "", type=str)
        recent_files = settings.value("recent_files", [])

        # 文字列から復元したリスト
        str_list = recent_files_str.split(";") if recent_files_str else []

        # 両方の設定値が一致していること
        assert str_list == recent_files
        assert test_path in str_list
        assert test_path in recent_files

    def test_menu_uses_correct_settings(self, qtbot, setup_settings):
        """メニュー更新時に正しい設定値が使用されるかテスト"""
        # 準備
        window = MainWindow()
        qtbot.addWidget(window)
        test_path = "/path/to/menu_test.po"

        # recent_files_strのみに値を設定
        settings = QSettings()
        settings.setValue("recent_files_str", test_path)
        settings.setValue("recent_files", [])
        settings.sync()

        # メニューを更新
        window.ui_manager.update_recent_files_menu(window._open_recent_file)

        # 検証：メニューにファイルが表示されていること
        recent_menu = window.ui_manager.recent_files_menu
        has_file = False
        for action in recent_menu.actions():
            if action.data() == test_path:
                has_file = True
                break

        # recent_files_strから読み込まれていれば成功、recent_filesから読み込まれていれば失敗
        assert has_file, "recent_files_strの値がメニューに反映されていません"

    def test_add_recent_file(self, qtbot, setup_settings, temp_po_file):
        """ファイルを開いた後に最近使用したファイルが設定に保存されるかテスト"""
        # 準備
        window = MainWindow()
        qtbot.addWidget(window)

        # 検証: 最初は最近使用したファイルが空
        settings = QSettings()
        initial_files_str = settings.value("recent_files_str", "", type=str)
        assert not initial_files_str  # 空文字列であること

        # ファイルハンドラのadd_recent_fileを直接呼び出す
        with mock.patch.object(window.file_handler, "open_file", return_value=True):
            window.file_handler.add_recent_file(temp_po_file)

        # 検証: 設定に最近使用したファイルが保存されている
        settings.sync()  # 確実に読み込み
        recent_files_str = settings.value("recent_files_str", "", type=str)
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
        # 「履歴なし」という無効なアクションがあることを確認
        assert recent_menu.actions()[0].text() == "(履歴なし)"
        assert not recent_menu.actions()[0].isEnabled()

        # ファイルを開く
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

    def test_max_recent_files(self, qtbot, setup_settings):
        """最近使用したファイルの最大数を超えた場合、古いものが削除されるかテスト"""
        # 準備
        window = MainWindow()
        qtbot.addWidget(window)

        # MAX_RECENT_FILES + 1個のファイルパスを作成
        max_files = 10  # FileHandlerのMAX_RECENT_FILESと同じ値
        test_files = [f"/path/to/file{i}.po" for i in range(max_files + 2)]

        # ファイルを順番に追加
        for filepath in test_files:
            window.file_handler.add_recent_file(filepath)

        # 検証: 最大数を超えないこと
        assert len(window.file_handler.recent_files) <= max_files

        # 最新のファイルがリストの先頭にあること
        assert window.file_handler.recent_files[0] == test_files[-1]

        # 最も古いファイルがリストから削除されていること
        assert test_files[0] not in window.file_handler.recent_files

    def test_clear_recent_files(self, qtbot, setup_settings, temp_po_file):
        """最近使用したファイルの履歴をクリアできるかテスト"""
        # 準備
        window = MainWindow()
        qtbot.addWidget(window)

        # ファイルを追加
        window.file_handler.add_recent_file(temp_po_file)

        # メニューを更新
        window.ui_manager.update_recent_files_menu(window._open_recent_file)

        # クリアアクションを実行
        clear_action = None
        for action in window.ui_manager.recent_files_menu.actions():
            # アクションテキストを修正 (&C を含む)
            if action.text() == "履歴をクリア (&C)":
                clear_action = action
                break

        assert clear_action is not None
        clear_action.trigger()

        # 検証: 設定から履歴が削除されていること
        settings = QSettings()
        recent_files = settings.value("recent_files", [])
        assert not recent_files

        # メニューが初期状態に戻っていること
        assert window.ui_manager.recent_files_menu.actions()[0].text() == "(履歴なし)"
        assert not window.ui_manager.recent_files_menu.actions()[0].isEnabled()
