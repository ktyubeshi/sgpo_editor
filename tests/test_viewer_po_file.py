"""ViewerPOFileのテスト"""
import os
from pathlib import Path

import pytest

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.models.entry import EntryModel


@pytest.fixture
def test_po_file(tmp_path):
    """テスト用のPOファイルを作成する"""
    po_file = ViewerPOFile()
    file_path = tmp_path / "test.po"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('''msgid ""
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
''')
    po_file.load(file_path)
    return po_file


def test_load_po_file(tmp_path):
    """POファイルを読み込めることを確認する"""
    po_file = ViewerPOFile()
    file_path = tmp_path / "test.po"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('msgid "test"\nmsgstr "テスト"')
    po_file.load(file_path)
    assert po_file.file_path == file_path


def test_get_entries(test_po_file):
    """エントリを取得できることを確認する"""
    entries = test_po_file.get_entries()
    assert len(entries) == 3
    assert all(isinstance(entry, EntryModel) for entry in entries)

    # フィルタリングのテスト
    filtered = test_po_file.get_filtered_entries(filter_keyword="test1")
    assert len(filtered) == 1
    assert filtered[0].msgid == "test1"


def test_update_entry(test_po_file):
    """エントリを更新できることを確認する"""
    entries = test_po_file.get_entries()
    entry = entries[0]
    entry.msgstr = "更新テスト"
    test_po_file.update_entry(entry)

    # 更新されたことを確認
    updated = test_po_file.get_entry_by_key(entry.key)
    assert updated is not None
    assert updated.msgstr == "更新テスト"


def test_search_entries(test_po_file):
    """エントリを検索できることを確認する"""
    results = test_po_file.search_entries("test1")
    assert len(results) == 1
    assert results[0].msgid == "test1"


def test_get_stats(test_po_file):
    """統計情報を取得できることを確認する"""
    stats = test_po_file.get_stats()
    assert stats.total == 3
    assert stats.translated == 1  # test1のみ翻訳済み
    assert stats.fuzzy == 1  # test2はfuzzy
    assert stats.untranslated == 1  # test3は未翻訳


def test_save_po_file(test_po_file, tmp_path):
    """POファイルを保存できることを確認する"""
    save_path = tmp_path / "save.po"
    test_po_file.save(save_path)
    assert os.path.exists(save_path)
    assert not test_po_file.modified

    # 保存したファイルを読み込んで内容を確認
    loaded = ViewerPOFile(save_path)
    entries = loaded.get_entries()
    assert len(entries) == 3
