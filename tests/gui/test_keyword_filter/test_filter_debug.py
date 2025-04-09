"""キーワードフィルタの問題を特定するためのデバッグテスト

このテストでは、キーワードフィルタリングの問題を特定するために、
詳細なデバッグ情報を出力し、フィルタリングの前後でエントリ数が
一致することを確認します。
"""

import pytest

# テスト対象のモジュールをインポート
from sgpo_editor.core.viewer_po_file import ViewerPOFile


class TestFilterDebug:
    """キーワードフィルタの問題を特定するためのデバッグテスト"""

    @pytest.fixture
    def setup_test_data(self):
        """テスト用のPOファイルとデータを設定"""
        # ViewerPOFileのインスタンスを作成
        po_file = ViewerPOFile()

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

        # データベースにエントリを追加
        po_file.db.add_entries_bulk(test_entries)

        # データがロードされたことを示すフラグを設定
        po_file._is_loaded = True

        yield po_file

    def test_filter_reset_with_detailed_debug(self, setup_test_data):
        """フィルタリセットの詳細なデバッグテスト"""
        po_file = setup_test_data

        # 1. 初期状態の確認
        print("\n[DEBUG] ===== 初期状態の確認 =====")
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"[DEBUG] 初期状態のエントリ数: {initial_count}件")
        print(
            f"[DEBUG] ViewerPOFile状態: search_text={po_file.search_text}, translation_status={po_file.translation_status}"
        )

        # 2. データベースから直接取得して比較
        db_entries = po_file.db.get_entries()
        db_count = len(db_entries)
        print(f"[DEBUG] データベースから直接取得したエントリ数: {db_count}件")

        # 初期状態の検証
        assert initial_count == db_count, (
            f"初期状態のエントリ数がデータベースと一致しません: {initial_count} != {db_count}"
        )

        # 3. フィルタを適用（'test'で検索）
        print("\n[DEBUG] ===== フィルタ適用 =====")
        filtered_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="test"
        )
        filtered_count = len(filtered_entries)
        print(f"[DEBUG] 'test'フィルタ適用後のエントリ数: {filtered_count}件")
        print(
            f"[DEBUG] ViewerPOFile状態: search_text={po_file.search_text}, translation_status={po_file.translation_status}"
        )

        # 4. フィルタをリセット（Noneを使用）
        print("\n[DEBUG] ===== フィルタリセット =====")
        # キャッシュの状態を確認
        if hasattr(po_file, "_entry_obj_cache"):
            cache_size = len(po_file._entry_obj_cache)
            print(f"[DEBUG] リセット前のキャッシュサイズ: {cache_size}件")

        # リセット前の内部状態を詳細に出力
        print("[DEBUG] リセット前のViewerPOFile状態:")
        print(f"  - search_text: {po_file.search_text}")
        print(f"  - translation_status: {po_file.translation_status}")
        print(f"  - filtered_entries: {len(po_file.filtered_entries)}件")
        print(f"  - flag_conditions: {po_file.flag_conditions}")

        # キャッシュとsearch_textを手動でリセット
        if hasattr(po_file, "_entry_obj_cache"):
            po_file._entry_obj_cache = {}
        po_file.search_text = None
        po_file.filtered_entries = []
        print("[DEBUG] キャッシュとsearch_textを手動でリセットしました")

        # リセット後のエントリを取得
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=None
        )
        reset_count = len(reset_entries)
        print(f"[DEBUG] リセット後のエントリ数: {reset_count}件")
        print(
            f"[DEBUG] ViewerPOFile状態: search_text={po_file.search_text}, translation_status={po_file.translation_status}"
        )

        # リセット後のキャッシュサイズを確認
        if hasattr(po_file, "_entry_obj_cache"):
            reset_cache_size = len(po_file._entry_obj_cache)
            print(f"[DEBUG] リセット後のキャッシュサイズ: {reset_cache_size}件")

        # 5. 検証: リセット後のエントリ数が初期状態と同じになるはず
        assert reset_count == initial_count, (
            f"リセット後のエントリ数が初期状態と異なります: {reset_count} != {initial_count}"
        )

        # 6. データベースから直接取得して比較（再確認）
        db_entries_after = po_file.db.get_entries()
        db_count_after = len(db_entries_after)
        print(
            f"[DEBUG] リセット後にデータベースから直接取得したエントリ数: {db_count_after}件"
        )

        # データベース取得結果と初期状態が一致するか検証
        assert db_count_after == initial_count, (
            f"リセット後のデータベースエントリ数が初期状態と異なります: {db_count_after} != {initial_count}"
        )

        print(
            "[DEBUG] フィルタリセットテスト成功: 初期状態とリセット後のエントリ数が一致しました"
        )

    def test_database_query_conditions(self, setup_test_data):
        """データベースのクエリ条件をテスト"""
        po_file = setup_test_data
        db = po_file.db

        print("\n[DEBUG] ===== データベースクエリ条件のテスト =====")

        # 1. 条件なしでエントリを取得
        entries_no_condition = db.get_entries()
        count_no_condition = len(entries_no_condition)
        print(f"[DEBUG] 条件なしのエントリ数: {count_no_condition}件")

        # 2. search_text=Noneでエントリを取得
        entries_none = db.get_entries(search_text=None)
        count_none = len(entries_none)
        print(f"[DEBUG] search_text=Noneのエントリ数: {count_none}件")

        # 3. search_text=""（空文字列）でエントリを取得
        entries_empty = db.get_entries(search_text="")
        count_empty = len(entries_empty)
        print(f"[DEBUG] search_text=''のエントリ数: {count_empty}件")

        # 4. search_text="test"でエントリを取得
        entries_test = db.get_entries(search_text="test")
        count_test = len(entries_test)
        print(f"[DEBUG] search_text='test'のエントリ数: {count_test}件")

        # 5. translation_status="all"でエントリを取得
        entries_all = db.get_entries(translation_status="all")
        count_all = len(entries_all)
        print(f"[DEBUG] translation_status='all'のエントリ数: {count_all}件")

        # 6. translation_status="translated"でエントリを取得
        entries_translated = db.get_entries(translation_status="translated")
        count_translated = len(entries_translated)
        print(
            f"[DEBUG] translation_status='translated'のエントリ数: {count_translated}件"
        )

        # 7. 両方の条件を指定してエントリを取得
        entries_both = db.get_entries(translation_status="all", search_text="test")
        count_both = len(entries_both)
        print(
            f"[DEBUG] translation_status='all', search_text='test'のエントリ数: {count_both}件"
        )

        # 8. フィルタ適用後にリセットした場合
        entries_reset = db.get_entries(translation_status="all", search_text=None)
        count_reset = len(entries_reset)
        print(
            f"[DEBUG] translation_status='all', search_text=Noneのエントリ数: {count_reset}件"
        )

        # 検証
        assert count_no_condition == count_none, (
            "条件なしとsearch_text=Noneの結果が一致しません"
        )
        assert count_no_condition == count_empty, (
            "条件なしとsearch_text=''の結果が一致しません"
        )
        assert count_no_condition == count_all, (
            "条件なしとfilter_text='すべて'の結果が一致しません"
        )
        assert count_no_condition == count_reset, (
            "条件なしとリセット後の結果が一致しません"
        )

        print(
            "[DEBUG] データベースクエリ条件テスト成功: 条件なしとリセット後の結果が一致しました"
        )

    def test_filter_reset_with_flag_conditions(self, setup_test_data):
        """フラグ条件を含むフィルタリセットをテスト"""
        po_file = setup_test_data

        print("\n[DEBUG] ===== フラグ条件を含むフィルタリセットのテスト =====")

        # 1. 初期状態の確認
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"[DEBUG] 初期状態のエントリ数: {initial_count}件")

        # 2. フラグ条件を設定
        po_file.flag_conditions = {"only_fuzzy": True}
        print(f"[DEBUG] フラグ条件を設定: {po_file.flag_conditions}")

        # 3. フラグ条件でフィルタリング
        flag_entries = po_file.get_filtered_entries(update_filter=True)
        flag_count = len(flag_entries)
        print(f"[DEBUG] フラグ条件適用後のエントリ数: {flag_count}件")

        # 4. キーワードでさらにフィルタリング
        keyword_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="test"
        )
        keyword_count = len(keyword_entries)
        print(f"[DEBUG] キーワードフィルタ追加後のエントリ数: {keyword_count}件")

        # 5. フラグ条件をリセット
        po_file.flag_conditions = {}
        print(f"[DEBUG] フラグ条件をリセット: {po_file.flag_conditions}")

        # 6. キーワードもリセット
        po_file.search_text = None
        if hasattr(po_file, "_entry_obj_cache"):
            po_file._entry_obj_cache = {}
        po_file.filtered_entries = []
        print("[DEBUG] キーワードとキャッシュをリセット")

        # 7. リセット後のエントリを取得
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=None
        )
        reset_count = len(reset_entries)
        print(f"[DEBUG] 完全リセット後のエントリ数: {reset_count}件")

        # 8. 検証
        assert reset_count == initial_count, (
            f"完全リセット後のエントリ数が初期状態と異なります: {reset_count} != {initial_count}"
        )

        print(
            "[DEBUG] フラグ条件を含むフィルタリセットテスト成功: 初期状態とリセット後のエントリ数が一致しました"
        )
