"""テーブルの状態表示に関するテスト"""

import pytest
from PySide6.QtWidgets import QApplication, QTableWidget
from unittest.mock import MagicMock

from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.core.constants import TranslationStatus
from sgpo_editor.i18n import translate
from sgpo_editor.core.cache_manager import EntryCacheManager


@pytest.fixture
def app():
    """QApplicationのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def table_widget(app):
    """テーブルウィジェットのフィクスチャ"""
    table = QTableWidget()
    mock_cache_manager = MagicMock(spec=EntryCacheManager)
    TableManager(table, mock_cache_manager)
    yield table


@pytest.fixture
def entry_data():
    """テスト用エントリデータ"""
    entries = [
        EntryModel(key="key1", msgid="test1", msgstr="", position=0),  # 未翻訳
        EntryModel(key="key2", msgid="test2", msgstr="テスト2", position=1),  # 翻訳済み
        EntryModel(
            key="key3", msgid="test3", msgstr="テスト3", flags=["fuzzy"], position=2
        ),  # ファジー
        EntryModel(
            key="key4", msgid="test4", msgstr="", obsolete=True, position=3
        ),  # 廃止済み
    ]
    return entries


def test_table_status_column_display(table_widget, entry_data):
    """テーブルの状態列が正しく表示されるかテスト"""
    # TableManagerの初期化
    table_manager = TableManager(table_widget)

    # モックのget_current_po関数を設定
    mock_get_current_po = MagicMock()
    table_manager._get_current_po = mock_get_current_po

    # テーブル更新
    table_manager.update_table(entry_data)

    # 各行の状態セルの内容を確認 - 翻訳された値を期待
    assert table_widget.item(0, 4).text() == translate(TranslationStatus.UNTRANSLATED)
    assert table_widget.item(1, 4).text() == translate(TranslationStatus.TRANSLATED)
    assert table_widget.item(2, 4).text() == translate(TranslationStatus.FUZZY)
    assert table_widget.item(3, 4).text() == translate(TranslationStatus.OBSOLETE)


@pytest.fixture
def table_manager(qtbot):
    table = QTableWidget()
    # モックオブジェクトを引数に追加
    mock_cache_manager = MagicMock(spec=EntryCacheManager)
    mock_sort_callback = MagicMock()
    manager = TableManager(
        table, mock_cache_manager, sort_request_callback=mock_sort_callback
    )
    qtbot.addWidget(table)
    return manager, table
