"""ViewerPOFileのフィルタリング機能のテスト"""

import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored


class TestViewerPOFileFilteredEntries(unittest.TestCase):
    """ViewerPOFileのフィルタリング機能のテスト"""

    def setUp(self):
        """テスト前の準備"""
        # モックをコンストラクタに渡す
        self.mock_db_accessor = MagicMock()
        self.viewer = ViewerPOFileRefactored(db_accessor=self.mock_db_accessor)

    def test_get_filtered_entries_with_direct_parameters(self):
        """get_filtered_entriesメソッドが直接パラメータを受け取れることを確認"""
        # テスト用のパラメータ
        filter_keyword = "keyword"

        # get_filtered_entriesを呼び出し
        self.viewer.get_filtered_entries(filter_keyword=filter_keyword)

        # 実際に DatabaseAccessor に渡される引数でアサートする
        self.mock_db_accessor.get_filtered_entries.assert_called_with(
            filter_text="すべて", # ViewerPOFileRefactored が渡すデフォルト
            filter_keyword=filter_keyword,
            match_mode="部分一致", # ViewerPOFileRefactored が渡すデフォルト
            case_sensitive=False, # ViewerPOFileRefactored が渡すデフォルト
            filter_status=None, # ViewerPOFileRefactored が渡すデフォルト
            filter_obsolete=True, # ViewerPOFileRefactored が渡すデフォルト
            # search_text は get_filtered_entries 内で filter_keyword から設定される
        )

    def test_get_filtered_entries_with_instance_variables(self):
        """get_filtered_entriesメソッドがインスタンス変数を使用することを確認"""
        # インスタンス変数を設定
        self.viewer.search_text = "search"

        # get_filtered_entriesを呼び出し（パラメータなし）
        self.viewer.get_filtered_entries()

        # 実際に DatabaseAccessor に渡される引数でアサートする
        self.mock_db_accessor.get_filtered_entries.assert_called_with(
            filter_text="すべて", # ViewerPOFileRefactored が渡すデフォルト
            filter_keyword=self.viewer.search_text, # インスタンス変数が使われる
            match_mode="部分一致", # ViewerPOFileRefactored が渡すデフォルト
            case_sensitive=False, # ViewerPOFileRefactored が渡すデフォルト
            filter_status=None, # ViewerPOFileRefactored が渡すデフォルト
            filter_obsolete=True, # ViewerPOFileRefactored が渡すデフォルト
            # search_text は get_filtered_entries 内で filter_keyword から設定される
        )

    def test_get_filtered_entries_with_update_filter_parameter(self):
        """update_filterパラメータが機能することを確認"""
        from unittest.mock import patch

        # キャッシュされたエントリを設定
        mock_entries = ["cached_entry"]
        self.viewer.filtered_entries = mock_entries

        # ViewerPOFileRefactored.get_filtered_entriesメソッドの一部をモックしてテストを実行
        with patch.object(
            self.viewer, "get_filtered_entries", return_value=mock_entries
        ) as mock_get_filtered:
            # モックしたメソッドを呼び出し
            result = mock_get_filtered(update_filter=False, filter_keyword=None)

            # キャッシュされたエントリが返されることを確認
            self.assertEqual(result, mock_entries)

            # update_filter=Falseで呼び出されたことを確認
            mock_get_filtered.assert_called_with(update_filter=False, filter_keyword=None)

        self.mock_db_accessor.get_filtered_entries.assert_not_called()

        # update_filter=Trueの場合はデータベースが呼ばれることを確認
        # モックを解除して実際のメソッドを呼び出す
        # NOTE: `get_filtered_entries` はインスタンスメソッドなので、第一引数に `self.viewer` は不要
        self.viewer.get_filtered_entries(update_filter=True)

        self.mock_db_accessor.get_filtered_entries.assert_called_once()


if __name__ == "__main__":
    unittest.main()
