"""基本的なフィルタリセットに関するテスト

このテストでは、フィルタを適用した後にキーワードを空にした場合に、
すべてのエントリが表示されるかどうかを検証します。
"""

import pytest

# テスト対象のモジュールをインポート
from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored


class TestFilterResetBasic:
    """基本的なフィルタリセットに関するテスト"""

    @pytest.fixture
    def setup_test_data(self):
        """テスト用のPOファイルとデータを設定"""
        # ViewerPOFileRefactoredのインスタンスを作成
        po_file = ViewerPOFileRefactored()

        # テスト用のエントリを作成（多めに）
        test_entries = []
        for i in range(200):
            entry = {
                "key": f"key{i}",
                "msgid": f"msgid{i}",
                "msgstr": f"msgstr{i}",
                "fuzzy": False,
                "translated": True,
            }
            test_entries.append(entry)

        # キーワード 'test' を含むエントリを追加
        for i in range(50):
            entry = {
                "key": f"test_key{i}",
                "msgid": f"test_msgid{i}",
                "msgstr": f"test_msgstr{i}",
                "fuzzy": False,
                "translated": True,
            }
            test_entries.append(entry)

        # データベースにエントリを追加 (db_accessor経由)
        po_file.db_accessor.add_entries_bulk(test_entries)

        # データがロードされたことを示すフラグを設定 (テスト簡略化)
        # po_file._is_loaded = True # 内部状態への直接アクセスは避ける

        yield po_file

    def test_filter_reset_full_simulation(self, setup_test_data):
        """フィルタをリセットした際に全エントリが表示されるかの完全シミュレーション"""
        po_file = setup_test_data

        # 1. 初期状態の確認
        # print(
        #     f"\n[TEST] ViewerPOFile初期状態: search_text={
        #         po_file.search_text
        #     }, translation_status={po_file.translation_status}"
        # )

        # 2. 初期状態で全エントリを取得
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"[TEST] 初期状態のエントリ数: {initial_count}件")

        # 3. フィルタを適用（'test'で検索）
        filtered_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="test"
        )
        filtered_count = len(filtered_entries)
        print(f"[TEST] 'test'フィルタ適用後のエントリ数: {filtered_count}件")

        # 4. フィルタを空にリセット
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=""
        )
        reset_count = len(reset_entries)
        print(f"[TEST] フィルタリセット後のエントリ数: {reset_count}件")

        # 5. 検証: リセット後のエントリ数が初期状態と同じになるはず
        assert reset_count == initial_count, (
            f"フィルタリセット後のエントリ数が初期状態と異なります: {reset_count} != {initial_count}"
        )

        # ログ出力
        print(
            "[TEST] フィルタリセットテスト成功: 初期状態とリセット後のエントリ数が一致しました"
        )

    def test_filter_reset_with_whitespace(self, setup_test_data):
        """空白文字だけのキーワードでフィルタリセットをテスト"""
        po_file = setup_test_data

        # 1. 初期状態の確認
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"\n[TEST] 初期状態のエントリ数: {initial_count}件")

        # 2. フィルタを適用（'test'で検索）
        filtered_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="test"
        )
        filtered_count = len(filtered_entries)
        print(f"[TEST] 'test'フィルタ適用後のエントリ数: {filtered_count}件")

        # 3. 空白文字だけのキーワードでフィルタをリセット
        whitespace_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="   "
        )
        whitespace_count = len(whitespace_entries)
        print(f"[TEST] 空白文字フィルタ後のエントリ数: {whitespace_count}件")

        # 4. 検証: 空白文字フィルタ後のエントリ数が初期状態と同じになるはず
        assert whitespace_count == initial_count, (
            f"空白文字フィルタ後のエントリ数が初期状態と異なります: {whitespace_count} != {initial_count}"
        )

        # 5. 検証: フィルタリセット後のsearch_textがNoneになるはず (get_filtersで確認)
        # assert (
        #     po_file.search_text is None or po_file.search_text.strip() == ""
        # ), f"search_textがNoneになっていません: {po_file.search_text}"
        current_filters = po_file.get_filters()
        assert current_filters.get("search_text") == "", f"search_textが空になっていません: {current_filters.get('search_text')}"

        print(
            "[TEST] 空白文字フィルタテスト成功: 初期状態とリセット後のエントリ数が一致しました"
        )

    def test_filter_reset_with_none(self, setup_test_data):
        """キーワードがNoneの場合のフィルタリセットをテスト"""
        po_file = setup_test_data

        # 1. 初期状態の確認
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"\n[TEST] 初期状態のエントリ数: {initial_count}件")
        # print(f"[TEST] 初期状態のフィルタ状態: search_text={po_file.search_text}")

        # 2. フィルタを適用（'test'で検索）
        filtered_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="test"
        )
        filtered_count = len(filtered_entries)
        print(f"[TEST] 'test'フィルタ適用後のエントリ数: {filtered_count}件")
        # print(f"[TEST] フィルタ適用後の状態: search_text={po_file.search_text}")

        # キャッシュの状態を確認 (内部キャッシュへのアクセスは削除)
        # cache_size = (
        #     len(po_file._entry_obj_cache) if hasattr(po_file, "_entry_obj_cache") else 0
        # )
        # print(f"[TEST] フィルタ適用後のキャッシュサイズ: {cache_size}件")

        # キャッシュとsearch_textを手動でリセット (内部状態操作は削除)
        # if hasattr(po_file, "_entry_obj_cache"):
        #     po_file._entry_obj_cache = {}
        # po_file.search_text = None
        # po_file.filtered_entries = []
        # print("[TEST] キャッシュとsearch_textを手動でリセットしました")

        # 3. Noneでフィルタをリセット
        none_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=None
        )
        none_count = len(none_entries)
        print(f"[TEST] Noneフィルタ後のエントリ数: {none_count}件")
        # print(f"[TEST] Noneフィルタ後の状態: search_text={po_file.search_text}")

        # 4. 検証: Noneフィルタ後のエントリ数が初期状態と同じになるはず
        assert none_count == initial_count, (
            f"Noneフィルタ後のエントリ数が初期状態と異なります: {none_count} != {initial_count}"
        )

        # 5. 検証: フィルタリセット後のsearch_textがNoneになるはず (get_filtersで確認)
        # assert (
        #     po_file.search_text is None or po_file.search_text.strip() == ""
        # ), f"search_textがNoneになっていません: {po_file.search_text}"
        current_filters = po_file.get_filters()
        assert current_filters.get("search_text") == "", f"search_textが空になっていません: {current_filters.get('search_text')}"

        print(
            "[TEST] Noneフィルタテスト成功: 初期状態とリセット後のエントリ数が一致しました"
        )

    def test_filter_reset_with_po_state(self, setup_test_data):
        """ViewerPOFileRefactoredの状態を使った詳細テスト"""
        po_file = setup_test_data

        # 1. 初期状態の確認
        initial_filters = po_file.get_filters()
        print(
            f"\n[TEST] ViewerPOFile初期状態: search_text={
                initial_filters.get('search_text')
            }, translation_status={initial_filters.get('translation_status')}"
        )
        # print(
        #     f"[TEST] 内部キャッシュ: _entry_obj_cache件数={
        #         len(po_file._entry_obj_cache)
        #         if hasattr(po_file, '_entry_obj_cache')
        #         else 'なし'
        #     }"
        # )

        # 2. 初期状態で全エントリを取得
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"[TEST] 初期状態のエントリ数: {initial_count}件")

        # 3. フィルタを適用
        po_file.get_filtered_entries(update_filter=True, filter_keyword="test")
        filtered_filters = po_file.get_filters()
        print(
            f"[TEST] フィルタ適用後のViewerPOFile状態: search_text={
                filtered_filters.get('search_text')
            }, translation_status={filtered_filters.get('translation_status')}"
        )
        # print(
        #     f"[TEST] フィルタ適用後の内部キャッシュ: _entry_obj_cache件数={
        #         len(po_file._entry_obj_cache)
        #         if hasattr(po_file, '_entry_obj_cache')
        #         else 'なし'
        #     }"
        # )

        # 4. フィルタをリセット（空文字列）
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=""
        )
        reset_count = len(reset_entries)
        reset_filters = po_file.get_filters()
        print(f"[TEST] リセット後のエントリ数: {reset_count}件")
        print(
            f"[TEST] リセット後のViewerPOFile状態: search_text={
                reset_filters.get('search_text')
            }, translation_status={reset_filters.get('translation_status')}"
        )
        # print(
        #     f"[TEST] リセット後の内部キャッシュ: _entry_obj_cache件数={
        #         len(po_file._entry_obj_cache)
        #         if hasattr(po_file, '_entry_obj_cache')
        #         else 'なし'
        #     }"
        # )

        # 5. 検証: リセット後のエントリ数が初期状態と同じになるはず
        assert reset_count == initial_count, (
            f"フィルタリセット後のエントリ数が初期状態と異なります: {reset_count} != {initial_count}"
        )

        # 6. データベースから直接取得して比較 (db_accessor経由)
        db_entries = po_file.db_accessor.get_filtered_entries(search_text=None)
        db_count = len(db_entries)
        print(f"[TEST] データベースから直接取得したエントリ数: {db_count}件")

        # データベース取得結果と初期状態が一致するか検証
        assert db_count == initial_count, (
            "データベース取得結果が初期状態と異なります"
        )
