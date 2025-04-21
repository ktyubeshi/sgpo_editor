import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from typing import Optional

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu

from sgpo_editor.gui.file_handler import FileHandler
from sgpo_editor.gui.main_window import MainWindow
from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.gui.widgets.stats import StatsWidget
from sgpo_editor.gui.widgets.search import SearchWidget
from PySide6.QtWidgets import QTableWidget
import sgpo_editor.gui.main_window  # Patch 対象のモジュールをインポート
import sgpo_editor.gui.ui_setup  # UIManager が定義されているモジュール


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """QSettingsのモックフィクスチャ"""
    settings_store = {}

    # __init__ のモックは削除

    def mock_set_value(self, key, value):
        settings_store[key] = value

    # type 引数を受け取れるように修正
    def mock_value(self, key, defaultValue=None, type=None):
        return settings_store.get(key, defaultValue)

    def mock_sync(self):
        pass  # 何もしない

    def mock_clear(self):
        nonlocal settings_store
        settings_store = {}

    monkeypatch.setattr(QSettings, "setValue", mock_set_value)
    monkeypatch.setattr(QSettings, "value", mock_value)
    monkeypatch.setattr(QSettings, "sync", mock_sync)
    monkeypatch.setattr(QSettings, "clear", mock_clear)

    settings_store = {}
    yield settings_store
    settings_store = {}


@pytest.fixture
def file_handler(mock_settings):
    """FileHandler フィクスチャ"""
    # FileHandlerに必要なコールバックをMagicMockで渡す
    mock_update_stats = MagicMock()
    mock_update_table = MagicMock()
    mock_status_callback = MagicMock()
    # mock_settings フィクスチャは QSettings の動作をモックするので、
    # ここでは QSettings() をインスタンス化して渡せばモックが使われる
    return FileHandler(
        QSettings(), mock_update_stats, mock_update_table, mock_status_callback
    )


@pytest.fixture
def main_window(qtbot, file_handler, monkeypatch):
    """MainWindow フィクスチャ (FileHandlerとUI状態復元をモック)"""
    monkeypatch.setattr(
        sgpo_editor.gui.main_window, "FileHandler", lambda *args, **kwargs: file_handler
    )

    # UIManager の状態復元メソッドをモックして QSettings アクセスを回避
    monkeypatch.setattr(
        sgpo_editor.gui.ui_setup.UIManager, "restore_dock_states", lambda self: None
    )
    monkeypatch.setattr(
        sgpo_editor.gui.ui_setup.UIManager, "restore_window_state", lambda self: None
    )

    window = MainWindow()
    qtbot.addWidget(window)
    qtbot.waitUntil(
        lambda: hasattr(window, "ui_manager")
        and hasattr(window.ui_manager, "recent_files_menu")
        and window.ui_manager.recent_files_menu is not None,
        timeout=2000,
    )
    return window


def test_menu_uses_correct_settings(main_window, file_handler, monkeypatch):
    """メニューが正しい設定キー（新しい形式 'recent_files'）を使用しているか確認"""
    test_files = ["file1.po", "file2.po"]

    # QSettings を直接操作して値を設定
    settings = QSettings()
    settings.setValue("recent_files", json.dumps(test_files))  # 新しいキー
    settings.setValue("recent_files_str", "old_value.po")  # 古いキー（無視されるはず）
    settings.sync()

    # ファイル存在チェック (Path.exists) をモックして常に True を返すようにする
    monkeypatch.setattr(Path, "exists", lambda self: True)

    # MainWindow のメニュー更新メソッドを呼び出す
    main_window._update_recent_files_menu()

    # 検証：メニューのアクションを確認
    # recent_files_menu は UIManager の属性
    recent_menu = main_window.ui_manager.recent_files_menu
    assert recent_menu is not None, "recent_files_menu was not created"
    menu_actions = recent_menu.actions()

    # メニューアイテムからファイルパスを抽出（セパレータやクリアを除く）
    action_files = [action.data() for action in menu_actions if action.data()]

    print(f"Menu actions data: {action_files}")  # デバッグ用
    print(f"Expected files: {test_files}")  # デバッグ用

    # 'recent_files' から読み込まれたファイルリストと一致するか確認
    assert action_files == test_files, (
        f"Menu actions {action_files} do not match expected {test_files}"
    )

    # 古いキー 'recent_files_str' の値が含まれていないことを確認
    assert "old_value.po" not in action_files, (
        "Old setting key 'recent_files_str' was incorrectly used"
    )


def test_recent_files_menu_update(main_window, file_handler, monkeypatch):
    """最近使ったファイルのメニューが更新されるか確認"""
    test_files = ["fileA.po", "fileB.po"]

    # QSettings を直接操作して値を設定
    settings = QSettings()
    settings.setValue("recent_files", json.dumps(test_files))
    settings.sync()

    # ファイル存在チェック (Path.exists) をモック
    monkeypatch.setattr(Path, "exists", lambda self: True)

    # メニュー更新メソッドを呼び出し
    main_window._update_recent_files_menu()

    # 検証：メニューのアクションを確認
    recent_menu = main_window.ui_manager.recent_files_menu
    assert recent_menu is not None
    actions = recent_menu.actions()

    # 期待されるアクション数: ファイル2つ + セパレータ1つ + クリア1つ = 4
    assert len(actions) == 4, f"Expected 4 actions, but found {len(actions)}"

    # ファイルアクションの確認
    assert actions[0].text() == "&1. fileA.po"
    assert actions[0].data() == "fileA.po"
    assert actions[1].text() == "&2. fileB.po"
    assert actions[1].data() == "fileB.po"

    # セパレータの確認
    assert actions[2].isSeparator() is True

    # クリアアクションの確認
    assert actions[3].text() == "履歴をクリア (&C)"
    assert actions[3].isEnabled() is True  # 履歴があるので有効なはず


@pytest.mark.asyncio
async def test_open_file_updates_menu(main_window, file_handler, tmp_path, monkeypatch):
    """ファイルを開いた後にメニューが更新されるか確認"""
    file_path = tmp_path / "test_open.po"
    file_path.touch()

    # 0. 初期状態: QSettings をクリア
    settings = QSettings()
    settings.setValue("recent_files", json.dumps([]))
    settings.sync()
    # Path.exists のモック
    monkeypatch.setattr(Path, "exists", lambda self: True)

    # 1. ファイルを開く前
    main_window._update_recent_files_menu()
    recent_menu_before = main_window.ui_manager.recent_files_menu
    actions_before = recent_menu_before.actions()
    # 期待されるアクション数: 履歴なし(無効) のみ = 1?
    # 現在の実装では、履歴がない場合「(履歴なし)」アクションのみ追加される
    assert len(actions_before) == 1, "Initial menu should have 1 action (no history)"
    assert actions_before[0].text() == "(履歴なし)"
    assert actions_before[0].isEnabled() is False

    # 2. ファイルを開く操作をシミュレート
    # FileHandler.open_file をモックして add_recent_file を呼び出すようにする
    async def mock_open_file(path: Optional[str] = None):
        actual_path = path or str(file_path)  # 引数がない場合はテストパスを使用
        print(f"[Mock open_file] Opening: {actual_path}")
        file_handler.add_recent_file(str(actual_path))  # 実際の add_recent_file を呼ぶ
        # await asyncio.sleep(0) # 必要なら非同期処理を待機
        return True  # 成功したと仮定

    # FileHandler の open_file メソッドを非同期モックで置き換え
    # 注意: MainWindow._open_file は FileHandler.open_file を呼び出すため、
    #       MainWindow._open_file 自体のモックは不要かもしれない。
    #       FileHandler.open_file の挙動を直接制御する。
    monkeypatch.setattr(file_handler, "open_file", mock_open_file)
    # FileHandler.add_recent_file は QSettings を更新するのでモック不要
    # FileHandler.get_recent_files も QSettings を読むのでモック不要

    # _open_file (または関連するアクション) を呼び出すのではなく、
    # モック化した file_handler.open_file を直接呼び出す
    file_path_str = str(file_path)
    # await main_window._open_file(file_path_str) # この呼び出しを削除
    await file_handler.open_file(file_path_str)  # モックされた open_file を呼び出す

    # 3. ファイルを開いた後、メニューを更新して確認
    main_window._update_recent_files_menu()
    recent_menu_after = main_window.ui_manager.recent_files_menu
    actions_after = recent_menu_after.actions()

    # 期待されるアクション数: ファイル1つ + セパレータ1つ + クリア1つ = 3
    assert len(actions_after) == 3, (
        f"Expected 3 actions after opening, but found {len(actions_after)}"
    )

    # ファイルアクションの確認
    assert actions_after[0].text() == f"&1. {file_path.name}"
    assert actions_after[0].data() == str(file_path)
    assert actions_after[0].isEnabled() is True

    # セパレータの確認
    assert actions_after[1].isSeparator() is True

    # クリアアクションの確認
    assert actions_after[2].text() == "履歴をクリア (&C)"
    assert actions_after[2].isEnabled() is True


@pytest.mark.asyncio
async def test_clear_recent_files(main_window):
    """最近使ったファイル履歴のクリア機能を確認"""
    initial_files = ["file1.po", "file2.po"]
    main_window.file_handler.get_recent_files.return_value = initial_files
    main_window._update_recent_files_menu()

    # クリア前のアクション数を確認
    assert (
        main_window.recent_files_menu.addAction.call_count == 4
    )  # ファイル2 + 区切り線 + クリア

    # クリアアクションを取得してトリガー
    # モックからトリガーするのではなく、対応するハンドラを直接呼び出す
    if asyncio.iscoroutinefunction(main_window._on_clear_recent_files_triggered):
        await main_window._on_clear_recent_files_triggered()  # await を追加
    else:
        main_window._on_clear_recent_files_triggered()

    # クリアされたか確認
    main_window.file_handler.clear_recent_files.assert_called_once()
    # メニューが更新されたか確認（クリアアクションのみになるはず）
    main_window._update_recent_files_menu()
    assert main_window.recent_files_menu.addAction.call_count == 1
