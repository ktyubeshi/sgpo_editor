"""ViewerPOFileの統計情報機能のテスト"""

import unittest
from unittest.mock import MagicMock

from sgpo_editor.core.viewer_po_file import ViewerPOFile as ViewerPOFileRefactored
from sgpo_editor.gui.widgets.search import SearchCriteria


class TestViewerPOFileStats(unittest.TestCase):
    """ViewerPOFileの統計情報機能のテスト"""

    def setUp(self):
        """テスト前の準備"""
        # db_accessor のモックをコンストラクタに渡す
        self.mock_db_accessor = MagicMock()
        # StatsComponent.get_statisticsメソッドで使用されるメソッドの戻り値を設定
        self.mock_db_accessor.count_entries.return_value = int(0)
        self.mock_db_accessor.count_entries_with_condition.return_value = int(0)
        self.mock_db_accessor.count_entries_with_flag.return_value = int(0)
        self.viewer = ViewerPOFileRefactored(db_accessor=self.mock_db_accessor)

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

        # StatsComponent.get_statisticsメソッドで使用されるメソッドの戻り値を設定
        self.mock_db_accessor.count_entries.return_value = int(3)
        self.mock_db_accessor.count_entries_with_condition.return_value = int(1)
        self.mock_db_accessor.count_entries_with_flag.return_value = int(1)

        # get_filtered_entriesをモック化
        self.viewer.get_filtered_entries = MagicMock(return_value=mock_entries)
        # get_statsメソッドの中でget_filtered_entriesが呼ばれる場合に備えて、引数をチェックする
        self.viewer.get_filtered_entries.side_effect = lambda criteria: mock_entries

        # 統計情報を取得
        stats = self.viewer.get_stats()

        # percent_translated属性が存在することを確認
        self.assertTrue(
            "percent_translated" in stats, "統計情報オブジェクトにpercent_translated属性がありません"
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
        # StatsComponent.get_statisticsメソッドで使用されるメソッドの戻り値を設定
        self.mock_db_accessor.count_entries.return_value = int(3)
        self.mock_db_accessor.count_entries_with_condition.return_value = int(1)
        self.mock_db_accessor.count_entries_with_flag.return_value = int(1)
        
        self.viewer.get_filtered_entries = MagicMock(return_value=mock_entries1)
        # get_statsメソッドの中でget_filtered_entriesが呼ばれる場合に備えて、引数をチェックする
        self.viewer.get_filtered_entries.side_effect = lambda criteria: mock_entries1
        stats1 = self.viewer.get_stats()
        # 進捗率 = 翻訳済み / 全体 * 100 = 1 / 3 * 100 = 33.33...%
        self.assertAlmostEqual(stats1["percent_translated"], 33.33, delta=0.01)

        # ケース2: すべて翻訳済みの場合
        mock_entries2 = [
            EntryModel(key="1", msgid="test1", msgstr="テスト1", fuzzy=False),
            EntryModel(key="2", msgid="test2", msgstr="テスト2", fuzzy=False),
        ]
        # StatsComponent.get_statisticsメソッドで使用されるメソッドの戻り値を設定
        self.mock_db_accessor.count_entries.return_value = int(2)
        self.mock_db_accessor.count_entries_with_condition.return_value = int(2)
        self.mock_db_accessor.count_entries_with_flag.return_value = int(0)
        
        self.viewer.get_filtered_entries = MagicMock(return_value=mock_entries2)
        # get_statsメソッドの中でget_filtered_entriesが呼ばれる場合に備えて、引数をチェックする
        self.viewer.get_filtered_entries.side_effect = lambda criteria: mock_entries2
        stats2 = self.viewer.get_stats()
        # 進捗率 = 翻訳済み / 全体 * 100 = 2 / 2 * 100 = 100%
        self.assertEqual(stats2["percent_translated"], 100.0)

        # ケース3: エントリがない場合
        # StatsComponent.get_statisticsメソッドで使用されるメソッドの戻り値を設定
        self.mock_db_accessor.count_entries.return_value = int(0)
        self.mock_db_accessor.count_entries_with_condition.return_value = int(0)
        self.mock_db_accessor.count_entries_with_flag.return_value = int(0)
        
        self.viewer.get_filtered_entries = MagicMock(return_value=[])
        # get_statsメソッドの中でget_filtered_entriesが呼ばれる場合に備えて、引数をチェックする
        self.viewer.get_filtered_entries.side_effect = lambda criteria: []
        stats3 = self.viewer.get_stats()
        # エントリがない場合は進捗率0%
        self.assertEqual(stats3["percent_translated"], 0.0)


if __name__ == "__main__":
    unittest.main()
