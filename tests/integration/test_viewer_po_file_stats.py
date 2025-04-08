"""ViewerPOFileの統計情報機能のテスト"""

import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file import ViewerPOFile


class TestViewerPOFileStats(unittest.TestCase):
    """ViewerPOFileの統計情報機能のテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.viewer = ViewerPOFile()
        # データベースをモック化
        self.viewer.db = MagicMock()

    def test_get_stats_has_progress_attribute(self):
        """get_statsメソッドが返すオブジェクトにprogress属性があることを確認"""
        # EntryModelクラスをインポート
        from sgpo_editor.models.entry import EntryModel
        
        # モックエントリをEntryModelインスタンスとして設定
        mock_entries = [
            EntryModel(key="1", msgid="test1", msgstr="テスト1", fuzzy=False),
            EntryModel(key="2", msgid="test2", msgstr="", fuzzy=True),
            EntryModel(key="3", msgid="test3", msgstr="", fuzzy=False),
        ]

        # get_filtered_entriesをモック化
        self.viewer.get_filtered_entries = MagicMock(return_value=mock_entries)

        # 統計情報を取得
        stats = self.viewer.get_stats()

        # progress属性が存在することを確認
        self.assertTrue(
            hasattr(stats, "progress"), "統計情報オブジェクトにprogress属性がありません"
        )

    def test_get_stats_calculates_progress_correctly(self):
        """get_statsメソッドがprogress属性を正しく計算することを確認"""
        # EntryModelクラスをインポート
        from sgpo_editor.models.entry import EntryModel
        
        # ケース1: 翻訳済み1件、Fuzzy1件、未翻訳1件の場合
        mock_entries1 = [
            EntryModel(key="1", msgid="test1", msgstr="テスト1", fuzzy=False),
            EntryModel(key="2", msgid="test2", msgstr="", fuzzy=True),
            EntryModel(key="3", msgid="test3", msgstr="", fuzzy=False),
        ]
        self.viewer.get_filtered_entries = MagicMock(return_value=mock_entries1)
        stats1 = self.viewer.get_stats()
        # 進捗率 = 翻訳済み / 全体 * 100 = 1 / 3 * 100 = 33.33...%
        self.assertAlmostEqual(stats1.progress, 33.33, delta=0.01)

        # ケース2: すべて翻訳済みの場合
        mock_entries2 = [
            EntryModel(key="1", msgid="test1", msgstr="テスト1", fuzzy=False),
            EntryModel(key="2", msgid="test2", msgstr="テスト2", fuzzy=False),
        ]
        self.viewer.get_filtered_entries = MagicMock(return_value=mock_entries2)
        stats2 = self.viewer.get_stats()
        # 進捗率 = 翻訳済み / 全体 * 100 = 2 / 2 * 100 = 100%
        self.assertEqual(stats2.progress, 100.0)

        # ケース3: エントリがない場合
        self.viewer.get_filtered_entries = MagicMock(return_value=[])
        stats3 = self.viewer.get_stats()
        # エントリがない場合は進捗率0%
        self.assertEqual(stats3.progress, 0.0)


if __name__ == "__main__":
    unittest.main()
