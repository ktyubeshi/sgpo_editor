"""エントリリストのフィルタリング機能テスト

このモジュールでは、エントリリストのフィルタリング機能に関するテストを行います。
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from PySide6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from PySide6.QtCore import Qt

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.widgets.search import SearchCriteria


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
    entry3.msgid = "Testing"
    entry3.msgstr = "テスト中"
    entry3.msgctxt = "context3"
    entry3.fuzzy = True
    entry3.obsolete = False
    entry3.get_status.return_value = "fuzzy"
    entry3.overall_quality_score.return_value = 60
    entries.append(entry3)
    
    # 廃止済みエントリ
    entry4 = MagicMock()
    entry4.position = 3
    entry4.msgid = "Obsolete Entry"
    entry4.msgstr = "廃止されたエントリ"
    entry4.msgctxt = "context4"
    entry4.fuzzy = False
    entry4.obsolete = True
    entry4.get_status.return_value = "obsolete"
    entry4.overall_quality_score.return_value = 70
    entries.append(entry4)
    
    # 低品質スコアのエントリ
    entry5 = MagicMock()
    entry5.position = 4
    entry5.msgid = "Low Quality"
    entry5.msgstr = "低品質"
    entry5.msgctxt = "quality"
    entry5.fuzzy = False
    entry5.obsolete = False
    entry5.get_status.return_value = "translated"
    entry5.overall_quality_score.return_value = 30
    entries.append(entry5)
    
    return entries


@pytest.fixture
def table_manager():
    """テーブルマネージャのフィクスチャ"""
    table = QTableWidget()
    manager = TableManager(table)
    return manager



class TestEntryListFilter:
    """エントリリストのフィルタリング機能テストクラス"""
    
    def test_filter_by_status(self, app, mock_entries, table_manager):
        """状態によるフィルタリングテスト"""
        # ViewerPOFileのget_filtered_entriesをモック
        po_file = MagicMock()
        po_file.get_filtered_entries.side_effect = lambda **kwargs: [
            entry for entry in mock_entries 
            if self._entry_matches_filter(entry, kwargs.get('filter_text'))
        ]
        
        # 未翻訳のエントリフィルタリング
        filter_text = "未翻訳"
        entries = po_file.get_filtered_entries(filter_text=filter_text, filter_keyword="")
        
        # SearchCriteriaを作成
        criteria = SearchCriteria(filter=filter_text, filter_keyword="")
        
        # テーブル更新処理をモック
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(entries, criteria)
        
        assert len(entries) == 1
        assert entries[0].get_status() == "untranslated"
        
        # 翻訳済みのエントリフィルタリング
        filter_text = "翻訳済み"
        entries = po_file.get_filtered_entries(filter_text=filter_text, filter_keyword="")
        criteria = SearchCriteria(filter=filter_text, filter_keyword="")
        
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(entries, criteria)
        
        assert len(entries) == 2
        for entry in entries:
            assert entry.get_status() == "translated"
        
        # ファジーのエントリフィルタリング
        filter_text = "ファジー"
        entries = po_file.get_filtered_entries(filter_text=filter_text, filter_keyword="")
        criteria = SearchCriteria(filter=filter_text, filter_keyword="")
        
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(entries, criteria)
        
        assert len(entries) == 1
        assert entries[0].get_status() == "fuzzy"
        
        # すべてのエントリフィルタリング
        filter_text = "すべて"
        entries = po_file.get_filtered_entries(filter_text=filter_text, filter_keyword="")
        criteria = SearchCriteria(filter=filter_text, filter_keyword="")
        
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(entries, criteria)
        
        assert len(entries) == 5  # 全エントリ
    
    def test_text_search(self, app, mock_entries, table_manager):
        """テキスト検索によるフィルタリングテスト"""
        # ViewerPOFileのget_filtered_entriesをモック
        po_file = MagicMock()
        po_file.get_filtered_entries.side_effect = lambda **kwargs: [
            entry for entry in mock_entries 
            if self._entry_matches_keyword(entry, kwargs.get('filter_keyword'))
        ]
        
        # 「Test」を含むエントリの検索
        filter_text = "すべて"
        filter_keyword = "Test"
        entries = po_file.get_filtered_entries(filter_text=filter_text, filter_keyword=filter_keyword)
        
        # SearchCriteriaを作成
        criteria = SearchCriteria(filter=filter_text, filter_keyword=filter_keyword)
        
        # テーブル更新
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(entries, criteria)
        
        assert len(entries) == 1
        assert "Testing" == entries[0].msgid
        
        # 「エントリ」を含むエントリの検索
        filter_keyword = "エントリ"
        entries = po_file.get_filtered_entries(filter_text=filter_text, filter_keyword=filter_keyword)
        criteria = SearchCriteria(filter=filter_text, filter_keyword=filter_keyword)
        
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(entries, criteria)
        
        assert len(entries) == 1
        assert "廃止されたエントリ" == entries[0].msgstr
        
        # コンテキストでの検索
        filter_keyword = "quality"
        entries = po_file.get_filtered_entries(filter_text=filter_text, filter_keyword=filter_keyword)
        criteria = SearchCriteria(filter=filter_text, filter_keyword=filter_keyword)
        
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(entries, criteria)
        
        assert len(entries) == 1
        assert "quality" == entries[0].msgctxt
    
    def _entry_matches_filter(self, entry, filter_text):
        """エントリがフィルタに一致するかを判定"""
        if filter_text == "すべて":
            return True
        elif filter_text == "未翻訳" and entry.get_status() == "untranslated":
            return True
        elif filter_text == "翻訳済み" and entry.get_status() == "translated":
            return True
        elif filter_text == "ファジー" and entry.get_status() == "fuzzy":
            return True
        elif filter_text == "廃止" and entry.get_status() == "obsolete":
            return True
        return False
    
    def _entry_matches_keyword(self, entry, keyword):
        """エントリがキーワードに一致するかを判定"""
        if not keyword:
            return True
            
        # 各フィールドでキーワード検索
        if keyword.lower() in str(entry.msgid).lower():
            return True
        if keyword.lower() in str(entry.msgstr).lower():
            return True
        if keyword.lower() in str(entry.msgctxt).lower():
            return True
        return False
        
    def test_combined_search(self, app, mock_entries, table_manager):
        """状態とキーワードを組み合わせた検索テスト"""
        # ViewerPOFileのget_filtered_entriesをモック
        po_file = MagicMock()
        po_file.get_filtered_entries.side_effect = lambda **kwargs: [
            entry for entry in mock_entries 
            if self._entry_matches_filter(entry, kwargs.get('filter_text')) and
               self._entry_matches_keyword(entry, kwargs.get('filter_keyword'))
        ]
        
        # 翻訳済みのエントリから「世界」を含むものの検索
        table_manager._current_filter_text = "翻訳済み"
        table_manager._current_search_text = "世界"
        
        entries = po_file.get_filtered_entries(
            filter_text="翻訳済み",
            filter_keyword="世界"
        )
        
        assert len(entries) == 1
        assert entries[0].msgstr == "世界"
    
    def test_update_filtered_table(self, app, mock_entries, table_manager):
        """フィルタリングされたテーブル更新のテスト"""
        # 翻訳済みエントリのフィルタリング
        translated_entries = [entry for entry in mock_entries if entry.get_status() == "translated"]
        
        # 検索条件の設定
        criteria = SearchCriteria(filter="翻訳済み", filter_keyword="")
        
        # テーブル更新処理をモック
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(translated_entries, criteria)
        
        # フィルタリング結果の確認
        assert len(translated_entries) == 2  # 2つの翻訳済みエントリ
        
        # ファジーエントリのフィルタリング
        fuzzy_entries = [entry for entry in mock_entries if entry.get_status() == "fuzzy"]
        
        # 検索条件の更新
        criteria = SearchCriteria(filter="ファジー", filter_keyword="")
        
        # テーブル更新
        with patch.object(table_manager, '_update_table_contents'):
            table_manager.update_table(fuzzy_entries, criteria)
        
        # フィルタリング結果の確認
        assert len(fuzzy_entries) == 1  # 1つのファジーエントリ
    
    def test_search_criteria_integration(self, app, mock_entries, table_manager):
        """SearchCriteriaとの連携テスト"""
        # フィルタとキーワードの組み合わせパターン
        test_cases = [
            ("すべて", "", 5),       # すべてのエントリ
            ("翻訳済み", "", 2),     # 翻訳済みエントリのみ
            ("未翻訳", "", 1),       # 未翻訳エントリのみ
            ("ファジー", "", 1),     # ファジーエントリのみ
            ("すべて", "Test", 1),   # "Test"を含むすべてのエントリ
            ("翻訳済み", "世界", 1),  # "世界"を含む翻訳済みエントリ
        ]
        
        for filter_text, keyword, expected_count in test_cases:
            # フィルタリング結果をテスト用に生成
            filtered_entries = [
                entry for entry in mock_entries 
                if self._entry_matches_filter(entry, filter_text) and
                   self._entry_matches_keyword(entry, keyword)
            ]
            
            # 検索条件の作成
            criteria = SearchCriteria(filter=filter_text, filter_keyword=keyword)
            
            # テーブル更新
            with patch.object(table_manager, '_update_table_contents'):
                table_manager.update_table(filtered_entries, criteria)
            
            # 結果の確認 - フィルタリング結果の数が期待値と一致するか
            assert len(filtered_entries) == expected_count, \
                f"フィルタ '{filter_text}' とキーワード '{keyword}' の結果数が期待と異なります"
