"""エントリリスト表示の統合テスト"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QTableWidget

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.file_handler import FileHandler
from sgpo_editor.gui.table_manager import TableManager


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
            f.write('''msgid ""
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
''')
    
    return po_path


@pytest.mark.integration
def test_entry_list_status_display(app, sample_po_path):
    """エントリリストのステータス表示統合テスト"""
    # テーブルとテーブルマネージャの用意
    table_widget = QTableWidget()
    table_manager = TableManager(table_widget)
    
    # POファイルの読み込み
    po_file = ViewerPOFile()
    po_file.load(sample_po_path)
    
    # エントリの取得
    entries = po_file.get_filtered_entries()
    
    # テーブル更新
    table_manager.update_table(entries)
    
    # 行数チェック
    assert table_widget.rowCount() == 4, f"Expected 4 rows, got {table_widget.rowCount()}"
    
    # 状態列の内容チェック
    states = [table_widget.item(i, 4).text() for i in range(table_widget.rowCount())]
    
    # 期待される状態値があるか確認
    assert "未翻訳" in states, "未翻訳状態が表示されていません"
    assert "翻訳済み" in states, "翻訳済み状態が表示されていません"
    assert "ファジー" in states, "ファジー状態が表示されていません"
    assert "廃止済み" in states, "廃止済み状態が表示されていません"
