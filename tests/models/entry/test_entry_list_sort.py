"""エントリリストのソート機能テスト

このモジュールでは、エントリリストのソート機能に関するテストを行います。
"""

import pytest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QTableWidget
from PySide6.QtCore import Qt

from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.core.constants import TranslationStatus


@pytest.fixture
def app():
    """QApplicationのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_entries():
    """モックエントリのリスト"""
    entries = []

    # 未翻訳エントリ
    entry1 = EntryModel(
        position=0,
        msgid="Hello",
        msgstr="",
        msgctxt="context1",
        flags=[],
        obsolete=False,
    )
    entry1.score = None
    entries.append(entry1)

    # 翻訳済みエントリ
    entry2 = EntryModel(
        position=1,
        msgid="World",
        msgstr="世界",
        msgctxt="context2",
        flags=[],
        obsolete=False,
    )
    entry2.score = 90
    entries.append(entry2)

    # ファジーエントリ
    entry3 = EntryModel(
        position=2,
        msgid="Test",
        msgstr="テスト",
        msgctxt="context3",
        flags=["fuzzy"],
        obsolete=False,
    )
    entry3.score = 60
    entries.append(entry3)

    # 廃止済みエントリ
    entry4 = EntryModel(
        position=3,
        msgid="Obsolete",
        msgstr="廃止",
        msgctxt="context4",
        flags=[],
        obsolete=True,
    )
    entry4.score = 70
    entries.append(entry4)

    # スコアなしのエントリ
    entry5 = EntryModel(
        position=4,
        msgid="NoScore",
        msgstr="スコアなし",
        msgctxt="context5",
        flags=[],
        obsolete=False,
    )
    entry5.score = None
    entries.append(entry5)

    return entries


@pytest.fixture
def table_manager():
    """テーブルマネージャのフィクスチャ"""
    table = QTableWidget()
    manager = TableManager(table)
    return manager


class TestEntryListSort:
    """エントリリストのソート機能テストクラス"""

    def test_sort_by_position(self, app, mock_entries, table_manager):
        """位置でのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 0, Qt.SortOrder.AscendingOrder
        )
        positions = [entry.position for entry in sorted_entries]
        assert positions == [0, 1, 2, 3, 4], "位置による昇順ソートが正しくありません"

        # 降順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 0, Qt.SortOrder.DescendingOrder
        )
        positions = [entry.position for entry in sorted_entries]
        assert positions == [4, 3, 2, 1, 0], "位置による降順ソートが正しくありません"

    def test_sort_by_context(self, app, mock_entries, table_manager):
        """コンテキストでのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 1, Qt.SortOrder.AscendingOrder
        )
        contexts = [entry.msgctxt for entry in sorted_entries]
        expected = ["context1", "context2", "context3", "context4", "context5"]
        assert contexts == expected, "コンテキストによる昇順ソートが正しくありません"

        # 降順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 1, Qt.SortOrder.DescendingOrder
        )
        contexts = [entry.msgctxt for entry in sorted_entries]
        expected.reverse()
        assert contexts == expected, "コンテキストによる降順ソートが正しくありません"

    def test_sort_by_msgid(self, app, mock_entries, table_manager):
        """原文でのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 2, Qt.SortOrder.AscendingOrder
        )
        msgids = [entry.msgid for entry in sorted_entries]
        expected = ["Hello", "NoScore", "Obsolete", "Test", "World"]
        assert msgids == expected, "原文による昇順ソートが正しくありません"

        # 降順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 2, Qt.SortOrder.DescendingOrder
        )
        msgids = [entry.msgid for entry in sorted_entries]
        expected.reverse()
        assert msgids == expected, "原文による降順ソートが正しくありません"

    def test_sort_by_status(self, app, mock_entries, table_manager):
        """状態でのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 4, Qt.SortOrder.AscendingOrder
        )
        # 状態の順序を確認: 未翻訳 -> ファジー -> 翻訳済み -> 廃止済み
        expected_statuses = [
            TranslationStatus.UNTRANSLATED,
            TranslationStatus.FUZZY,
            TranslationStatus.TRANSLATED,
            TranslationStatus.TRANSLATED,
            TranslationStatus.OBSOLETE,
        ]
        statuses = [entry.get_status() for entry in sorted_entries]
        assert statuses == expected_statuses, "状態による昇順ソートが正しくありません"

        # 降順でソート
        sorted_entries = table_manager._sort_entries(
            mock_entries, 4, Qt.SortOrder.DescendingOrder
        )
        expected_statuses.reverse()
        statuses = [entry.get_status() for entry in sorted_entries]
        assert statuses == expected_statuses, "状態による降順ソートが正しくありません"

    def test_sort_by_score(self, app, mock_entries, table_manager):
        """スコアでのソートテスト"""
        # 昇順でソート
        sorted_entries = table_manager._sort_entries_by_score(
            mock_entries, Qt.SortOrder.AscendingOrder
        )
        scores = [entry.score for entry in sorted_entries]
        # スコアがNoneのエントリは最後に来るはず
        expected = [60, 70, 90, None, None]
        assert scores == expected, "スコアによる昇順ソートが正しくありません"

        # 降順でソート
        sorted_entries = table_manager._sort_entries_by_score(
            mock_entries, Qt.SortOrder.DescendingOrder
        )
        scores = [entry.score for entry in sorted_entries]
        # スコアがNoneのエントリは最後に来るはず
        expected = [90, 70, 60, None, None]
        assert scores == expected, "スコアによる降順ソートが正しくありません"

    def test_sort_header_click(self, app, mock_entries, table_manager):
        """ヘッダークリックによるソートテスト"""
        # テーブル更新処理をモック
        with patch.object(table_manager, "_update_table_contents"):
            table_manager.update_table(mock_entries)

        # ソート状態を確認（初期状態）
        assert table_manager._current_sort_column == 0
        assert table_manager._current_sort_order == Qt.SortOrder.AscendingOrder

        # POFileオブジェクトをモック化
        mock_po_file = MagicMock()
        mock_po_file.get_filtered_entries.return_value = mock_entries

        # _get_current_poメソッドをモック化してテスト用のPOファイルを返すようにする
        with patch.object(table_manager, "_get_current_po", return_value=mock_po_file):
            # ヘッダークリックをシミュレート - update_tableをモック化
            with patch.object(table_manager, "update_table") as mock_update:
                table_manager._on_header_clicked(1)  # コンテキスト列
                # update_tableが呼ばれたことを確認
                mock_update.assert_called_once()
                # ソート状態が更新されたことを確認
                assert table_manager._current_sort_column == 1
                assert table_manager._current_sort_order == Qt.SortOrder.AscendingOrder

            # 同じ列を再度クリック（降順に変更）
            with patch.object(table_manager, "update_table") as mock_update:
                table_manager._on_header_clicked(1)
                # update_tableが呼ばれたことを確認
                mock_update.assert_called_once()
                # ソート状態が更新されたことを確認
                assert table_manager._current_sort_column == 1
                assert table_manager._current_sort_order == Qt.SortOrder.DescendingOrder

            # 別の列をクリック（昇順に戻る）
            with patch.object(table_manager, "update_table") as mock_update:
                table_manager._on_header_clicked(2)  # 原文列
                # update_tableが呼ばれたことを確認
                mock_update.assert_called_once()
                # ソート状態が更新されたことを確認
                assert table_manager._current_sort_column == 2
                assert table_manager._current_sort_order == Qt.SortOrder.AscendingOrder
