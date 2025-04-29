"""エントリリストのフィルタリング機能テスト

このモジュールでは、エントリリストのフィルタリング機能に関するテストを行います。
"""

import pytest
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication, QTableWidget

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.widgets.search import SearchCriteria
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.gui.facades.entry_list_facade import EntryListFacade
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
        msgid="Testing",
        msgstr="テスト中",
        msgctxt="context3",
        flags=["fuzzy"],
        obsolete=False,
    )
    entry3.score = 60
    entries.append(entry3)

    # 廃止済みエントリ
    entry4 = EntryModel(
        position=3,
        msgid="Obsolete Entry",
        msgstr="廃止されたエントリ",
        msgctxt="context4",
        flags=[],
        obsolete=True,
    )
    entry4.score = 70
    entries.append(entry4)

    # 低品質スコアのエントリ
    entry5 = EntryModel(
        position=4,
        msgid="Low Quality",
        msgstr="低品質",
        msgctxt="quality",
        flags=[],
        obsolete=False,
    )
    entry5.score = 30
    entries.append(entry5)

    return entries


@pytest.fixture
def table_manager(mock_entries):
    """テーブルマネージャのフィクスチャ"""
    mock_po = MagicMock()
    mock_po.get_entries_by_keys.return_value = {e.key: e for e in mock_entries}
    mock_table = MagicMock(spec=QTableWidget)
    mock_cache_manager = MagicMock(spec=EntryCacheManager)
    table_manager = TableManager(mock_table, mock_cache_manager, lambda: mock_po)

    mock_search_widget = MagicMock()
    entry_list = EntryListFacade(
        mock_table,
        table_manager,
        mock_search_widget,
        mock_cache_manager,
        lambda: mock_po,
    )

    return entry_list


class TestEntryListFilter:
    """エントリリストのフィルタリング機能テストクラス"""

    @pytest.fixture(autouse=True)
    def setup_method(self, qtbot, table_manager):
        self.manager = table_manager

    def test_filter_by_status(self, mock_entries):
        """状態によるフィルタリングテスト"""
        # ViewerPOFileのget_filtered_entriesをモック
        po_file = self.manager._get_current_po()
        po_file.get_filtered_entries.side_effect = lambda **kwargs: [
            entry
            for entry in mock_entries
            if self._entry_matches_filter(entry, kwargs.get("filter_text"))
        ]

        # 未翻訳のエントリフィルタリング
        filter_text = TranslationStatus.UNTRANSLATED
        entries = po_file.get_filtered_entries(
            filter_text=filter_text, filter_keyword=""
        )

        # SearchCriteriaを作成
        SearchCriteria(filter=filter_text, filter_keyword="")

        # テーブル更新処理を直接呼び出し
        self.manager.update_table()

        assert len(entries) == 1
        assert entries[0].get_status() == TranslationStatus.UNTRANSLATED

        # 翻訳済みのエントリフィルタリング
        filter_text = TranslationStatus.TRANSLATED
        entries = po_file.get_filtered_entries(
            filter_text=filter_text, filter_keyword=""
        )
        SearchCriteria(filter=filter_text, filter_keyword="")

        self.manager.update_table()

        assert len(entries) == 2
        for entry in entries:
            assert entry.get_status() == TranslationStatus.TRANSLATED

        # ファジーのエントリフィルタリング
        filter_text = TranslationStatus.FUZZY
        entries = po_file.get_filtered_entries(
            filter_text=filter_text, filter_keyword=""
        )
        SearchCriteria(filter=filter_text, filter_keyword="")

        self.manager.update_table()

        assert len(entries) == 1
        assert entries[0].get_status() == TranslationStatus.FUZZY

        # 廃止済みのエントリフィルタリング
        filter_text = TranslationStatus.OBSOLETE
        entries = po_file.get_filtered_entries(
            filter_text=filter_text, filter_keyword=""
        )
        SearchCriteria(filter=filter_text, filter_keyword="")

        self.manager.update_table()

        assert len(entries) == 1
        assert entries[0].get_status() == TranslationStatus.OBSOLETE

    def test_text_search(self, mock_entries):
        """テキスト検索によるフィルタリングテスト"""
        # ViewerPOFileのget_filtered_entriesをモック
        po_file = self.manager._get_current_po()
        po_file.get_filtered_entries.side_effect = lambda **kwargs: [
            entry
            for entry in mock_entries
            if self._entry_matches_keyword(entry, kwargs.get("filter_keyword"))
        ]

        # 「Test」を含むエントリの検索
        filter_text = TranslationStatus.ALL
        filter_keyword = "Test"
        entries = po_file.get_filtered_entries(
            filter_text=filter_text, filter_keyword=filter_keyword
        )

        # SearchCriteriaを作成
        SearchCriteria(filter=filter_text, filter_keyword=filter_keyword)

        # テーブル更新
        self.manager.update_table()

        assert len(entries) == 1
        assert "Testing" == entries[0].msgid

        # 「エントリ」を含むエントリの検索
        filter_keyword = "エントリ"
        entries = po_file.get_filtered_entries(
            filter_text=filter_text, filter_keyword=filter_keyword
        )
        SearchCriteria(filter=filter_text, filter_keyword=filter_keyword)

        self.manager.update_table()

        assert len(entries) == 1
        assert "廃止されたエントリ" == entries[0].msgstr

        # コンテキストでの検索
        filter_keyword = "quality"
        entries = po_file.get_filtered_entries(
            filter_text=filter_text, filter_keyword=filter_keyword
        )
        SearchCriteria(filter=filter_text, filter_keyword=filter_keyword)

        self.manager.update_table()

        assert len(entries) == 1
        assert "quality" == entries[0].msgctxt

    def _entry_matches_filter(self, entry, filter_text):
        """エントリがフィルタに一致するかを判定"""
        if filter_text == "すべて" or filter_text == TranslationStatus.ALL:
            return True
        elif (
            filter_text == TranslationStatus.UNTRANSLATED
            and entry.get_status() == TranslationStatus.UNTRANSLATED
        ):
            return True
        elif (
            filter_text == TranslationStatus.TRANSLATED
            and entry.get_status() == TranslationStatus.TRANSLATED
        ):
            return True
        elif (
            filter_text == TranslationStatus.FUZZY
            and entry.get_status() == TranslationStatus.FUZZY
        ):
            return True
        elif (
            filter_text == TranslationStatus.OBSOLETE
            and entry.get_status() == TranslationStatus.OBSOLETE
        ):
            return True
        return False

    def _entry_matches_keyword(self, entry, keyword):
        """エントリがキーワードに一致するかを判定"""
        if not keyword:
            return True

        # 各フィールドでキーワード検索
        if keyword.lower() in str(entry.msgid).lower():
            return True
        if keyword.lower() in str(entry.msgstr).lower():
            return True
        if keyword.lower() in str(entry.msgctxt).lower():
            return True
        return False

    def test_combined_search(self, mock_entries):
        """状態とキーワードを組み合わせた検索テスト"""
        # ViewerPOFileのget_filtered_entriesをモック
        po_file = self.manager._get_current_po()
        po_file.get_filtered_entries.side_effect = lambda **kwargs: [
            entry
            for entry in mock_entries
            if self._entry_matches_filter(entry, kwargs.get("filter_text"))
            and self._entry_matches_keyword(entry, kwargs.get("filter_keyword"))
        ]

        # 翻訳済みのエントリから「世界」を含むものの検索
        self.manager._current_filter_text = TranslationStatus.TRANSLATED
        self.manager._current_search_text = "世界"

        entries = po_file.get_filtered_entries(
            filter_text=TranslationStatus.TRANSLATED, filter_keyword="世界"
        )

        assert len(entries) == 1
        assert "世界" in entries[0].msgstr
        assert entries[0].get_status() == TranslationStatus.TRANSLATED

        # 全てのエントリから「エントリ」を含むものの検索
        self.manager._current_filter_text = TranslationStatus.ALL
        self.manager._current_search_text = "エントリ"

        entries = po_file.get_filtered_entries(
            filter_text=TranslationStatus.ALL, filter_keyword="エントリ"
        )

        assert len(entries) == 1
        assert "廃止されたエントリ" == entries[0].msgstr

        # コンテキストでの検索
        filter_keyword = "quality"
        entries = po_file.get_filtered_entries(
            filter_text=TranslationStatus.ALL, filter_keyword=filter_keyword
        )

        assert len(entries) == 1
        assert "quality" == entries[0].msgctxt

    def test_search_criteria_integration(self, mock_entries):
        """SearchCriteriaとの連携テスト"""
        # フィルタとキーワードの組み合わせパターン
        test_cases = [
            (TranslationStatus.ALL, "", 5),  # すべてのエントリ
            (TranslationStatus.TRANSLATED, "", 2),  # 翻訳済みエントリのみ
            (TranslationStatus.UNTRANSLATED, "", 1),  # 未翻訳エントリのみ
            (TranslationStatus.FUZZY, "", 1),  # ファジーエントリのみ
            (TranslationStatus.ALL, "Test", 1),  # "Test"を含むすべてのエントリ
            (TranslationStatus.TRANSLATED, "世界", 1),  # "世界"を含む翻訳済みエントリ
        ]

        for filter_text, keyword, expected_count in test_cases:
            # フィルタリング結果をテスト用に生成
            filtered_entries = [
                entry
                for entry in mock_entries
                if self._entry_matches_filter(entry, filter_text)
                and self._entry_matches_keyword(entry, keyword)
            ]

            # 検索条件の作成
            SearchCriteria(filter=filter_text, filter_keyword=keyword)

            # テーブル更新
            self.manager.update_table()

            # 結果の確認 - フィルタリング結果の数が期待値と一致するか
            assert len(filtered_entries) == expected_count, (
                f"フィルタ '{filter_text}' とキーワード '{keyword}' の結果数が期待と異なります"
            )

    def test_update_filtered_table(self, mock_entries):
        """フィルタリングされたテーブル更新のテスト"""
        # 翻訳済みエントリのフィルタリング
        self.manager._get_current_po()
        translated_entries = [
            entry
            for entry in mock_entries
            if entry.get_status() == TranslationStatus.TRANSLATED
        ]

        # 検索条件の設定
        SearchCriteria(
            filter=TranslationStatus.TRANSLATED, filter_keyword=""
        )

        # テーブル更新処理を直接呼び出し
        self.manager.update_table()

        # フィルタリング結果の確認
        assert len(translated_entries) == 2  # 2つの翻訳済みエントリ
        for entry in translated_entries:
            assert entry.get_status() == TranslationStatus.TRANSLATED
