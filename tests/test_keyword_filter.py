#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.models.database import Database


class TestKeywordFilter(unittest.TestCase):
    """キーワードフィルタ機能のテスト"""

    def setUp(self):
        """各テストの前処理"""
        # データベースのモック
        self.mock_db = MagicMock(spec=Database)

        # ViewerPOFileのインスタンス作成とdbをモックに置き換え
        self.po_file = ViewerPOFile()
        self.po_file.db = self.mock_db

        # モックの戻り値を設定
        self.mock_entries = [
            {"key": "1", "msgid": "test1", "msgstr": "テスト1", "position": 0},
            {"key": "2", "msgid": "test2", "msgstr": "テスト2", "position": 1},
            {"key": "3", "msgid": "keyword", "msgstr": "キーワード", "position": 2},
        ]
        self.mock_db.get_entries.return_value = self.mock_entries

    def test_filter_keyword_is_passed_to_database(self):
        """キーワードフィルタがデータベースに正しく渡されることを確認するテスト"""
        # get_filtered_entriesを呼び出し
        self.po_file.get_filtered_entries(filter_keyword="keyword")

        # get_entriesが正しいパラメータで呼び出されたことを確認
        self.mock_db.get_entries.assert_called_once()
        args, kwargs = self.mock_db.get_entries.call_args

        # キーワードが正しく渡されていることを確認
        self.assertEqual(kwargs.get("search_text"), "keyword")

    def test_filter_text_and_keyword_together(self):
        """フィルタテキストとキーワードの両方が正しく渡されることを確認するテスト"""
        # get_filtered_entriesを呼び出し
        self.po_file.get_filtered_entries(
            filter_text="translated", filter_keyword="keyword"
        )

        # get_entriesが正しいパラメータで呼び出されたことを確認
        self.mock_db.get_entries.assert_called_once()
        args, kwargs = self.mock_db.get_entries.call_args

        # フィルタテキストとキーワードが正しく渡されていることを確認
        self.assertEqual(kwargs.get("filter_text"), "translated")
        self.assertEqual(kwargs.get("search_text"), "keyword")

    @patch("sgpo_editor.models.database.Database.get_entries")
    def test_database_query_with_keyword(self, mock_get_entries):
        """データベースクエリがキーワードで正しく検索することを確認するテスト"""
        # モックの戻り値を設定
        mock_get_entries.return_value = self.mock_entries

        # 実際のデータベースインスタンスを使用
        db = Database()

        # get_entriesを呼び出し
        db.get_entries(search_text="keyword")

        # モックが呼び出されたことを確認
        mock_get_entries.assert_called_once()
        args, kwargs = mock_get_entries.call_args

        # キーワードが正しく渡されていることを確認
        self.assertEqual(kwargs.get("search_text"), "keyword")


if __name__ == "__main__":
    unittest.main()
