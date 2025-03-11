"""エントリデータ構造の検証テスト"""
import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file import ViewerPOFile


class TestEntryStructure(unittest.TestCase):
    """エントリデータ構造の検証テスト"""

    def setUp(self):
        """テスト前の準備"""
        self.viewer = ViewerPOFile()
        # データベースをモック化
        self.viewer.db = MagicMock()
        
    def test_entry_structure(self):
        """エントリが期待される構造を持っていることを確認"""
        # モックエントリを設定
        mock_entries = [
            {"key": "1", "msgid": "test1", "msgstr": "テスト1", "flags": []},
            {"key": "2", "msgid": "test2", "msgstr": "", "flags": ["fuzzy"]},
            {"key": "3", "msgid": "test3", "msgstr": "", "flags": []}
        ]
        
        # get_filtered_entriesをモック化
        self.viewer.db.get_entries.return_value = mock_entries
        
        # フィルタされたエントリを取得
        entries = self.viewer.get_filtered_entries()
        
        # 各エントリが必要なキーを持っていることを確認
        required_keys = ["key", "msgid", "msgstr", "flags"]
        for entry in entries:
            for key in required_keys:
                self.assertIn(key, entry, f"エントリに必要なキー '{key}' がありません")
                
    def test_entry_access_pattern(self):
        """エントリへのアクセスパターンが正しく機能することを確認"""
        # モックエントリを設定
        mock_entries = [
            {"key": "1", "msgid": "test1", "msgstr": "テスト1", "flags": []},
        ]
        
        # get_filtered_entriesをモック化
        self.viewer.db.get_entries.return_value = mock_entries
        
        # フィルタされたエントリを取得
        entries = self.viewer.get_filtered_entries()
        
        # 実際のコードで使用されるアクセスパターンをテスト
        try:
            # 辞書アクセス
            entry_key = entries[0]["key"]
            entry_msgid = entries[0]["msgid"]
            self.assertEqual(entry_key, "1")
            self.assertEqual(entry_msgid, "test1")
            
            # 属性アクセス
            self.assertEqual(entries[0].key, "1")
            self.assertEqual(entries[0].msgid, "test1")
                
        except Exception as e:
            self.fail(f"エントリへのアクセス中に予期しないエラーが発生しました: {e}")


if __name__ == "__main__":
    unittest.main()
