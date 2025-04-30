import pytest
from unittest.mock import MagicMock, patch
from typing import List, Set, Optional, Dict

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.constants import TranslationStatus
from sgpo_editor.types import EntryDict


# --- Test Data ---
def create_mock_entry_dicts(num_entries: int = 1000) -> List[EntryDict]:
    """テスト用のEntry辞書リストを作成する"""
    entries = []
    for i in range(num_entries):
        is_translated = i % 10 != 0
        msgid = f"Source text {i}"
        if i % 5 == 0:  # Add keyword 'test' occasionally
            msgid += " test key"

        # EntryDict に必要なフィールドを定義 (EntryModel.from_dict が期待するもの)
        entry_dict: EntryDict = {
            "key": f"key_{i}",
            "msgid": msgid,
            "msgstr": f"Translated text {i}" if is_translated else "",
            "msgctxt": None,
            "obsolete": False,
            "fuzzy": False,  # 必要に応じて設定
            "flags": [],  # 必要に応じて設定
            "position": i,  # ソートや識別に必要
            "occurrences": [],
            "comment": None,
            "tcomment": None,
            # EntryModel.from_dict が pop する可能性のあるフィールドも追加
            "review_comments": [],
            "check_results": [],
            "category_quality_scores": {},
            "score": None,
            "metadata": {},
        }
        entries.append(entry_dict)
    return entries


# --- Fixtures ---
@pytest.fixture
def mock_db_accessor() -> MagicMock:
    """DatabaseAccessorのモックフィクスチャ (advanced_search の動作を模倣)"""
    db_accessor = MagicMock(spec=DatabaseAccessor)

    # advanced_search の動作を模倣する side_effect 関数
    def mock_advanced_search(
        search_text: Optional[str] = None,
        search_fields: Optional[List[str]] = None,
        sort_column: str = "position",
        sort_order: str = "ASC",
        flag_conditions: Optional[Dict[str, bool]] = None,
        translation_status: Optional[Set[str]] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
        **kwargs,  # Allow extra args if spec changes
    ):
        # 1. 全モックエントリ辞書を生成
        all_entry_dicts = create_mock_entry_dicts()

        # 2. フィルタリング実行
        filtered = []
        for entry_dict in all_entry_dicts:
            status_match = True
            # Determine status from dict (simplified)
            current_status = (
                TranslationStatus.TRANSLATED
                if entry_dict["msgstr"]
                else TranslationStatus.UNTRANSLATED
            )
            if entry_dict.get("obsolete", False):
                current_status = TranslationStatus.OBSOLETE
            elif entry_dict.get("fuzzy", False):
                current_status = TranslationStatus.FUZZY

            if translation_status and current_status not in translation_status:
                status_match = False

            keyword_match = True
            if search_text and search_text.strip():
                st = search_text.strip().lower()
                # Check only msgid/msgstr for simplicity
                if (
                    st not in (entry_dict.get("msgid", "") or "").lower()
                    and st not in (entry_dict.get("msgstr", "") or "").lower()
                ):
                    keyword_match = False
            # None or empty string means no keyword filtering

            # TODO: Add filtering based on flag_conditions, exact_match, case_sensitive if needed

            if status_match and keyword_match:
                filtered.append(entry_dict)  # Append the dictionary

        # 3. ソート (using position)
        reverse = sort_order.upper() == "DESC"
        filtered.sort(key=lambda d: d.get("position", 0), reverse=reverse)

        # 4. Limit/Offset
        if offset < 0:
            offset = 0
        end = offset + limit if limit is not None else None
        paginated = filtered[offset:end]

        return paginated  # Return list of filtered dictionaries

    db_accessor.advanced_search.side_effect = mock_advanced_search
    db_accessor.get_filtered_entries = MagicMock()
    return db_accessor


@pytest.fixture
def viewer_po_file(mock_db_accessor: MagicMock) -> ViewerPOFileRefactored:
    """ViewerPOFileRefactoredのフィクスチャ (モックDB使用)"""
    # ViewerPOFileRefactoredは内部でDatabaseAccessorを持つ
    # モックを注入するためにパッチを使用するか、コンストラクタ経由で渡す
    # ここでは DatabaseAccessor を直接モックとして渡せるように仮定
    with patch(
        "sgpo_editor.core.database_accessor.DatabaseAccessor",
        return_value=mock_db_accessor,
    ):
        po_file = ViewerPOFileRefactored("dummy.po", db_accessor=mock_db_accessor)
        po_file.filter.db_accessor = mock_db_accessor
        po_file.filter.filtered_entries = []
        po_file.filter.cache_manager = None
        # 初期状態ではすべてのステータスが選択されていると仮定
        po_file.filter_status = {
            TranslationStatus.TRANSLATED,
            TranslationStatus.UNTRANSLATED,
            # 他のステータスも必要に応じて追加
        }
        po_file.search_text = ""  # 初期検索テキストは空
    return po_file


# --- Test Function ---
def test_filter_reset_after_complex_filter(
    viewer_po_file: ViewerPOFileRefactored, mock_db_accessor: MagicMock
):
    """複雑なフィルター（状態＋キーワード）の後、キーワードフィルターのみをリセットするテスト"""

    # 1. 初期状態（フィルターなし）を確認
    #    get_filtered_entries にデフォルトパラメータで呼び出す
    initial_entries = viewer_po_file.get_filtered_entries(update_filter=True)
    # advanced_search が初期値で呼ばれることを確認
    mock_db_accessor.advanced_search.assert_called_once_with(
        search_text=viewer_po_file.search_text,  # 初期値: ""
        search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"],
        sort_column=viewer_po_file.get_sort_column(),  # 初期値: "position"
        sort_order=viewer_po_file.get_sort_order(),  # 初期値: "ASC"
        flag_conditions={},  # 初期値: {}
        translation_status=viewer_po_file.filter_status,  # 初期値: {TRANSLATED, UNTRANSLATED}
        exact_match=viewer_po_file.filter.exact_match,  # 初期値: False
        case_sensitive=viewer_po_file.filter.case_sensitive,  # 初期値: False
        limit=None,
        offset=0,
    )
    assert len(initial_entries) == 1000
    # get_filtered_entries によりインスタンス変数が更新されているはず
    # デフォルト呼び出しでは search_text は "" に設定される
    assert viewer_po_file.search_text == ""
    assert viewer_po_file.filter_status == {
        TranslationStatus.TRANSLATED,
        TranslationStatus.UNTRANSLATED,
    }
    mock_db_accessor.reset_mock()

    # 2. 状態フィルター("翻訳済み")とキーワードフィルター("test")を適用
    filter_status_param = {TranslationStatus.TRANSLATED}
    keyword_param = "test"
    # フィルタ条件をパラメータで渡す
    filtered_entries_complex = viewer_po_file.get_filtered_entries(
        translation_status=filter_status_param,
        filter_keyword=keyword_param,  # filter_keyword 経由で search_text を設定
        update_filter=True,
    )

    # advanced_search が渡したパラメータに対応する値で呼ばれることを確認
    mock_db_accessor.advanced_search.assert_called_once_with(
        search_text=keyword_param,
        search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"],
        sort_column=viewer_po_file.get_sort_column(),
        sort_order=viewer_po_file.get_sort_order(),
        flag_conditions={},
        translation_status=filter_status_param,
        exact_match=viewer_po_file.filter.exact_match,
        case_sensitive=viewer_po_file.filter.case_sensitive,
        limit=None,
        offset=0,
    )
    # mock_advanced_search がフィルタリングした結果 (100件) を返すはず (元々の180件は計算間違い)
    assert len(filtered_entries_complex) == 100
    # インスタンス変数が更新されていることを確認
    assert viewer_po_file.filter_status == filter_status_param
    assert viewer_po_file.search_text == keyword_param

    # 3. キーワードフィルターのみをリセットし、状態フィルターを維持
    viewer_po_file.set_filter_keyword("")  # Reset search_text to empty string
    mock_db_accessor.reset_mock()
    reset_entries = viewer_po_file.get_filtered_entries(update_filter=True)
    print("Mock calls after reset:", mock_db_accessor.advanced_search.mock_calls)
    # advanced_search が search_text="" で呼ばれることを確認
    mock_db_accessor.advanced_search.assert_called_once_with(
        search_text="",  # リセット後、search_text は空文字列であるべき
        search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"],
        sort_column=viewer_po_file.get_sort_column(),
        sort_order=viewer_po_file.get_sort_order(),
        flag_conditions={},
        translation_status=filter_status_param,  # 状態フィルターは維持
        exact_match=viewer_po_file.filter.exact_match,
        case_sensitive=viewer_po_file.filter.case_sensitive,
        limit=None,
        offset=0,
    )
    assert len(reset_entries) == 900
    # インスタンス変数が更新されていることを確認
    assert viewer_po_file.filter_status == filter_status_param  # 状態は維持
    assert viewer_po_file.search_text == ""  # キーワードは空文字列にリセット
