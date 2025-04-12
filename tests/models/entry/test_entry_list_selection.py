"""
このモジュールでは、エントリリストの選択機能に関するテストを行います。
"""

import pytest
from unittest.mock import patch, MagicMock, call

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.gui.facades.entry_list_facade import EntryListFacade


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
    mock_po = MagicMock()
    mock_po.get_entries_by_keys.return_value = {e.key: e for e in mock_entries()}
    mock_table = MagicMock(spec=QTableWidget)
    mock_cache_manager = MagicMock(spec=EntryCacheManager)
    table_manager = TableManager(mock_table, mock_cache_manager, lambda: mock_po)

    entry_list = EntryListFacade(mock_table, table_manager, lambda: mock_po)

    return table_manager


class TestEntryListSelection:
    """エントリリストの選択機能テストクラス"""

    @pytest.fixture(autouse=True)
    def setup_method(self, qtbot, table_manager):
        self.manager = table_manager
        self.qtbot = qtbot
        # モックの初期化
        self.manager._display_entries = []
        # `TableManager` は `_entry_cache` を直接持たないため、
        # `entry_cache_manager` のモックを使用する
        self.mock_cache_manager = MagicMock(spec=EntryCacheManager)
        self.manager.entry_cache_manager = self.mock_cache_manager

    def test_row_selection(self, mock_entries):
        """行選択のテスト"""
        # テーブル更新処理をモック
        with patch.object(self.manager, "_update_table_contents"):
            self.manager.update_table(mock_entries)

        # テーブルに必要な行数を設定
        self.manager.table.setRowCount(len(mock_entries))

        # 選択前の状態確認 - 選択行がないことを確認
        selected_rows = self.manager.table.selectedItems()
        assert len(selected_rows) == 0

        # 行選択
        self.manager.select_row(2)  # 3行目を選択

        # 選択行のキーをテスト用に設定
        key = "key_2"
        item = QTableWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, key)
        self.manager.table.setItem(2, 0, item)

        # 選択行のキーを取得
        selected_key = self.manager.get_key_at_row(2)
        assert selected_key == key

    def test_get_key_at_row(self, mock_entries):
        """行からキーを取得するテスト"""
        # テーブル更新処理をモック
        with patch.object(self.manager, "_update_table_contents"):
            self.manager.update_table(mock_entries)

        # テーブルに必要な行数を設定
        self.manager.table.setRowCount(len(mock_entries))

        # 各行にキーを設定
        for i in range(len(mock_entries)):
            key = f"key_{i}"
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.manager.table.setItem(i, 0, item)

        # 各行のキーを取得して確認
        for i in range(len(mock_entries)):
            expected_key = f"key_{i}"
            actual_key = self.manager.get_key_at_row(i)
            assert actual_key == expected_key

        # 範囲外の行インデックスの場合はNoneを返すことを確認
        assert self.manager.get_key_at_row(-1) is None
        assert self.manager.get_key_at_row(len(mock_entries)) is None

    def test_find_row_by_key(self, mock_entries):
        """キーから行を検索するテスト"""
        # テーブル更新処理をモック
        with patch.object(self.manager, "_update_table_contents"):
            self.manager.update_table(mock_entries)

        # テーブルに必要な行数を設定
        self.manager.table.setRowCount(len(mock_entries))

        # 各エントリのキーを設定
        for i in range(len(mock_entries)):
            key = f"key_{i}"
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.manager.table.setItem(i, 0, item)

            # _display_entriesにキーを追加
            self.manager._display_entries.append(key)

        # キーから行を検索
        row = self.manager.find_row_by_key("key_3")
        assert row == 3, "キーから行を正しく検索できていません"

        # 存在しないキーの場合
        row = self.manager.find_row_by_key("non_existent_key")
        assert row == -1, "存在しないキーの場合は-1を返すべき"
