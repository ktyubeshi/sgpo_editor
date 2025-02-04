"""ViewerPOFileのテスト"""
import os
from pathlib import Path

import pytest

from po_viewer.core.viewer_po_file import ViewerPOFile
from po_viewer.gui.models.entry import EntryModel


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
    assert not po_file.modified


def test_get_entries(test_po_file):
    """エントリを取得できることを確認する"""
    entries = test_po_file.get_entries()
    assert len(entries) == 3
    assert all(isinstance(entry, EntryModel) for entry in entries)

    translated = test_po_file.get_entries("translated")
    assert len(translated) == 1
    assert translated[0].msgid == "test1"

    untranslated = test_po_file.get_entries("untranslated")
    assert len(untranslated) == 1
    assert untranslated[0].msgid == "test3"

    fuzzy = test_po_file.get_entries("fuzzy")
    assert len(fuzzy) == 1
    assert fuzzy[0].msgid == "test2"


def test_update_entry(test_po_file):
    """エントリを更新できることを確認する"""
    entries = test_po_file.get_entries()
    entry = entries[0]
    entry.msgstr = "更新テスト"
    test_po_file.update_entry(entry)
    assert test_po_file.modified

    updated = test_po_file.get_entries()
    assert updated[0].msgstr == "更新テスト"


def test_search_entries(test_po_file):
    """エントリを検索できることを確認する"""
    entries = test_po_file.search_entries("test1")
    assert len(entries) == 1
    assert entries[0].msgid == "test1"

    entries = test_po_file.search_entries("テスト")
    assert len(entries) == 2
    assert {entry.msgid for entry in entries} == {"test1", "test2"}


def test_get_stats(test_po_file):
    """統計情報を取得できることを確認する"""
    stats = test_po_file.get_stats()
    assert stats.total == 3
    assert stats.translated == 1
    assert stats.untranslated == 2
    assert stats.fuzzy == 1
    assert stats.progress == pytest.approx(33.33, rel=1e-2)


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
