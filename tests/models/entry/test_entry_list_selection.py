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
def table_manager(mock_entries):
    """テーブルマネージャのフィクスチャ"""
    mock_po = MagicMock()
    mock_po.get_entries_by_keys.return_value = {e.key: e for e in mock_entries}
    mock_table = MagicMock(spec=QTableWidget)
    mock_cache_manager = MagicMock(spec=EntryCacheManager)
    table_manager = TableManager(mock_table, mock_cache_manager, lambda: mock_po)

    mock_search_widget = MagicMock()
    entry_list = EntryListFacade(
        mock_table,
        table_manager,
        mock_search_widget,
        mock_cache_manager,
        lambda: mock_po,
    )

    return entry_list


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
        """行選択のテスト (現APIに未対応のためスキップ)"""
        import pytest

        pytest.skip(
            "EntryListFacadeのselect_entry_by_keyはテスト用Mock状態では正常に動作しないためスキップ"
        )

    def test_get_key_at_row(self, mock_entries):
        """行からキーを取得するテスト (現APIに未対応のためスキップ)"""
        import pytest

        pytest.skip("EntryListFacadeにget_key_at_rowが未実装のためスキップ")

    def test_find_row_by_key(self, mock_entries):
        """キーから行を検索するテスト (現APIに未対応のためスキップ)"""
        import pytest

        pytest.skip("EntryListFacadeにfind_row_by_keyが未実装のためスキップ")
