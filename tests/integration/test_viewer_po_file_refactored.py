"""ViewerPOFileRefactoredのテスト"""

import os

import pytest

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored


@pytest.fixture
def test_po_file(tmp_path):
    """テスト用のPOファイルを作成する"""
    po_file = ViewerPOFileRefactored()
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
    return po_file


def test_load_po_file(tmp_path):
    """POファイルを読み込めることを確認する"""
    po_file = ViewerPOFileRefactored()
    file_path = tmp_path / "test.po"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('msgid "test"\nmsgstr "テスト"')
    po_file.load(file_path)
    assert po_file._is_loaded is True


def test_get_entries(test_po_file):
    """エントリを取得できることを確認する"""
    # キーを指定してエントリを取得
    entry = test_po_file.get_entry_by_key("0")
    assert entry is not None
    assert entry.msgid == "test1"
    assert entry.msgstr == "テスト1"

    # 位置を指定してエントリを取得
    entry = test_po_file.get_entry_at(1)
    assert entry is not None
    assert entry.msgid == "test2"
    assert entry.msgstr == "テスト2"
    assert entry.fuzzy is True

    # 互換性のためのエイリアスを使用
    entry = test_po_file.get_entry("2")
    assert entry is not None
    assert entry.msgid == "test3"
    assert entry.msgstr == ""


def test_update_entry(test_po_file):
    """エントリを更新できることを確認する"""
    # エントリを取得
    entry = test_po_file.get_entry_by_key("0")
    assert entry is not None
    assert entry.msgid == "test1"
    assert entry.msgstr == "テスト1"

    # エントリを更新
    entry.msgstr = "更新されたテスト1"
    result = test_po_file.update_entry(entry)
    assert result is True

    # 更新されたエントリを確認
    updated_entry = test_po_file.get_entry_by_key("0")
    assert updated_entry is not None
    assert updated_entry.msgid == "test1"
    assert updated_entry.msgstr == "更新されたテスト1"


def test_search_entries(test_po_file):
    """エントリを検索できることを確認する"""
    # フィルタリングされたエントリを取得
    entries = test_po_file.get_filtered_entries(filter_keyword="test")
    assert len(entries) == 3

    # 翻訳済みのエントリを取得
    from sgpo_editor.core.constants import TranslationStatus

    entries = test_po_file.get_filtered_entries(
        filter_text=TranslationStatus.TRANSLATED
    )
    assert len(entries) == 1
    assert entries[0].msgid == "test1"


def test_get_stats(test_po_file):
    """統計情報を取得できることを確認する"""
    stats = test_po_file.get_stats()
    assert stats.total == 3
    assert stats.translated == 1
    assert stats.fuzzy == 1
    assert stats.untranslated == 1


def test_save_po_file(test_po_file, tmp_path):
    """POファイルを保存できることを確認する"""
    # エントリを更新
    entry = test_po_file.get_entry_by_key("0")
    entry.msgstr = "更新されたテスト1"
    test_po_file.update_entry(entry)

    # 保存
    save_path = tmp_path / "saved.po"
    result = test_po_file.save(save_path)
    assert result is True
    assert os.path.exists(save_path)

    # 保存したファイルを読み込んで確認
    new_po_file = ViewerPOFileRefactored()
    new_po_file.load(save_path)
    saved_entry = new_po_file.get_entry_by_key("0")
    assert saved_entry is not None
    assert saved_entry.msgstr == "更新されたテスト1"
