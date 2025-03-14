"""テーブルのスコア表示に関するテスト"""

import sys
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget
from PySide6.QtGui import QColor
from unittest.mock import MagicMock, patch

from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.models.evaluation_state import EvaluationState


@pytest.fixture
def app():
    """QApplicationのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def table_widget(app):
    """テスト用のテーブルウィジェット"""
    return QTableWidget()


@pytest.fixture
def entry_data():
    """テスト用のエントリデータを生成する"""
    entries = []
    
    # スコアなしのエントリ
    entry1 = MagicMock(spec=EntryModel)
    entry1.position = 0
    entry1.key = "entry1"
    entry1.msgid = "Source text 1"
    entry1.msgstr = "Translated text 1"
    entry1.msgctxt = None
    entry1.obsolete = False
    entry1.fuzzy = False
    entry1.get_status.return_value = "翻訳済み"
    entry1.overall_quality_score.return_value = None
    entries.append(entry1)
    
    # 高スコアのエントリ (80以上)
    entry2 = MagicMock(spec=EntryModel)
    entry2.position = 1
    entry2.key = "entry2"
    entry2.msgid = "Source text 2"
    entry2.msgstr = "Translated text 2"
    entry2.msgctxt = None
    entry2.obsolete = False
    entry2.fuzzy = False
    entry2.get_status.return_value = "翻訳済み"
    entry2.overall_quality_score.return_value = 90
    entries.append(entry2)
    
    # 中スコアのエントリ (60-79)
    entry3 = MagicMock(spec=EntryModel)
    entry3.position = 2
    entry3.key = "entry3"
    entry3.msgid = "Source text 3"
    entry3.msgstr = "Translated text 3"
    entry3.msgctxt = None
    entry3.obsolete = False
    entry3.fuzzy = False
    entry3.get_status.return_value = "翻訳済み"
    entry3.overall_quality_score.return_value = 70
    entries.append(entry3)
    
    # 低スコアのエントリ (60未満)
    entry4 = MagicMock(spec=EntryModel)
    entry4.position = 3
    entry4.key = "entry4"
    entry4.msgid = "Source text 4"
    entry4.msgstr = "Translated text 4"
    entry4.msgctxt = None
    entry4.obsolete = False
    entry4.fuzzy = False
    entry4.get_status.return_value = "翻訳済み"
    entry4.overall_quality_score.return_value = 40
    entries.append(entry4)
    
    return entries


def test_table_score_column_display(table_widget, entry_data):
    """テーブルのスコア列が正しく表示されるかテスト"""
    # テーブルマネージャの初期化
    table_manager = TableManager(table_widget)
    
    # エントリの更新
    table_manager._update_table_contents(entry_data)
    
    # テーブルの行数を確認
    assert table_widget.rowCount() == 4, "テーブルに4行のエントリが表示されるべき"
    
    # スコア列が存在することを確認
    assert table_widget.columnCount() >= 6, "テーブルに少なくとも6列あるべき"
    assert table_manager.get_column_name(5) == "Score", "6列目はScore列であるべき"
    
    # スコアの表示内容を確認
    assert table_widget.item(0, 5).text() == "-", "スコアなしのエントリは'-'と表示されるべき"
    assert table_widget.item(1, 5).text() == "90", "高スコアのエントリは数値が表示されるべき"
    assert table_widget.item(2, 5).text() == "70", "中スコアのエントリは数値が表示されるべき"
    assert table_widget.item(3, 5).text() == "40", "低スコアのエントリは数値が表示されるべき"
    
    # スコアに応じた背景色を確認
    light_green = QColor(200, 255, 200)  # 薄緑
    light_yellow = QColor(255, 255, 200)  # 薄黄
    light_red = QColor(255, 200, 200)  # 薄赤
    
    assert table_widget.item(1, 5).background().color().rgb() == light_green.rgb(), "高スコアのエントリは薄緑で表示されるべき"
    assert table_widget.item(2, 5).background().color().rgb() == light_yellow.rgb(), "中スコアのエントリは薄黄で表示されるべき"
    assert table_widget.item(3, 5).background().color().rgb() == light_red.rgb(), "低スコアのエントリは薄赤で表示されるべき"


def test_table_score_sorting(table_widget, entry_data):
    """スコアによるソートが正しく機能するかテスト"""
    # テーブルマネージャの初期化
    table_manager = TableManager(table_widget)
    
    # エントリの更新
    table_manager.update_table(entry_data, None, 0, Qt.SortOrder.AscendingOrder)
    
    # _sort_entries_by_scoreメソッドをテスト
    # 昇順ソートでは、スコアが低い順に並ぶはず
    sorted_entries_asc = table_manager._sort_entries_by_score(entry_data, Qt.SortOrder.AscendingOrder)
    
    # スコア値を直接取得して確認
    scores_asc = [entry.overall_quality_score() if hasattr(entry, 'overall_quality_score') else None 
                 for entry in sorted_entries_asc]
    
    print(f"Ascending order scores: {scores_asc}")
    
    # 昇順なので、値があるスコアが低い順から並び、Noneは最後
    # 最初の三つのスコアが昇順になっていることを確認
    assert scores_asc[0] == 40, "昇順ソートの最初は最低スコア(40)のエントリ"
    assert scores_asc[1] == 70, "昇順ソートの2番目は中間スコア(70)のエントリ"
    assert scores_asc[2] == 90, "昇順ソートの3番目は最高スコア(90)のエントリ"
    assert scores_asc[3] is None, "昇順ソートの最後はスコアなしのエントリ"
    
    # 降順ソートでは、スコアが高い順に並ぶはず
    sorted_entries_desc = table_manager._sort_entries_by_score(entry_data, Qt.SortOrder.DescendingOrder)
    
    # スコア値を直接取得して確認
    scores_desc = [entry.overall_quality_score() if hasattr(entry, 'overall_quality_score') else None 
                  for entry in sorted_entries_desc]
    
    print(f"Descending order scores: {scores_desc}")
    
    # 降順なので、値があるスコアが高い順から並び、Noneは最後
    assert scores_desc[0] == 90, "降順ソートの最初は最高スコア(90)のエントリ"
    assert scores_desc[1] == 70, "降順ソートの2番目は中間スコア(70)のエントリ"
    assert scores_desc[2] == 40, "降順ソートの3番目は最低スコア(40)のエントリ"
    assert scores_desc[3] is None, "降順ソートの最後はスコアなしのエントリ"


def test_table_score_column_visibility(table_widget):
    """スコア列の表示/非表示が正しく動作するかテスト"""
    # テーブルマネージャの初期化
    table_manager = TableManager(table_widget)
    
    # 初期状態では列は表示されているはず
    assert not table_widget.isColumnHidden(5), "初期状態ではスコア列は表示されているべき"
    
    # スコア列を非表示にする
    table_manager.toggle_column_visibility(5)
    assert table_widget.isColumnHidden(5), "列非表示設定後はスコア列は非表示になるべき"
    
    # スコア列を再度表示する
    table_manager.toggle_column_visibility(5)
    assert not table_widget.isColumnHidden(5), "列表示設定後はスコア列は表示されるべき"
