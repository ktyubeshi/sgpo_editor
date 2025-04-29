"""エントリリスト表示の統合テスト"""

import pytest
from pathlib import Path

from PySide6.QtWidgets import QApplication, QTableWidget

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.widgets.search import SearchWidget
from sgpo_editor.gui.facades.entry_list_facade import EntryListFacade
from unittest.mock import MagicMock
from tests.core.filter.test_filter_reset_advanced import create_mock_entry_dicts


@pytest.fixture
def app():
    """QApplicationのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_po_path():
    """サンプルPOファイルのパス"""
    current_dir = Path(__file__).parent
    data_dir = current_dir / "data" / "test_sgpo" / "common"
    po_path = data_dir / "sample.po"

    # サンプルファイルが存在しない場合は作成
    if not po_path.exists():
        po_path.parent.mkdir(parents=True, exist_ok=True)
        with open(po_path, "w", encoding="utf-8") as f:
            f.write("""msgid ""
msgstr ""
"Project-Id-Version: Test\\n"
"POT-Creation-Date: 2023-01-01 00:00+0900\\n"
"PO-Revision-Date: 2023-01-01 00:00+0900\\n"
"Language: ja\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

msgid "Hello"
msgstr ""

msgid "World"
msgstr "世界"

#, fuzzy
msgid "Test"
msgstr "テスト"

#~ msgid "Obsolete"
#~ msgstr "廃止"
""")

    return po_path


@pytest.mark.integration
@pytest.mark.asyncio  # asyncioを使用するため追加
async def test_entry_list_status_display(app, sample_po_path):
    """エントリリストのステータス表示統合テスト"""
    # テーブルとテーブルマネージャの用意
    mock_po = MagicMock()
    entries = create_mock_entry_dicts(4) # 例として4件作成

    mock_po.get_entries_by_keys.return_value = {e.key: e for e in entries}
    mock_table = MagicMock(spec=QTableWidget)
    mock_cache_manager = MagicMock(spec=EntryCacheManager)
    table_manager = TableManager(mock_table, mock_cache_manager, lambda: mock_po)

    # EntryListFacade の初期化引数を修正
    EntryListFacade(
        mock_table, 
        table_manager, 
        MagicMock(spec=SearchWidget), # SearchWidget のモックを追加
        lambda: mock_po # get_current_po を渡す
    )

    # POファイルの読み込み
    po_file = ViewerPOFileRefactored()
    await po_file.load(sample_po_path)  # 非同期メソッドのため await を追加

    # エントリの取得
    entries = po_file.get_filtered_entries()

    # テーブル更新
    table_manager.update_table(entries)

    # 行数チェック
    assert mock_table.rowCount() == 4, (
        f"Expected 4 rows, got {mock_table.rowCount()}"
    )

    # 状態列の内容チェック
    states = [mock_table.item(i, 4).text() for i in range(mock_table.rowCount())]

    # 期待される状態値があるか確認
    assert "未翻訳" in states, "未翻訳状態が表示されていません"
    assert "翻訳済み" in states, "翻訳済み状態が表示されていません"
    assert "ファジー" in states, "ファジー状態が表示されていません"
    assert "廃止" in states, "廃止状態が表示されていません"
