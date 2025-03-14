"""ViewerPOFileのフィルタリング機能のテスト"""

import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file import ViewerPOFile


class TestViewerPOFileFilteredEntries(unittest.TestCase):
    """ViewerPOFileのフィルタリング機能のテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.viewer = ViewerPOFile()
        # データベースをモック化
        self.viewer.db = MagicMock()

    def test_get_filtered_entries_with_direct_parameters(self):
        """get_filtered_entriesメソッドが直接パラメータを受け取れることを確認"""
        # テスト用のパラメータ
        filter_text = "test"
        filter_keyword = "keyword"

        # get_filtered_entriesを呼び出し
        self.viewer.get_filtered_entries(
            filter_text=filter_text, filter_keyword=filter_keyword
        )

        # データベースのget_entriesが正しいパラメータで呼ばれることを確認
        self.viewer.db.get_entries.assert_called_with(
            filter_text=filter_text,
            search_text=filter_keyword,  # filter_keywordはsearch_textとして渡される
            sort_column=self.viewer.sort_column,
            sort_order=self.viewer.sort_order,
            flag_conditions=self.viewer.flag_conditions,
            translation_status=self.viewer.translation_status,
        )

    def test_get_filtered_entries_with_instance_variables(self):
        """get_filtered_entriesメソッドがインスタンス変数を使用することを確認"""
        # インスタンス変数を設定
        self.viewer.filter_text = "test"
        self.viewer.search_text = "search"

        # get_filtered_entriesを呼び出し（パラメータなし）
        self.viewer.get_filtered_entries()

        # データベースのget_entriesが正しいパラメータで呼ばれることを確認
        self.viewer.db.get_entries.assert_called_with(
            filter_text=self.viewer.filter_text,
            search_text=self.viewer.search_text,
            sort_column=self.viewer.sort_column,
            sort_order=self.viewer.sort_order,
            flag_conditions=self.viewer.flag_conditions,
            translation_status=self.viewer.translation_status,
        )

    def test_get_filtered_entries_with_update_filter_parameter(self):
        """update_filterパラメータが機能することを確認"""
        # キャッシュされたエントリを設定
        self.viewer.filtered_entries = ["cached_entry"]

        # update_filter=Falseでget_filtered_entriesを呼び出し
        result = self.viewer.get_filtered_entries(update_filter=False)

        # データベースのget_entriesが呼ばれないことを確認
        self.viewer.db.get_entries.assert_not_called()

        # キャッシュされたエントリが返されることを確認
        self.assertEqual(result, ["cached_entry"])

        # update_filter=Trueでget_filtered_entriesを呼び出し
        self.viewer.get_filtered_entries(update_filter=True)

        # データベースのget_entriesが呼ばれることを確認
        self.viewer.db.get_entries.assert_called_once()


if __name__ == "__main__":
    unittest.main()
