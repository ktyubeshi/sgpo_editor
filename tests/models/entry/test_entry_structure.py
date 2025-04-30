"""エントリデータ構造の検証テスト"""

import unittest
from unittest.mock import MagicMock, patch

from sgpo_editor.core.viewer_po_file import ViewerPOFile as ViewerPOFileRefactored
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.gui.widgets.search import SearchCriteria


class TestEntryStructure(unittest.TestCase):
    """エントリデータ構造の検証テスト"""

    def setUp(self):
        """テスト前の準備"""
        # モックをコンストラクタに渡す
        self.mock_db_accessor = MagicMock()
        self.mock_cache_manager = MagicMock()
        self.viewer = ViewerPOFileRefactored(
            db_accessor=self.mock_db_accessor, cache_manager=self.mock_cache_manager
        )
        # _force_filter_update は不要

    def test_entry_structure(self):
        """エントリが期待される構造を持っていることを確認"""
        # モックエントリを設定
        mock_entries = [
            {"key": "1", "msgid": "test1", "msgstr": "テスト1", "flags": []},
            {"key": "2", "msgid": "test2", "msgstr": "", "flags": ["fuzzy"]},
            {"key": "3", "msgid": "test3", "msgstr": "", "flags": []},
        ]

        # get_filtered_entriesをモック化
        self.mock_db_accessor.get_filtered_entries.return_value = mock_entries

        # フィルタされたエントリを取得
        entries = self.viewer.get_filtered_entries(SearchCriteria())

        # 各エントリが必要なキーを持っていることを確認
        required_keys = ["key", "msgid", "msgstr", "flags"]
        for entry in entries:
            for key in required_keys:
                self.assertTrue(
                    hasattr(entry, key), f"エントリに必要な属性 '{key}' がありません"
                )

    def test_entry_access_pattern(self):
        """エントリへのアクセスパターンが正しく機能することを確認"""
        # モックエントリを設定
        mock_entries = [
            EntryModel(key="1", msgid="test1", msgstr="テスト1", flags=[]),
        ]

        # ViewerPOFileのget_filtered_entriesメソッドを直接モック化
        original_get_filtered = self.viewer.get_filtered_entries
        self.viewer.get_filtered_entries = MagicMock(return_value=mock_entries)

        try:
            # 実際のコードで使用されるアクセスパターンをテスト
            # 辞書アクセス
            from sgpo_editor.utils.entry_utils import get_entry_key
            entries = self.viewer.get_filtered_entries(SearchCriteria())
            entry_key = get_entry_key(entries[0])
            entry_msgid = entries[0].msgid
            self.assertEqual(entry_key, "1")
            self.assertEqual(entry_msgid, "test1")

            # 属性アクセス
            self.assertEqual(entries[0].key, "1")
            self.assertEqual(entries[0].msgstr, "テスト1")

        except Exception as e:
            self.fail(
                f"エントリへのアクセス中に予期しないエラーが発生しました: {e}"
            )
        finally:
            # テスト後に元のメソッドに戻す
            self.viewer.get_filtered_entries = original_get_filtered


if __name__ == "__main__":
    unittest.main()
