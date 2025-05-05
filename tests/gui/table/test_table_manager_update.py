#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QTableWidget

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.table_manager import TableManager


class TestTableManagerUpdate(unittest.TestCase):
    """テーブル更新時の列表示/非表示状態に関するテスト"""

    def setUp(self):
        """各テストの前処理"""
        # テーブルをモック
        self.table = MagicMock(spec=QTableWidget)
        self.table.columnCount.return_value = 6
        self.table.isColumnHidden.return_value = False

        # 列名リスト
        self.column_names = ["位置", "コンテキスト", "原文", "訳文", "状態", "スコア"]

        # テーブルマネージャを作成
        self.mock_cache_manager = MagicMock(spec=EntryCacheManager)
        self.table_manager = TableManager(self.table, self.mock_cache_manager)

        # 既存のモックをリセット
        self.table.reset_mock()

    def tearDown(self):
        """各テストの後処理"""
        self.table_manager = None
        self.table = None

    def test_update_table_with_hidden_columns(self):
        """テーブル更新時に列の表示/非表示状態が正しく保持されるかテスト"""
        # 非表示にする列のインデックス
        hidden_column = 2  # 例: "原文"列を非表示に

        # isColumnHiddenの振る舞いを設定
        column_hidden_state = {}

        def is_column_hidden_side_effect(idx):
            return column_hidden_state.get(idx, False)

        self.table.isColumnHidden.side_effect = is_column_hidden_side_effect

        # テーブルの初期状態を確認
        self.assertNotIn(hidden_column, self.table_manager._hidden_columns)
        self.assertFalse(self.table.isColumnHidden(hidden_column))

        # 非表示状態をセットアップ
        # モックの状態を更新
        column_hidden_state[hidden_column] = True
        self.table_manager._hidden_columns.add(hidden_column)

        # テーブル更新前の状態を確認
        self.assertTrue(self.table.isColumnHidden(hidden_column))
        self.assertIn(hidden_column, self.table_manager._hidden_columns)

        # モックエントリを作成
        entries = []
        for i in range(5):
            entry = MagicMock()
            entry.position = i
            entry.msgctxt = f"context_{i}"
            entry.msgid = f"msgid_{i}"
            entry.msgstr = f"msgstr_{i}"
            entry.fuzzy = False
            entry.obsolete = False
            # get_statusメソッドをセットアップ
            entry.get_status.return_value = "translated"
            # overall_quality_scoreメソッドをセットアップ
            entry.overall_quality_score.return_value = 85
            entry.key = f"key_{i}"
            entries.append(entry)

        # _apply_column_visibilityメソッドをパッチして直接呼び出しを確認できるようにする
        with patch.object(self.table_manager, "_apply_column_visibility") as mock_apply:
            # テーブル更新処理を実行
            with patch("sgpo_editor.gui.table_manager.QTableWidgetItem"):
                self.table_manager._update_table_contents(entries)

            # _apply_column_visibilityが呼ばれたことを確認
            mock_apply.assert_called()

            # 列の非表示状態が維持されていることを確認
            self.assertIn(hidden_column, self.table_manager._hidden_columns)

    def test_multiple_hidden_columns(self):
        """複数の列を非表示にした状態でテーブル更新が正しく動作するかテスト"""
        # 複数の列を非表示に
        hidden_columns = [1, 3, 5]  # "コンテキスト", "訳文", "スコア"列

        # 列の非表示状態をセットアップ
        for col in hidden_columns:
            self.table_manager._hidden_columns.add(col)
            self.table_manager.toggle_column_visibility(col)

        # isColumnHiddenの振る舞いを設定
        def is_column_hidden_side_effect(idx):
            return idx in self.table_manager._hidden_columns

        self.table.isColumnHidden.side_effect = is_column_hidden_side_effect

        # テーブル更新前の状態を確認
        for col in hidden_columns:
            self.assertTrue(self.table.isColumnHidden(col))
            self.assertIn(col, self.table_manager._hidden_columns)

        # テーブル更新用のモックエントリを作成
        entries = []
        for i in range(3):
            entry = MagicMock()
            entry.position = i
            entry.msgctxt = f"context_{i}"
            entry.msgid = f"msgid_{i}"
            entry.msgstr = f"msgstr_{i}"
            entry.fuzzy = False
            entry.obsolete = False
            entry.get_status.return_value = "translated"
            entry.overall_quality_score.return_value = 75
            entries.append(entry)

        # テーブル更新処理を実行
        with patch("sgpo_editor.gui.table_manager.QTableWidgetItem"):
            self.table_manager._update_table_contents(entries)

        # テーブル更新後も全ての非表示状態が維持されているか確認
        for col in hidden_columns:
            self.assertIn(col, self.table_manager._hidden_columns)
            self.table.setColumnHidden.assert_any_call(col, True)

    def test_toggle_column_after_update(self):
        """テーブル更新後に列の表示/非表示を切り替えるテスト"""
        # テーブル更新用のモックエントリを作成
        entries = []
        for i in range(2):
            entry = MagicMock()
            entry.position = i
            entry.msgctxt = f"context_{i}"
            entry.msgid = f"msgid_{i}"
            entry.msgstr = f"msgstr_{i}"
            entry.fuzzy = False
            entry.obsolete = False
            entry.get_status.return_value = "translated"
            entry.overall_quality_score.return_value = 90
            entry.key = f"key_{i}"
            entries.append(entry)

        # テーブル更新処理を実行
        with patch("sgpo_editor.gui.table_manager.QTableWidgetItem"):
            self.table_manager._update_table_contents(entries)

        # テーブル更新後に列の表示/非表示を切り替え
        toggle_column = 4  # "状態"列

        # モックをリセット
        self.table.reset_mock()

        # 現在は表示されているモック設定
        hidden_columns = set()

        def mock_is_column_hidden(idx):
            return idx in hidden_columns

        self.table.isColumnHidden.side_effect = mock_is_column_hidden

        # 手動で内部状態を設定
        self.table_manager._hidden_columns = set()

        # _apply_column_visibilityメソッドをパッチ
        with patch.object(self.table_manager, "_apply_column_visibility") as mock_apply:
            # 列の表示/非表示を切り替え
            self.table_manager.toggle_column_visibility(toggle_column)

            # 内部状態が正しく更新されたか確認
            self.assertIn(toggle_column, self.table_manager._hidden_columns)

            # _apply_column_visibilityが呼ばれたことを確認
            mock_apply.assert_called()

        # モックを一部更新
        hidden_columns.add(toggle_column)

        # もう一度切り替え
        self.table.reset_mock()
        with patch.object(self.table_manager, "_apply_column_visibility") as mock_apply:
            self.table_manager.toggle_column_visibility(toggle_column)

            # 再度切り替え後の状態を確認
            self.assertNotIn(toggle_column, self.table_manager._hidden_columns)

            # _apply_column_visibilityが呼ばれたことを確認
            mock_apply.assert_called()


if __name__ == "__main__":
    unittest.main()
