#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch, call

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.main_window import MainWindow


class TestTableGuiSync(unittest.TestCase):
    """テーブルとGUIの同期に関する詳細なテスト"""

    def setUp(self):
        """各テストの前処理"""
        # テーブルをモック
        self.table = MagicMock(spec=QTableWidget)
        self.table.columnCount.return_value = 6
        
        # 列の表示/非表示状態を管理する辞書
        self.column_visibility = {i: False for i in range(6)}  # 初期状態：全て表示
        
        # isColumnHiddenの振る舞いを設定
        def is_column_hidden_side_effect(idx):
            return self.column_visibility.get(idx, False)
            
        self.table.isColumnHidden.side_effect = is_column_hidden_side_effect
        
        # setColumnHiddenの振る舞いを設定
        def set_column_hidden_side_effect(idx, hidden):
            self.column_visibility[idx] = hidden
            
        self.table.setColumnHidden.side_effect = set_column_hidden_side_effect
        
        # テーブルマネージャを作成
        self.table_manager = TableManager(self.table)
        
        # _hidden_columnsを初期化
        self.table_manager._hidden_columns = set()

    def tearDown(self):
        """各テストの後処理"""
        self.table_manager = None
        self.table = None

    def test_toggle_visibility_updates_internal_state_and_gui(self):
        """列の表示/非表示切替が内部状態とGUIの両方を正しく更新するか検証"""
        # 切り替える列
        column = 3
        
        # 初期状態を確認
        self.assertFalse(self.table.isColumnHidden(column))
        self.assertNotIn(column, self.table_manager._hidden_columns)
        
        # 列の表示/非表示を切り替え (表示→非表示)
        self.table_manager.toggle_column_visibility(column)
        
        # 内部状態の更新を確認
        self.assertIn(column, self.table_manager._hidden_columns)
        
        # GUI状態の更新を確認
        self.assertTrue(self.column_visibility[column])
        
        # もう一度切り替え (非表示→表示)
        self.table_manager.toggle_column_visibility(column)
        
        # 内部状態の更新を確認
        self.assertNotIn(column, self.table_manager._hidden_columns)
        
        # GUI状態の更新を確認
        self.assertFalse(self.column_visibility[column])

    def test_update_table_preserves_visibility_in_gui(self):
        """テーブル更新時にGUIの列表示/非表示状態が正しく保持されるか検証"""
        # 非表示にする列
        hidden_columns = [1, 4]
        
        # 列を非表示に設定
        for col in hidden_columns:
            self.table_manager.toggle_column_visibility(col)
            
        # setColumnHiddenが適切に呼ばれたか確認
        for col in hidden_columns:
            self.assertTrue(self.column_visibility[col])
            self.assertIn(col, self.table_manager._hidden_columns)
            
        # モックをリセット
        self.table.setColumnHidden.reset_mock()
        
        # テーブル更新用のモックデータを作成
        entries = []
        for i in range(3):
            entry = MagicMock()
            entry.position = i
            entry.msgctxt = f"context_{i}"
            entry.msgid = f"msgid_{i}"
            entry.msgstr = f"msgstr_{i}"
            entry.fuzzy = False
            entry.obsolete = False
            entry.get_status = MagicMock(return_value="translated")
            entry.overall_quality_score = MagicMock(return_value=85)
            entries.append(entry)
            
        # テーブル更新処理を実行
        with patch('sgpo_editor.gui.table_manager.QTableWidgetItem'):
            self.table_manager._update_table_contents(entries)
            
        # テーブル更新後に非表示列が正しく設定されているか確認
        expected_calls = []
        for i in range(6):
            if i in hidden_columns:
                expected_calls.append(call(i, True))
                
        # setColumnHiddenの呼び出しを確認
        self.table.setColumnHidden.assert_has_calls(expected_calls, any_order=True)
        
        # 内部状態が保持されているか確認
        for col in hidden_columns:
            self.assertIn(col, self.table_manager._hidden_columns)

    def test_internal_state_and_gui_always_in_sync(self):
        """内部状態とGUIの同期が常に保たれているか検証"""
        # _apply_column_visibilityメソッドをモックするのではなく、実際に動作させるための代替実装
        def apply_column_visibility_mock(self):
            for i in range(self.table.columnCount()):
                is_hidden = i in self._hidden_columns
                self.table.setColumnHidden(i, is_hidden)
                
        # _apply_column_visibilityをモック実装で置き換え
        with patch.object(self.table_manager.__class__, '_apply_column_visibility', new=apply_column_visibility_mock):
            # 列表示状態を追跡するための追加データ構造
            column_states = {i: {'internal': False, 'gui': False} for i in range(6)}
            
            # いくつかの列を非表示に
            columns_to_hide = [0, 2, 5]
            
            # 列を順番に非表示に
            for col in columns_to_hide:
                self.table_manager.toggle_column_visibility(col)
                
                # 内部状態を更新
                for i in range(6):
                    column_states[i]['internal'] = i in self.table_manager._hidden_columns
                    column_states[i]['gui'] = self.column_visibility[i]
                
                # 各ステップで内部状態とGUIが一致しているか確認
                for i in range(6):
                    self.assertEqual(
                        column_states[i]['internal'], 
                        column_states[i]['gui'], 
                        f"列 {i} の状態: 内部={column_states[i]['internal']}, GUI={column_states[i]['gui']}"
                    )
                    
            # いくつかの列を表示に戻す
            columns_to_show = [0, 5]
            
            # 列を順番に表示に
            for col in columns_to_show:
                self.table_manager.toggle_column_visibility(col)
                
                # 内部状態を更新
                for i in range(6):
                    column_states[i]['internal'] = i in self.table_manager._hidden_columns
                    column_states[i]['gui'] = self.column_visibility[i]
                
                # 各ステップで内部状態とGUIが一致しているか確認
                for i in range(6):
                    self.assertEqual(
                        column_states[i]['internal'],
                        column_states[i]['gui'],
                        f"列 {i} の状態: 内部={column_states[i]['internal']}, GUI={column_states[i]['gui']}"
                    )
                    
            # テーブル更新後も同期が保たれるか確認
            entries = []
            for i in range(3):
                entry = MagicMock()
                entry.position = i
                entry.msgctxt = f"context_{i}"
                entry.msgid = f"msgid_{i}"
                entry.msgstr = f"msgstr_{i}"
                entry.fuzzy = False
                entry.obsolete = False
                entry.get_status = MagicMock(return_value="translated")
                entry.overall_quality_score = MagicMock(return_value=80)
                entries.append(entry)
                
            # テーブル更新
            with patch('sgpo_editor.gui.table_manager.QTableWidgetItem'):
                self.table_manager._update_table_contents(entries)
                
            # 内部状態を更新
            for i in range(6):
                column_states[i]['internal'] = i in self.table_manager._hidden_columns
                column_states[i]['gui'] = self.column_visibility[i]
                
            # 更新後も同期が保たれているか確認
            for i in range(6):
                self.assertEqual(
                    column_states[i]['internal'],
                    column_states[i]['gui'],
                    f"テーブル更新後、列 {i} の状態: 内部={column_states[i]['internal']}, GUI={column_states[i]['gui']}"
                )


if __name__ == "__main__":
    unittest.main()
