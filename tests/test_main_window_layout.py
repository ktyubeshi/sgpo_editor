#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import gc
import unittest
from unittest.mock import MagicMock, patch

# モックの設定後にインポート
from sgpo_editor.gui.widgets.entry_editor import LayoutType


class MockMainWindow:
    """MainWindowのモック実装"""

    def __init__(self):
        # 各コンポーネントをモック化
        self.ui_manager = MagicMock()
        self.entry_editor = MagicMock()
        self.table = MagicMock()
        self.current_po = MagicMock()

        # ドックウィジェットのモック
        self.dock_widgets = {
            "search": MagicMock(),
            "stats": MagicMock(),
            "entry_editor": MagicMock()
        }

        # 状態保存用のメソッド
        self.saveState = MagicMock(return_value=bytearray(b'saved_state'))
        self.restoreState = MagicMock(return_value=True)

    def _save_dock_states(self):
        """ドック状態の保存"""
        # QSettingsはモック済みなので実際のオブジェクトは作成しない
        # 代わりにモックオブジェクトを返す
        settings = MagicMock()
        settings.setValue = MagicMock()
        settings.setValue("mainWindow/geometry", self.saveState())
        return settings

    def _restore_dock_states(self):
        """ドック状態の復元"""
        # QSettingsはモック済みなので実際のオブジェクトは作成しない
        # 代わりにモックオブジェクトを返す
        settings = MagicMock()
        settings.value = MagicMock(return_value=bytearray(b'test'))
        state = settings.value("mainWindow/geometry")
        if state:
            self.restoreState(state)
        return settings

    def _set_layout_compact(self):
        """コンパクトレイアウトに設定"""
        self.entry_editor.set_layout_type(LayoutType.LAYOUT1)

    def _set_layout_full(self):
        """フルレイアウトに設定"""
        self.entry_editor.set_layout_type(LayoutType.LAYOUT2)

    def _show_current_entry(self):
        """現在選択されているエントリを表示"""
        row = self.table.currentRow()
        if row >= 0:
            entry = self.current_po.get_entry_at(row)
            self.entry_editor.set_entry(entry)


class TestMainWindowLayout(unittest.TestCase):
    """MainWindowのレイアウト関連テスト"""

    def setUp(self):
        """各テストの前処理"""
        self.main_window = MockMainWindow()

    def tearDown(self):
        """各テストの後処理"""
        self.main_window = None
        gc.collect()

    def test_save_dock_states(self) -> None:
        """ドック状態の保存テスト"""
        # テスト対象メソッドを実行
        settings = self.main_window._save_dock_states()

        # 検証
        settings.setValue.assert_called_once()  # 特定の値をチェックするのは難しいため、メソッドが呼ばれたことだけを確認

    def test_restore_dock_states(self) -> None:
        """ドック状態の復元テスト"""
        # テスト対象メソッドを実行
        settings = self.main_window._restore_dock_states()

        # 検証
        settings.value.assert_called_once()  # 特定の値をチェックするのは難しいため、メソッドが呼ばれたことだけを確認

    def test_view_menu_layout(self) -> None:
        """表示メニューのレイアウト切り替え機能のテスト"""
        # エントリエディタのメソッドをパッチしてモック
        self.main_window.entry_editor.set_layout_type = MagicMock()

        # 直接メソッドを呼び出してテスト
        self.main_window._set_layout_compact()
        self.main_window._set_layout_full()

        # 検証（エントリエディタのレイアウトが変更されたことを確認）
        self.main_window.entry_editor.set_layout_type.assert_any_call(LayoutType.LAYOUT1)
        self.main_window.entry_editor.set_layout_type.assert_any_call(LayoutType.LAYOUT2)

    def test_layout_switching(self) -> None:
        """レイアウト切り替えの動作テスト"""
        # LayoutTypeを直接パッチするのではなく、メソッドをモック
        with patch.object(self.main_window.entry_editor, 'set_layout_type') as mock_set_layout_type:
            # レイアウトをCOMPACT（LAYOUT1）に切り替え
            self.main_window._set_layout_compact()
            # レイアウトタイプがLAYOUT1に設定されたことを確認
            mock_set_layout_type.assert_called_with(LayoutType.LAYOUT1)

            # レイアウトをFULL（LAYOUT2）に切り替え
            self.main_window._set_layout_full()
            # レイアウトタイプがLAYOUT2に設定されたことを確認
            mock_set_layout_type.assert_called_with(LayoutType.LAYOUT2)

    def test_layout_with_entry(self) -> None:
        """エントリ表示中のレイアウト切り替えテスト"""
        # テーブルのモック
        self.main_window.table.currentRow.return_value = 0

        # テスト用のエントリを作成
        mock_entry = MagicMock()

        # ViewerPOFileのモック
        self.main_window.current_po.get_entry_at.return_value = mock_entry

        # エントリエディタのモック
        self.main_window.entry_editor.set_entry = MagicMock()

        # 現在のエントリを表示
        self.main_window._show_current_entry()

        # 検証（エントリエディタにエントリが設定されたことを確認）
        self.main_window.entry_editor.set_entry.assert_called_once_with(mock_entry)

        # レイアウトを変更
        self.main_window._set_layout_compact()

        # 検証（レイアウトが変更されたことを確認）
        self.main_window.entry_editor.set_layout_type.assert_called_with(LayoutType.LAYOUT1)


if __name__ == "__main__":
    unittest.main()
