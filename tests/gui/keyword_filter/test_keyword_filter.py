#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.models.database import InMemoryEntryStore


class TestKeywordFilter(unittest.TestCase):
    """キーワードフィルタ機能のテスト"""

    def setUp(self):
        """各テストの前処理"""
        self.mock_db_accessor = MagicMock(spec=DatabaseAccessor)

        self.po_file = ViewerPOFileRefactored(db_accessor=self.mock_db_accessor)
        self.po_file.filter.db_accessor = self.mock_db_accessor
        self.po_file.filter.filtered_entries = []
        self.po_file.filter.cache_manager = None

        # モックの戻り値を設定
        self.mock_entries_dict = [
            {"key": "1", "msgid": "test1", "msgstr": "テスト1", "position": 0},
            {"key": "2", "msgid": "test2", "msgstr": "テスト2", "position": 1},
            {"key": "3", "msgid": "keyword", "msgstr": "キーワード", "position": 2},
        ]
        self.mock_db_accessor.advanced_search = MagicMock(
            return_value=self.mock_entries_dict
        )
        # get_statsダミーメソッドを追加
        self.mock_db_accessor.get_stats = MagicMock(return_value={})

    def test_filter_keyword_is_passed_to_database(self):
        """キーワードフィルタがデータベースに正しく渡されることを確認するテスト"""
        # get_filtered_entriesを呼び出し
        self.po_file.get_filtered_entries(filter_keyword="keyword")

        self.mock_db_accessor.advanced_search.assert_called_once()
        args, kwargs = self.mock_db_accessor.advanced_search.call_args

        # キーワードが正しく渡されていることを確認
        self.assertEqual(kwargs.get("search_text"), "keyword")

    def test_filter_text_and_keyword_together(self):
        """翻訳ステータスとキーワードの両方が正しく渡されることを確認するテスト"""
        # 翻訳ステータスを設定 (内部状態ではなくメソッド呼び出しで渡す想定)
        # self.po_file.translation_status = "translated"
        # get_filtered_entriesを呼び出し
        self.po_file.get_filtered_entries(
            filter_keyword="keyword", filter_status="translated", update_filter=True
        )

        self.mock_db_accessor.advanced_search.assert_called_once()
        args, kwargs = self.mock_db_accessor.advanced_search.call_args

        # 翻訳ステータスとキーワードが正しく渡されていることを確認
        self.assertEqual(kwargs.get("translation_status"), "translated")
        self.assertEqual(kwargs.get("search_text"), "keyword")

    def test_database_query_with_keyword(self):
        """DatabaseAccessorがキーワードで正しく検索することを確認するテスト"""
        # 実際のデータベースインスタンスとDatabaseAccessorを使用
        db_store = InMemoryEntryStore()
        db_accessor = DatabaseAccessor(db_store)

        # テストデータを追加
        test_data = [
            {"key": "1", "msgid": "test1", "msgstr": "テスト1", "position": 0},
            {"key": "2", "msgid": "test2", "msgstr": "テスト2", "position": 1},
            {"key": "3", "msgid": "keyword", "msgstr": "キーワード", "position": 2},
        ]
        db_accessor.add_entries_bulk(test_data)

        # get_filtered_entriesを呼び出し
        filtered_entries = db_accessor.get_filtered_entries(search_text="keyword")

        # 結果を検証
        self.assertEqual(len(filtered_entries), 1)
        self.assertEqual(filtered_entries[0]["msgid"], "keyword")


if __name__ == "__main__":
    unittest.main()
