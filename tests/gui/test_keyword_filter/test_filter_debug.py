"""キーワードフィルタの問題を特定するためのデバッグテスト

このテストでは、キーワードフィルタリングの問題を特定するために、
詳細なデバッグ情報を出力し、フィルタリングの前後でエントリ数が
一致することを確認します。
"""

import logging

import pytest

# テスト対象のモジュールをインポート
from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored

logger = logging.getLogger(__name__)


class TestFilterDebug:
    """キーワードフィルタの問題を特定するためのデバッグテスト"""

    @pytest.fixture
    def setup_test_data(self):
        """テスト用のPOファイルとデータを設定"""
        # ViewerPOFileRefactoredのインスタンスを作成
        po_file = ViewerPOFileRefactored()

        # テスト用のエントリを作成
        test_entries = [
            {"key": "key1", "msgid": "msgid 1", "msgstr": "msgstr 1"},
            {"key": "key2", "msgid": "msgid 2", "msgstr": "msgstr 2"},
            {"key": "debug", "msgid": "debug id", "msgstr": "debug str"},
        ]

        # データベースにエントリを追加 (db_accessor経由)
        po_file.db_accessor.add_entries_bulk(test_entries)

        # データがロードされたことを示すフラグを設定 (テスト簡略化)
        # po_file._is_loaded = True # 内部状態への直接アクセスは避ける

        yield po_file

    def test_filter_reset_with_debug_prints(self, setup_test_data):
        """デバッグプリントを含むフィルタリセットテスト"""
        po_file = setup_test_data

        logger.info("\n--- デバッグテスト開始 ---")

        # 1. 初期状態の確認
        # logger.debug(
        #     f"[DEBUG] ViewerPOFile状態: search_text={po_file.search_text}, translation_status={po_file.translation_status}"
        # )
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        logger.debug(f"[DEBUG] 初期状態のエントリ数: {initial_count}件")
        logger.debug("初期状態の全エントリ:")
        for entry in initial_entries:
            logger.debug(f"  - {entry.key}: {entry.msgid}")

        # 2. フィルタを適用（'debug'で検索）
        logger.debug("\n[DEBUG] 'debug'フィルタ適用")
        filtered_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="debug"
        )
        filtered_count = len(filtered_entries)
        logger.debug(f"[DEBUG] 'debug'フィルタ適用後のエントリ数: {filtered_count}件")
        # logger.debug(
        #     f"[DEBUG] ViewerPOFile状態: search_text={po_file.search_text}, translation_status={po_file.translation_status}"
        # )
        logger.debug("フィルタ適用後のエントリ:")
        for entry in filtered_entries:
            logger.debug(f"  - {entry.key}: {entry.msgid}")

        # 3. フィルタをリセット（空文字列）
        logger.debug("\n[DEBUG] フィルタをリセット (空文字列)")
        # print("[DEBUG] リセット前のViewerPOFile状態:")
        # print(
        #     f"  search_text: {po_file.search_text}"
        # )
        # print(
        #     f"  filtered_entries: {[e.key for e in po_file.filtered_entries] if po_file.filtered_entries else '[]'}"
        # )
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=""
        )
        reset_count = len(reset_entries)
        logger.debug(f"[DEBUG] フィルタリセット後のエントリ数: {reset_count}件")
        # logger.debug(
        #     f"[DEBUG] ViewerPOFile状態: search_text={po_file.search_text}, translation_status={po_file.translation_status}"
        # )
        logger.debug("リセット後の全エントリ:")
        for entry in reset_entries:
            logger.debug(f"  - {entry.key}: {entry.msgid}")

        # 4. 検証: リセット後のエントリ数が初期状態と同じになるはず
        logger.debug(
            f"\n[DEBUG] 検証: リセット後({reset_count}) == 初期状態({
                initial_count
            }) -> {reset_count == initial_count}"
        )
        assert reset_count == initial_count, (
            f"フィルタリセット後のエントリ数が初期状態と異なります: {reset_count} != {initial_count}"
        )

        # 5. データベースから直接取得して比較 (db_accessor経由)
        db_entries = po_file.db_accessor.get_filtered_entries(search_text=None)
        db_count = len(db_entries)
        logger.debug(f"[DEBUG] データベース直接取得のエントリ数: {db_count}件")
        assert db_count == initial_count, "データベース取得結果が初期状態と異なります"

        logger.info("--- デバッグテスト終了 ---")

    def test_database_query_conditions(self, setup_test_data):
        """データベースのクエリ条件をテスト"""
        po_file = setup_test_data
        db = po_file.db_accessor

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
