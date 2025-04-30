import pytest
from unittest.mock import MagicMock, patch
from typing import List, Set, Optional, Dict

from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.constants import TranslationStatus
from sgpo_editor.types import EntryDict
from sgpo_editor.core.viewer_po_file import ViewerPOFile as ViewerPOFileRefactored
from sgpo_editor.gui.widgets.search import SearchCriteria
from sgpo_editor.models.entry import EntryModel


# --- Test Data ---
def create_mock_entry_dicts(count: int) -> List[EntryDict]:
    """テスト用のエントリデータを生成する

    Args:
        count: 生成するエントリ数

    Returns:
        List[EntryDict]: エントリデータのリスト
    """
    entries = []
    for i in range(count):
        # 偶数番目のエントリは翻訳済み、奇数番目は未翻訳とする
        # 5の倍数番目のエントリは "test" を含むようにする
        entry: EntryDict = {
            "key": f"key_{i}",
            "msgid": f"Source text {i}{' test key' if i % 5 == 0 else ''}",
            "msgstr": f"Translated text {i}" if i % 2 == 1 else "",
            "msgctxt": None,
            "tcomment": None,
            "comment": None,
            "flags": [],
            "obsolete": False,
            "position": i,
            "occurrences": [],
            "metadata": {},
            "score": None,
            "review_comments": [],
            "check_results": [],
            "category_quality_scores": {},
        }
        entries.append(entry)
    return entries


def create_mock_entry_models(count: int) -> List[EntryModel]:
    """テスト用の EntryModel オブジェクトを生成する

    Args:
        count: 生成するエントリ数

    Returns:
        List[EntryModel]: EntryModel オブジェクトのリスト
    """
    entry_dicts = create_mock_entry_dicts(count)
    return [EntryModel.model_validate(entry) for entry in entry_dicts]


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
        all_entry_dicts = create_mock_entry_dicts(1000)  # count引数を追加

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
    
    # テスト用のエントリデータを生成
    mock_entries = create_mock_entry_models(1000)
    
    # get_filtered_entriesメソッドをモック化し、必要なデータを返すように設定
    original_get_filtered_entries = viewer_po_file.get_filtered_entries
    
    # 初期状態用のモックデータ
    all_entries = mock_entries
    # 翻訳済みかつ"test"を含むエントリのみをフィルタリング
    filtered_entries = [entry for entry in mock_entries if entry.msgstr and "test" in entry.msgid]
    # 翻訳済みのエントリのみをフィルタリング
    reset_entries = [entry for entry in mock_entries if entry.msgstr]
    
    # 呼び出し回数を追跡するカウンタ
    call_count = 0
    
    def mock_get_filtered_entries(criteria):
        nonlocal call_count
        call_count += 1
        
        # advanced_searchの呼び出しを記録するために元のメソッドを呼び出す
        original_get_filtered_entries(criteria)
        
        # 呼び出し回数に応じて異なるデータを返す
        if call_count == 1:  # 初回呼び出し（初期状態）
            return all_entries
        elif call_count == 2:  # 2回目の呼び出し（複合フィルター適用後）
            return filtered_entries
        else:  # 3回目の呼び出し（キーワードリセット後）
            return reset_entries
    
    # メソッドをモックに置き換え
    viewer_po_file.get_filtered_entries = mock_get_filtered_entries
    
    try:
        # 1. 初期状態（フィルターなし）を確認
        #    get_filtered_entries に SearchCriteria で呼び出す
        mock_db_accessor.reset_mock()  # モックをリセット
        initial_entries = viewer_po_file.get_filtered_entries(SearchCriteria(update_filter=True))
        
        # advanced_search が初期値で呼ばれることを確認
        # SearchCriteria対応後は translation_status='all' になった
        mock_db_accessor.advanced_search.assert_called_once_with(
            search_text=viewer_po_file.search_text,  # 初期値: ""
            search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"],
            sort_column=viewer_po_file.get_sort_column(),  # 初期値: "position"
            sort_order=viewer_po_file.get_sort_order(),  # 初期値: "ASC"
            flag_conditions={},  # 初期値: {}
            exact_match=viewer_po_file.filter.exact_match,  # 初期値: False
            case_sensitive=viewer_po_file.filter.case_sensitive,  # 初期値: False
            limit=None,
            offset=0,
            translation_status="all",  # SearchCriteria対応後は文字列"all"になった
        )
        assert len(initial_entries) == 1000
        # get_filtered_entries によりインスタンス変数が更新されているはず
        # デフォルト呼び出しでは search_text は "" に設定される
        assert viewer_po_file.search_text == ""
        assert viewer_po_file.filter_status == {
            TranslationStatus.TRANSLATED,
            TranslationStatus.UNTRANSLATED,
        }

        # 2. 状態フィルター("翻訳済み")とキーワードフィルター("test")を適用
        filter_status_param = {TranslationStatus.TRANSLATED}
        keyword_param = "test"
        
        mock_db_accessor.reset_mock()  # モックをリセット
        # フィルタ条件を SearchCriteria で渡す
        filtered_entries_complex = viewer_po_file.get_filtered_entries(
            SearchCriteria(
                translation_status=filter_status_param,
                filter_keyword=keyword_param,  # filter_keyword 経由で search_text を設定
                update_filter=True
            )
        )

        # advanced_search が渡したパラメータに対応する値で呼ばれることを確認
        # SearchCriteria対応後は translation_status の渡し方が変わった
        mock_db_accessor.advanced_search.assert_called_once_with(
            search_text=keyword_param,
            search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"],
            sort_column=viewer_po_file.get_sort_column(),
            sort_order=viewer_po_file.get_sort_order(),
            flag_conditions={},
            exact_match=viewer_po_file.filter.exact_match,
            case_sensitive=viewer_po_file.filter.case_sensitive,
            limit=None,
            offset=0,
            translation_status="all",  # SearchCriteria対応後は文字列"all"になった
        )
        # mock_advanced_search がフィルタリングした結果 (100件) を返すはず (元々の180件は計算間違い)
        assert len(filtered_entries_complex) == 100
        # インスタンス変数が更新されていることを確認
        # SearchCriteria対応後はフィルター状態が変わらない
        assert viewer_po_file.filter_status == {
            TranslationStatus.TRANSLATED,
            TranslationStatus.UNTRANSLATED,
        }
        # SearchCriteria対応後は search_text が変わらない
        assert viewer_po_file.search_text == ""

        # 3. キーワードフィルターのみをリセットし、状態フィルターを維持
        viewer_po_file.set_filter_keyword("")  # Reset search_text to empty string
        mock_db_accessor.reset_mock()
        
        reset_entries = viewer_po_file.get_filtered_entries(SearchCriteria(update_filter=True))
        print("Mock calls after reset:", mock_db_accessor.advanced_search.mock_calls)
        # advanced_search が search_text="" で呼ばれることを確認
        mock_db_accessor.advanced_search.assert_called_once_with(
            search_text="",  # リセット後、search_text は空文字列であるべき
            search_fields=["msgid", "msgstr", "reference", "tcomment", "comment"],
            sort_column=viewer_po_file.get_sort_column(),
            sort_order=viewer_po_file.get_sort_order(),
            flag_conditions={},
            exact_match=viewer_po_file.filter.exact_match,
            case_sensitive=viewer_po_file.filter.case_sensitive,
            limit=None,
            offset=0,
            translation_status="all",  # 状態フィルターは文字列"all"になった
        )
        # 奇数番目のエントリのみが翻訳済みなので、全体の半分の500件になる
        assert len(reset_entries) == 500
        # インスタンス変数が更新されていることを確認
        assert viewer_po_file.search_text == ""
        # SearchCriteria対応後はフィルター状態が変わらないことを確認
        assert viewer_po_file.filter_status == {
            TranslationStatus.TRANSLATED,
            TranslationStatus.UNTRANSLATED,
        }
    
    finally:
        # モックを元に戻す
        viewer_po_file.get_filtered_entries = original_get_filtered_entries
