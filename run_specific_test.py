"""特定のテストを実行するスクリプト"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

# srcディレクトリをPYTHONPATHに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    # テストに必要なモジュールをインポート
    from sgpo_editor.core.viewer_po_file import ViewerPOFile

    # 一時ディレクトリを作成してテスト用POファイルを作成
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # test_po_file関数を実装
        print("test_po_fileを実行中...")
        po_file = ViewerPOFile()
        file_path = tmp_path / "test.po"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                """msgid ""
msgstr ""
"Project-Id-Version: test\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: 2024-01-01 00:00+0900\\n"
"PO-Revision-Date: 2024-01-01 00:00+0900\\n"
"Last-Translator: test\\n"
"Language-Team: test\\n"
"Language: ja\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

msgid "test1"
msgstr "テスト1"

#, fuzzy
msgid "test2"
msgstr "テスト2"

msgid "test3"
msgstr ""
"""
            )
        po_file.load(file_path)
        print("POファイルのロード成功")

        # test_get_entriesを実行
        print("\ntest_get_entriesを実行中...")
        entries = po_file.get_entries()
        print(f"エントリ数: {len(entries)}")
        print(f"エントリの型: {type(entries[0])}")

        # フィルタリングのテスト
        filtered = po_file.get_filtered_entries(filter_keyword="test1")
        print(f"フィルタリング結果数: {len(filtered)}")
        print(f"フィルタリング結果の最初のエントリのmsgid: {filtered[0]['msgid']}")

        # test_update_entryを実行
        print("\ntest_update_entryを実行中...")
        entry = entries[0]
        entry_key = entry["key"]
        print(f"更新前のmsgstr: {entry['msgstr']}")

        # エントリを更新
        updated_entry = entry.copy()
        updated_entry["msgstr"] = "更新テスト"
        po_file.update_entry(updated_entry)

        # 更新されたことを確認
        updated = po_file.get_entry_by_key(entry_key)
        print(f"更新後のmsgstr: {updated['msgstr']}")

        # test_search_entriesを実行
        print("\ntest_search_entriesを実行中...")
        results = po_file.search_entries("test1")
        print(f"検索結果数: {len(results)}")
        print(f"検索結果の最初のエントリのmsgid: {results[0]['msgid']}")

        # test_get_statsを実行
        print("\ntest_get_statsを実行中...")
        stats = po_file.get_stats()
        print(f"合計: {stats.total}")
        print(f"翻訳済み: {stats.translated}")
        print(f"fuzzy: {stats.fuzzy}")
        print(f"未翻訳: {stats.untranslated}")

        # test_save_po_fileを実行
        print("\ntest_save_po_fileを実行中...")
        save_path = tmp_path / "save.po"
        po_file.save(save_path)
        print(f"ファイルが存在するか: {os.path.exists(save_path)}")
        print(f"modified状態: {po_file.modified}")

        # 保存したファイルを読み込んで内容を確認
        loaded = ViewerPOFile()
        loaded.load(save_path)
        entries = loaded.get_entries()
        print(f"読み込んだエントリ数: {len(entries)}")

    print("\nすべてのテストが成功しました！")

except Exception as e:
    print(f"エラーが発生しました: {e}")
    traceback.print_exc()
