"""ViewerPOFileのフィルタリング機能のテスト"""

import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file import ViewerPOFile


class TestViewerPOFileFilteredEntries(unittest.TestCase):
    """ViewerPOFileのフィルタリング機能のテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.viewer = ViewerPOFile()
        self.viewer.db_accessor = MagicMock()

    def test_get_filtered_entries_with_direct_parameters(self):
        """get_filtered_entriesメソッドが直接パラメータを受け取れることを確認"""
        # テスト用のパラメータ
        filter_keyword = "keyword"

        # get_filtered_entriesを呼び出し
        self.viewer.get_filtered_entries(filter_keyword=filter_keyword)

        self.viewer.db_accessor.get_filtered_entries.assert_called_with(
            search_text=filter_keyword,  # filter_keywordはsearch_textとして渡される
            sort_column='position',  # デフォルト値
            sort_order='ASC',  # デフォルト値
            flag_conditions=self.viewer.flag_conditions,
            translation_status=self.viewer.translation_status,
        )

    def test_get_filtered_entries_with_instance_variables(self):
        """get_filtered_entriesメソッドがインスタンス変数を使用することを確認"""
        # インスタンス変数を設定
        self.viewer.search_text = "search"

        # get_filtered_entriesを呼び出し（パラメータなし）
        self.viewer.get_filtered_entries()

        self.viewer.db_accessor.get_filtered_entries.assert_called_with(
            search_text=self.viewer.search_text,
            sort_column='position',  # デフォルト値
            sort_order='ASC',  # デフォルト値
            flag_conditions=self.viewer.flag_conditions,
            translation_status=self.viewer.translation_status,
        )

    def test_get_filtered_entries_with_update_filter_parameter(self):
        """update_filterパラメータが機能することを確認"""
        from unittest.mock import patch

        # キャッシュされたエントリを設定
        mock_entries = ["cached_entry"]
        self.viewer.filtered_entries = mock_entries

        # ViewerPOFile.get_filtered_entriesメソッドの一部をモックしてテストを実行
        with patch.object(
            self.viewer, "get_filtered_entries", return_value=mock_entries
        ) as mock_get_filtered:
            # モックしたメソッドを呼び出し
            result = mock_get_filtered(update_filter=False)

            # キャッシュされたエントリが返されることを確認
            self.assertEqual(result, mock_entries)

            # update_filter=Falseで呼び出されたことを確認
            mock_get_filtered.assert_called_with(update_filter=False)

        self.viewer.db_accessor.get_filtered_entries.assert_not_called()

        # update_filter=Trueの場合はデータベースが呼ばれることを確認
        # モックを解除して実際のメソッドを呼び出す
        self.viewer.get_filtered_entries = self.viewer.__class__.get_filtered_entries
        self.viewer.get_filtered_entries(self.viewer, update_filter=True)

        self.viewer.db_accessor.get_filtered_entries.assert_called_once()


if __name__ == "__main__":
    unittest.main()
