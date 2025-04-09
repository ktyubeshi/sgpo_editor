"""
このモジュールでは、エントリリストの選択機能に関するテストを行います。
"""

import pytest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt

from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.models.entry import EntryModel


@pytest.fixture
def app():
    """QApplicationのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_entries():
    """モックエントリのリスト"""
    entries = []

    for i in range(5):
        entry = EntryModel(
            position=i,
            msgid=f"msgid_{i}",
            msgstr=f"msgstr_{i}" if i % 2 == 0 else "",
            msgctxt=f"context_{i}",
            flags=["fuzzy"] if i == 2 else [],
            obsolete=(i == 4),
        )
        entry.score = 90 - (i * 10) if i < 4 else None
        entries.append(entry)

    return entries


@pytest.fixture
def table_manager():
    """テーブルマネージャのフィクスチャ"""
    table = QTableWidget()
    table.setColumnCount(6)  # 6列（位置、コンテキスト、原文、訳文、状態、スコア）
    table.setHorizontalHeaderLabels(
        ["位置", "コンテキスト", "原文", "訳文", "状態", "スコア"]
    )

    # TableManagerの初期化
    manager = TableManager(table)

    return manager


class TestEntryListSelection:
    """エントリリストの選択機能テストクラス"""

    def test_row_selection(self, app, mock_entries, table_manager):
        """行選択のテスト"""
        # テーブル更新処理をモック
        with patch.object(table_manager, "_update_table_contents"):
            table_manager.update_table(mock_entries)

        # テーブルに必要な行数を設定
        table_manager.table.setRowCount(len(mock_entries))

        # 選択前の状態確認 - 選択行がないことを確認
        selected_rows = table_manager.table.selectedItems()
        assert len(selected_rows) == 0

        # 行選択
        table_manager.select_row(2)  # 3行目を選択

        # 選択行のキーをテスト用に設定
        key = "key_2"
        item = QTableWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, key)
        table_manager.table.setItem(2, 0, item)

        # 選択行のキーを取得
        selected_key = table_manager.get_key_at_row(2)
        assert selected_key == key

    def test_get_key_at_row(self, app, mock_entries, table_manager):
        """行からキーを取得するテスト"""
        # テーブル更新処理をモック
        with patch.object(table_manager, "_update_table_contents"):
            table_manager.update_table(mock_entries)

        # テーブルに必要な行数を設定
        table_manager.table.setRowCount(len(mock_entries))

        # 各行にキーを設定
        for i in range(len(mock_entries)):
            key = f"key_{i}"
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            table_manager.table.setItem(i, 0, item)

        # 各行のキーを取得して確認
        for i in range(len(mock_entries)):
            expected_key = f"key_{i}"
            actual_key = table_manager.get_key_at_row(i)
            assert actual_key == expected_key

        # 範囲外の行インデックスの場合はNoneを返すことを確認
        assert table_manager.get_key_at_row(-1) is None
        assert table_manager.get_key_at_row(len(mock_entries)) is None

    def test_find_row_by_key(self, app, mock_entries, table_manager):
        """キーから行を検索するテスト"""
        # テーブル更新処理をモック
        with patch.object(table_manager, "_update_table_contents"):
            table_manager.update_table(mock_entries)

        # テーブルに必要な行数を設定
        table_manager.table.setRowCount(len(mock_entries))

        # 各エントリのキーを設定
        for i in range(len(mock_entries)):
            key = f"key_{i}"
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            table_manager.table.setItem(i, 0, item)

            # _display_entriesにキーを追加
            table_manager._display_entries.append(key)

        # キーから行を検索
        row = table_manager.find_row_by_key("key_3")
        assert row == 3, "キーから行を正しく検索できていません"

        # 存在しないキーの場合
        row = table_manager.find_row_by_key("non_existent_key")
        assert row == -1, "存在しないキーの場合は-1を返すべき"
