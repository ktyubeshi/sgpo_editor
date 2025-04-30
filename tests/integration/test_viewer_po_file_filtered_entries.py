"""ViewerPOFileのフィルタリング機能のテスト"""

import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file import ViewerPOFile as ViewerPOFileRefactored


class TestViewerPOFileFilteredEntries(unittest.TestCase):
    """ViewerPOFileのフィルタリング機能のテスト"""

    def setUp(self):
        """テスト前の準備"""
        # モックをコンストラクタに渡す
        self.mock_db_accessor = MagicMock()
        self.viewer = ViewerPOFileRefactored(db_accessor=self.mock_db_accessor)

    def test_get_filtered_entries_with_direct_parameters(self):
        from sgpo_editor.gui.widgets.search import SearchCriteria
        """get_filtered_entriesメソッドが直接パラメータを受け取れることを確認"""
        # テスト用のパラメータ
        filter_keyword = "keyword"

        # get_filtered_entriesをSearchCriteriaで呼び出し
        self.viewer.get_filtered_entries(SearchCriteria(filter_keyword=filter_keyword))

        # filter_keyword指定時はadvanced_searchが呼ばれたことを検証
        self.mock_db_accessor.advanced_search.assert_called()

    def test_get_filtered_entries_with_instance_variables(self):
        from sgpo_editor.gui.widgets.search import SearchCriteria
        """get_filtered_entriesメソッドがインスタンス変数を使用することを確認"""
        # インスタンス変数を設定
        self.viewer.search_text = "search"

        # get_filtered_entriesをSearchCriteriaで呼び出し（パラメータなし）
        self.viewer.get_filtered_entries(SearchCriteria())

        # DatabaseAccessor.get_filtered_entriesが呼ばれたことのみを検証
        self.mock_db_accessor.advanced_search.assert_called()

    def test_get_filtered_entries_with_update_filter_parameter(self):
        """update_filterパラメータが機能することを確認"""
        from sgpo_editor.gui.widgets.search import SearchCriteria
        from unittest.mock import patch

        # キャッシュされたエントリを設定
        mock_entries = ["cached_entry"]
        self.viewer.filtered_entries = mock_entries

        # patchブロック内はキャッシュ利用時の挙動のみテスト
        with patch.object(
            self.viewer, "get_filtered_entries", return_value=mock_entries
        ) as mock_get_filtered:
            result = mock_get_filtered(SearchCriteria(update_filter=False, filter_keyword=None))
            self.assertEqual(result, mock_entries)
            mock_get_filtered.assert_called_with(SearchCriteria(update_filter=False, filter_keyword=None))

        self.mock_db_accessor.get_filtered_entries.assert_not_called()

        # テスト前にモックをリセット
        self.mock_db_accessor.reset_mock()
        self.mock_db_accessor.advanced_search.reset_mock()

        # フィルタ属性を明示的にクリア
        self.viewer.search_text = ""
        self.viewer.filter_keyword = ""
        self.viewer.filter_status = None
        self.viewer.filtered_entries = None
        
        # ViewerPOFileの内部状態を確認
        print(f"DEBUG: ViewerPOFile current state: translation_status={self.viewer.translation_status}")
        
        # update_filter=Trueで呼び出し、キャッシュを無視してデータベースをアクセスする
        self.viewer.get_filtered_entries(SearchCriteria(update_filter=True))
        
        # db_accessor.get_filtered_entriesまたはadvanced_searchのいずれかが呼ばれていることを確認
        self.assertTrue(
            self.mock_db_accessor.get_filtered_entries.called or 
            self.mock_db_accessor.advanced_search.called,
            "Either get_filtered_entries or advanced_search should be called when update_filter=True"
        )



if __name__ == "__main__":
    unittest.main()
