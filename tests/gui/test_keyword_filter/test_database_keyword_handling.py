"""データベースの空キーワード処理に関するテスト

このテストでは、データベースクエリに空のキーワードや
Noneが渡された場合の動作を検証します。
"""

import pytest

# テスト対象のモジュールをインポート
from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored


class TestDatabaseKeywordHandling:
    """データベースの空キーワード処理に関するテスト"""

    @pytest.fixture
    def setup_test_data(self):
        """テスト用のPOファイルとデータを設定"""
        # ViewerPOFileRefactoredのインスタンスを作成
        po_file = ViewerPOFileRefactored()

        # テスト用の通常エントリを作成 (testを含まない)
        normal_entries = []
        for i in range(150):
            entry = {
                "key": f"normal_key{i}",
                "msgid": f"normal_msgid{i}",
                "msgstr": f"normal_msgstr{i}",
                "fuzzy": False,
                "translated": True,
            }
            normal_entries.append(entry)

        # キーワード 'test' を含むエントリを作成
        test_entries = []
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
        po_file.db_accessor.add_entries_bulk(normal_entries + test_entries)
        print(
            f"\n[SETUP] データベースに追加したエントリ数: 通常={
                len(normal_entries)
            }件, test含む={len(test_entries)}件"
        )

        # データがロードされたことを示すフラグを設定 (不要)
        # po_file._is_loaded = True

        yield po_file

    def test_database_get_entries_with_empty_keyword(self, setup_test_data):
        """データベースアクセサのget_filtered_entriesメソッドの空キーワード処理をテスト"""
        po_file = setup_test_data
        db_accessor = po_file.db_accessor

        # 1. 初期状態で全エントリを取得
        all_entries = db_accessor.get_filtered_entries()
        all_count = len(all_entries)
        print(f"\n[TEST] データベースからの全エントリ数: {all_count}件")

        # 2. 検索テキストがNoneの場合
        none_entries = db_accessor.get_filtered_entries(search_text=None)
        none_count = len(none_entries)
        print(f"[TEST] search_text=Noneの場合のエントリ数: {none_count}件")
        assert none_count == all_count, "Noneでの検索結果が全エントリと一致しません"

        # 3. 検索テキストが空文字列の場合
        empty_entries = db_accessor.get_filtered_entries(search_text="")
        empty_count = len(empty_entries)
        print(f"[TEST] search_text=''の場合のエントリ数: {empty_count}件")
        assert empty_count == all_count, (
            "空文字列での検索結果が全エントリと一致しません"
        )

        # 4. 検索テキストが空白のみの場合
        space_entries = db_accessor.get_filtered_entries(search_text="  ")
        space_count = len(space_entries)
        print(f"[TEST] search_text='  'の場合のエントリ数: {space_count}件")
        assert space_count == all_count, (
            "空白のみでの検索結果が全エントリと一致しません"
        )

    def test_database_query_construction(self, setup_test_data):
        """データベースのクエリ構築とキーワードフィルタリングのテスト"""
        po_file = setup_test_data
        db_accessor = po_file.db_accessor

        # 1. 初期状態で全エントリを取得
        all_entries = db_accessor.get_filtered_entries()
        all_count = len(all_entries)
        print(f"\n[TEST] 初期状態のエントリ数: {all_count}件")

        # 2. データベースに直接問い合わせてtestキーワードでフィルタリング
        db_test_entries = db_accessor.get_filtered_entries(search_text="test")
        db_test_count = len(db_test_entries)
        print(
            f"[TEST] データベース直接問い合わせ - search_text='test'の場合のエントリ数: {db_test_count}件"
        )
        assert db_test_count < all_count, (
            "データベース直接問い合わせでもtestキーワードのフィルタリングが機能していません"
        )
        assert db_test_count > 0, (
            "データベース直接問い合わせでtestキーワードのフィルタリング結果が0件になっています"
        )

        # 3. ViewerPOFileのget_filtered_entriesを使用してキーワードなしのフィルタリング
        none_entries = po_file.get_filtered_entries(filter_keyword=None)
        none_count = len(none_entries)
        print(f"[TEST] filter_keyword=Noneの場合のエントリ数: {none_count}件")
        assert none_count == all_count, (
            "Noneキーワードでのフィルタリング結果が全エントリと一致しません"
        )

        # 4. 空文字列キーワードでのフィルタリング
        empty_entries = po_file.get_filtered_entries(filter_keyword="")
        empty_count = len(empty_entries)
        print(f"[TEST] filter_keyword=''の場合のエントリ数: {empty_count}件")
        assert empty_count == all_count, (
            "空文字列キーワードでのフィルタリング結果が全エントリと一致しません"
        )

        # 5. 空白文字のみのキーワードでのフィルタリング
        whitespace_entries = po_file.get_filtered_entries(filter_keyword="   ")
        whitespace_count = len(whitespace_entries)
        print(f"[TEST] filter_keyword='   'の場合のエントリ数: {whitespace_count}件")
        assert whitespace_count == all_count, (
            "空白文字のみのキーワードでのフィルタリング結果が全エントリと一致しません"
        )

        # 6. 有効なキーワードでのフィルタリング
        # update_filter=Trueを明示的に指定してキャッシュを無視する
        print("\n[TEST] update_filter=Trueを指定してキーワードフィルタリングを実行")
        test_entries = po_file.get_filtered_entries(
            filter_keyword="test", update_filter=True
        )
        test_count = len(test_entries)
        print(f"[TEST] filter_keyword='test'の場合のエントリ数: {test_count}件")
        assert test_count < all_count, (
            "有効なキーワードでのフィルタリング結果が全エントリと同じになっています"
        )
        assert test_count > 0, (
            "有効なキーワードでのフィルタリング結果が0件になっています"
        )

        # 7. ViewerPOFileのフィルタリング結果とデータベース直接問い合わせの結果が一致するか確認
        assert test_count == db_test_count, (
            "ViewerPOFileのフィルタリング結果とデータベース直接問い合わせの結果が一致しません"
        )

        # 8. キーワードが含まれているか確認
        for entry in test_entries[:5]:  # 最初の5件だけ確認
            msgid = entry.msgid.lower() if hasattr(entry, "msgid") else ""
            msgstr = entry.msgstr.lower() if hasattr(entry, "msgstr") else ""
            key = entry.key.lower() if hasattr(entry, "key") else ""

            found = "test" in msgid or "test" in msgstr or "test" in key
            print(
                f"[TEST] エントリーチェック - key: {entry.key}, 'test'を含む: {found}"
            )
            assert found, f"キーワード'test'がエントリーに含まれていません: {entry.key}"
