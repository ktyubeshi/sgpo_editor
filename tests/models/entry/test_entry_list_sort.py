"""エントリリストのソート機能テスト

このモジュールでは、エントリリストのソート機能に関するテストを行います。
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from PySide6.QtWidgets import QApplication, QTableWidget
from PySide6.QtCore import Qt

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.table_manager import TableManager


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
    
    # 未翻訳エントリ
    entry1 = MagicMock()
    entry1.position = 0
    entry1.msgid = "Hello"
    entry1.msgstr = ""
    entry1.msgctxt = "context1"
    entry1.fuzzy = False
    entry1.obsolete = False
    entry1.get_status.return_value = "untranslated"
    entry1.overall_quality_score.return_value = None
    entries.append(entry1)
    
    # 翻訳済みエントリ
    entry2 = MagicMock()
    entry2.position = 1
    entry2.msgid = "World"
    entry2.msgstr = "世界"
    entry2.msgctxt = "context2"
    entry2.fuzzy = False
    entry2.obsolete = False
    entry2.get_status.return_value = "translated"
    entry2.overall_quality_score.return_value = 90
    entries.append(entry2)
    
    # ファジーエントリ
    entry3 = MagicMock()
    entry3.position = 2
    entry3.msgid = "Test"
    entry3.msgstr = "テスト"
    entry3.msgctxt = "context3"
    entry3.fuzzy = True
    entry3.obsolete = False
    entry3.get_status.return_value = "fuzzy"
    entry3.overall_quality_score.return_value = 60
    entries.append(entry3)
    
    # 廃止済みエントリ
    entry4 = MagicMock()
    entry4.position = 3
    entry4.msgid = "Obsolete"
    entry4.msgstr = "廃止"
    entry4.msgctxt = "context4"
    entry4.fuzzy = False
    entry4.obsolete = True
    entry4.get_status.return_value = "obsolete"
    entry4.overall_quality_score.return_value = 70
    entries.append(entry4)
    
    # スコアなしのエントリ
    entry5 = MagicMock()
    entry5.position = 4
    entry5.msgid = "NoScore"
    entry5.msgstr = "スコアなし"
    entry5.msgctxt = "context5"
    entry5.fuzzy = False
    entry5.obsolete = False
    entry5.get_status.return_value = "translated"
    entry5.overall_quality_score.return_value = None
    entries.append(entry5)
    
    return entries


@pytest.fixture
def table_manager():
    """テーブルマネージャのフィクスチャ"""
    table = QTableWidget()
    manager = TableManager(table)
    return manager



class TestEntryListSort:
    """エントリリストのソート機能テストクラス"""
    
    def test_sort_by_position(self, app, mock_entries, table_manager):
        """位置でのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 0, Qt.SortOrder.AscendingOrder)
        positions = [entry.position for entry in sorted_entries]
        assert positions == [0, 1, 2, 3, 4], "位置による昇順ソートが正しくありません"
        
        # 降順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 0, Qt.SortOrder.DescendingOrder)
        positions = [entry.position for entry in sorted_entries]
        assert positions == [4, 3, 2, 1, 0], "位置による降順ソートが正しくありません"
    
    def test_sort_by_context(self, app, mock_entries, table_manager):
        """コンテキストでのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 1, Qt.SortOrder.AscendingOrder)
        contexts = [entry.msgctxt for entry in sorted_entries]
        expected = ["context1", "context2", "context3", "context4", "context5"]
        assert contexts == expected, "コンテキストによる昇順ソートが正しくありません"
        
        # 降順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 1, Qt.SortOrder.DescendingOrder)
        contexts = [entry.msgctxt for entry in sorted_entries]
        expected.reverse()
        assert contexts == expected, "コンテキストによる降順ソートが正しくありません"
    
    def test_sort_by_msgid(self, app, mock_entries, table_manager):
        """原文でのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 2, Qt.SortOrder.AscendingOrder)
        msgids = [entry.msgid for entry in sorted_entries]
        expected = ["Hello", "NoScore", "Obsolete", "Test", "World"]
        assert msgids == expected, "原文による昇順ソートが正しくありません"
        
        # 降順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 2, Qt.SortOrder.DescendingOrder)
        msgids = [entry.msgid for entry in sorted_entries]
        expected.reverse()
        assert msgids == expected, "原文による降順ソートが正しくありません"
    
    def test_sort_by_msgstr(self, app, mock_entries, table_manager):
        """訳文でのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 3, Qt.SortOrder.AscendingOrder)
        msgstrs = [entry.msgstr for entry in sorted_entries]
        expected = ["", "スコアなし", "テスト", "世界", "廃止"]
        assert msgstrs == expected, "訳文による昇順ソートが正しくありません"
        
        # 降順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 3, Qt.SortOrder.DescendingOrder)
        msgstrs = [entry.msgstr for entry in sorted_entries]
        expected.reverse()
        assert msgstrs == expected, "訳文による降順ソートが正しくありません"
    
    def test_sort_by_status(self, app, mock_entries, table_manager):
        """状態でのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 4, Qt.SortOrder.AscendingOrder)
        statuses = [entry.get_status() for entry in sorted_entries]
        # 未翻訳 = 0, ファジー = 1, 翻訳済み = 2, 廃止済み = 3 の順
        expected = ["untranslated", "fuzzy", "translated", "translated", "obsolete"]
        assert statuses == expected, "状態による昇順ソートが正しくありません"
        
        # 降順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 4, Qt.SortOrder.DescendingOrder)
        statuses = [entry.get_status() for entry in sorted_entries]
        expected.reverse()
        assert statuses == expected, "状態による降順ソートが正しくありません"
    
    def test_sort_by_score(self, app, mock_entries, table_manager):
        """スコアでのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 5, Qt.SortOrder.AscendingOrder)
        scores = [entry.overall_quality_score() for entry in sorted_entries]
        # スコアなしのエントリは最後になることを確認
        assert scores[:3] == [60, 70, 90], "スコアによる昇順ソートが正しくありません"
        assert all(score is None for score in scores[3:]), "スコアなしエントリの配置が正しくありません"
        
        # 降順でソート
        sorted_entries = table_manager._sort_entries(mock_entries, 5, Qt.SortOrder.DescendingOrder)
        scores = [entry.overall_quality_score() for entry in sorted_entries]
        # スコアなしのエントリは最後になることを確認
        assert scores[:3] == [90, 70, 60], "スコアによる降順ソートが正しくありません"
        assert all(score is None for score in scores[3:]), "スコアなしエントリの配置が正しくありません"
    
    def test_sort_header_click(self, app, mock_entries, table_manager):
        """ヘッダークリックによるソートテスト"""
        # テーブル更新処理をモック
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(mock_entries)
        
        # ソート状態を確認（初期状態）
        assert table_manager._current_sort_column == 0
        assert table_manager._current_sort_order == Qt.SortOrder.AscendingOrder
        
        # POFileオブジェクトをモック化
        mock_po_file = MagicMock()
        mock_po_file.get_filtered_entries.return_value = mock_entries
        
        # _get_current_poメソッドをモック化してテスト用のPOファイルを返すようにする
        with patch.object(table_manager, '_get_current_po', return_value=mock_po_file):
            # ヘッダークリックをシミュレート - update_tableをモック化
            with patch.object(table_manager, 'update_table') as mock_update:
                table_manager._on_header_clicked(1)  # コンテキスト列
                # update_tableが呼ばれたことを確認
                mock_update.assert_called_once()
                # ソート状態が更新されたことを確認
                assert table_manager._current_sort_column == 1
                assert table_manager._current_sort_order == Qt.SortOrder.AscendingOrder
            
            # 同じ列を再度クリック（降順に変更）
            with patch.object(table_manager, 'update_table') as mock_update:
                table_manager._on_header_clicked(1)
                # update_tableが呼ばれたことを確認
                mock_update.assert_called_once()
                # ソート状態が更新されたことを確認
                assert table_manager._current_sort_column == 1
                assert table_manager._current_sort_order == Qt.SortOrder.DescendingOrder
            
            # 別の列をクリック（昇順に戻る）
            with patch.object(table_manager, 'update_table') as mock_update:
                table_manager._on_header_clicked(2)  # 原文列
                # update_tableが呼ばれたことを確認
                mock_update.assert_called_once()
                # ソート状態が更新されたことを確認
                assert table_manager._current_sort_column == 2
                assert table_manager._current_sort_order == Qt.SortOrder.AscendingOrder
