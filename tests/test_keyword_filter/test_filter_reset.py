"""フィルタリセットに関するテスト

このテストでは、フィルタを適用した後にキーワードを空にした場合に、
すべてのエントリが表示されるかどうかを検証します。
"""

import pytest

# テスト対象のモジュールをインポート
from sgpo_editor.core.viewer_po_file import ViewerPOFile


class TestFilterReset:
    """フィルタリセットに関するテスト"""

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

    def test_filter_reset_full_simulation(self, setup_test_data):
        """フィルタをリセットした際に全エントリが表示されるかの完全シミュレーション"""
        po_file = setup_test_data

        # 1. 初期状態の確認
        print(
            f"\n[TEST] ViewerPOFile初期状態: search_text={
                po_file.search_text}, filter_text={
                po_file.filter_text}"
        )

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
        assert (
            reset_count == initial_count
        ), f"フィルタリセット後のエントリ数が初期状態と異なります: {reset_count} != {initial_count}"

        # ログ出力
        print(
            "[TEST] フィルタリセットテスト成功: 初期状態とリセット後のエントリ数が一致しました"
        )

    def test_filter_reset_with_po_state(self, setup_test_data):
        """ViewerPOFileの状態を使った詳細テスト"""
        po_file = setup_test_data

        # 1. 状態を調査
        print(
            f"\n[TEST] ViewerPOFile初期状態: search_text={
                po_file.search_text}, filter_text={
                po_file.filter_text}"
        )

        # 2. 初期状態で全エントリを取得
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"[TEST] 初期状態のエントリ数: {initial_count}件")

        # 3. フィルタを適用（'test'で検索）
        print("[TEST] 'test'フィルタを適用...")
        filtered_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="test"
        )
        filtered_count = len(filtered_entries)
        print(f"[TEST] 'test'フィルタ適用後のエントリ数: {filtered_count}件")

        # 状態を調査（問題発生時はここで値がキャッシュされている可能性）
        print(
            f"[TEST] フィルタ後のViewerPOFile状態: search_text={
                po_file.search_text}, filter_text={
                po_file.filter_text}"
        )
        print(
            f"[TEST] ViewerPOFile内部キャッシュ: _entry_obj_cache件数={
                len(
                    po_file._entry_obj_cache) if hasattr(
                    po_file,
                    '_entry_obj_cache') else 'なし'}"
        )

        # 4. フィルタをリセット（空文字列に設定）
        print("[TEST] フィルタをリセット...")
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=""
        )
        reset_count = len(reset_entries)
        print(f"[TEST] フィルタリセット後のエントリ数: {reset_count}件")

        # 状態を再度調査（ここが重要な調査ポイント）
        print(
            f"[TEST] リセット後のViewerPOFile状態: search_text={
                po_file.search_text}, filter_text={
                po_file.filter_text}"
        )
        print(
            f"[TEST] リセット後の内部キャッシュ: _entry_obj_cache件数={
                len(
                    po_file._entry_obj_cache) if hasattr(
                    po_file,
                    '_entry_obj_cache') else 'なし'}"
        )

        # 5. 検証: リセット後のエントリ数が初期状態と同じになるはず
        assert (
            reset_count == initial_count
        ), f"フィルタリセット後のエントリ数が初期状態と異なります: {reset_count} != {initial_count}"

        # 6. データベースから直接取得して比較
        db_entries = po_file.db.get_entries(search_text=None)
        db_count = len(db_entries)
        print(f"[TEST] データベースから直接取得したエントリ数: {db_count}件")

        # データベース取得結果と初期状態が一致するか検証
        assert (
            db_count == initial_count
        ), f"データベースから取得したエントリ数が初期状態と異なります: {db_count} != {initial_count}"

        # 7. 内部状態をNoneに設定して再度テスト
        print("[TEST] 直接Noneを設定してテスト...")
        po_file.search_text = None
        po_file.filtered_entries = []
        if hasattr(po_file, "_entry_obj_cache"):
            po_file._entry_obj_cache = {}
        none_entries = po_file.get_filtered_entries(update_filter=True)
        none_count = len(none_entries)
        print(f"[TEST] search_text=None設定後のエントリ数: {none_count}件")

        # Noneでの取得結果が初期状態と一致するか検証
        assert (
            none_count == initial_count
        ), f"None設定後のエントリ数が初期状態と異なります: {none_count} != {initial_count}"

    def test_filter_reset_multiple_operations(self, setup_test_data):
        """複数回のフィルタリング操作後のリセットテスト"""
        po_file = setup_test_data

        # 1. 初期状態の確認
        initial_entries = po_file.get_filtered_entries()
        initial_count = len(initial_entries)
        print(f"\n[TEST] 初期状態のエントリ数: {initial_count}件")

        # 2. 最初のフィルタを適用 ('test'で検索)
        po_file.get_filtered_entries(update_filter=True, filter_keyword="test")
        print(f"[TEST] 1回目のフィルタ適用後: search_text={po_file.search_text}")

        # 3. 2回目のフィルタを適用 ('msgstr'で検索)
        po_file.get_filtered_entries(update_filter=True, filter_keyword="msgstr")
        print(f"[TEST] 2回目のフィルタ適用後: search_text={po_file.search_text}")

        # 4. 3回目のフィルタを適用 ('key'で検索)
        po_file.get_filtered_entries(update_filter=True, filter_keyword="key")
        print(f"[TEST] 3回目のフィルタ適用後: search_text={po_file.search_text}")

        # 5. 完全リセット (空文字列でなくNoneを直接使用)
        print("[TEST] 完全リセット実行...")
        po_file.search_text = None
        po_file.filtered_entries = []
        if hasattr(po_file, "_entry_obj_cache"):
            po_file._entry_obj_cache = {}

        # 6. リセット後のエントリを取得
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=None
        )
        reset_count = len(reset_entries)
        print(f"[TEST] 複数フィルタ後のリセット結果: {reset_count}件")

        # 7. 検証
        assert (
            reset_count == initial_count
        ), f"複数回フィルタ後のリセット結果が初期状態と異なります: {reset_count} != {initial_count}"

    def test_database_get_entries_with_empty_keyword(self, setup_test_data):
        """データベースのget_entriesメソッドの空キーワード処理をテスト"""
        po_file = setup_test_data
        db = po_file.db

        # 1. 初期状態で全エントリを取得
        all_entries = db.get_entries()
        all_count = len(all_entries)
        print(f"\n[TEST] データベースからの全エントリ数: {all_count}件")

        # 2. 検索テキストがNoneの場合
        none_entries = db.get_entries(search_text=None)
        none_count = len(none_entries)
        print(f"[TEST] search_text=Noneの場合のエントリ数: {none_count}件")
        assert none_count == all_count, "Noneでの検索結果が全エントリと一致しません"

        # 3. 検索テキストが空文字列の場合
        empty_entries = db.get_entries(search_text="")
        empty_count = len(empty_entries)
        print(f"[TEST] search_text=''の場合のエントリ数: {empty_count}件")
        assert (
            empty_count == all_count
        ), "空文字列での検索結果が全エントリと一致しません"

        # 4. 検索テキストが空白のみの場合
        space_entries = db.get_entries(search_text="  ")
        space_count = len(space_entries)
        print(f"[TEST] search_text='  'の場合のエントリ数: {space_count}件")
        assert (
            space_count == all_count
        ), "空白のみでの検索結果が全エントリと一致しません"

    def test_entry_conversion_with_cache(self, setup_test_data):
        """エントリの変換とキャッシュの動作をテスト"""
        po_file = setup_test_data

        # 1. キャッシュの初期状態を確認
        if not hasattr(po_file, "_entry_obj_cache"):
            po_file._entry_obj_cache = {}
        initial_cache_size = len(po_file._entry_obj_cache)
        print(f"\n[TEST] キャッシュの初期サイズ: {initial_cache_size}件")

        # 2. エントリを取得してキャッシュを構築
        entries = po_file.get_filtered_entries(update_filter=True)
        initial_count = len(entries)
        after_get_cache_size = len(po_file._entry_obj_cache)
        print(f"[TEST] エントリ取得後のキャッシュサイズ: {after_get_cache_size}件")
        print(f"[TEST] 初期状態のエントリ数: {initial_count}件")

        # 3. 特定のキーワードでフィルタリング
        filtered_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword="test"
        )
        filtered_count = len(filtered_entries)
        filtered_cache_size = len(po_file._entry_obj_cache)
        print(f"[TEST] フィルタリング後のキャッシュサイズ: {filtered_cache_size}件")
        print(f"[TEST] フィルタリング後のエントリ数: {filtered_count}件")

        # 4. キャッシュをクリア
        po_file._entry_obj_cache = {}
        # search_textもリセットする必要がある
        po_file.search_text = None
        # filtered_entriesもクリア
        po_file.filtered_entries = []
        print("[TEST] キャッシュを手動でクリア、search_textをNoneに設定")

        # 5. フィルタリングをリセット
        reset_entries = po_file.get_filtered_entries(
            update_filter=True, filter_keyword=None
        )
        reset_count = len(reset_entries)
        reset_cache_size = len(po_file._entry_obj_cache)
        print(f"[TEST] リセット後のキャッシュサイズ: {reset_cache_size}件")
        print(f"[TEST] リセット後のエントリ数: {reset_count}件")

        # 6. 検証: リセット後のエントリ数が初期状態と同じになるはず
        assert (
            reset_count == initial_count
        ), f"リセット後のエントリ数が想定と異なります: {reset_count} != {initial_count}"
