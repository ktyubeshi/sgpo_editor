"""ViewerPOFileのテスト"""

import os
import logging

import pytest
import pytest_asyncio

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored
from sgpo_editor.core.constants import TranslationStatus

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def test_po_file(tmp_path):
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
    await po_file.load(file_path)
    
    return po_file


@pytest.mark.asyncio
async def test_load_po_file(tmp_path):
    """POファイルを読み込めることを確認する"""
    po_file = ViewerPOFileRefactored()
    file_path = tmp_path / "test.po"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('msgid "test"\nmsgstr "テスト"')
    await po_file.load(file_path)
    assert po_file.path == file_path


@pytest.mark.asyncio
async def test_get_entries(test_po_file):
    """エントリを取得できることを確認する"""
    # get_filtered_entriesを使用してエントリを取得
    entries = test_po_file.get_filtered_entries(
        update_filter=True, filter_status=None
    )
    assert len(entries) == 3
    
    # Entryオブジェクトを返すことを確認
    from sgpo_editor.models.entry import EntryModel
    assert all(isinstance(entry, EntryModel) for entry in entries)

    # フィルタリングのテスト
    # 検索テキストを使用したフィルタリング
    test_po_file.search_text = "test1"
    filtered = test_po_file.get_filtered_entries(
        update_filter=True, filter_keyword="test1", filter_status=None
    )
    assert len(filtered) == 1
    assert filtered[0].msgid == "test1"


@pytest.mark.asyncio
async def test_update_entry(test_po_file):
    """エントリを更新できることを確認する"""
    # get_filtered_entriesを使用してエントリを取得
    entries = test_po_file.get_filtered_entries(
        update_filter=True, filter_status=None
    )
    assert len(entries) > 0, "エントリが取得できませんでした"
    
    entry = entries[0]
    entry_key = entry.key

    # エントリを更新
    # Entryオブジェクトの属性を直接更新
    entry.msgstr = "更新テスト"
    test_po_file.update_entry(entry)

    # 更新されたことを確認
    updated = test_po_file.get_entry_by_key(entry_key)
    assert updated is not None
    assert updated.msgstr == "更新テスト"


@pytest.mark.asyncio
async def test_search_entries(test_po_file):
    """エントリを検索できることを確認する"""
    # get_filtered_entriesを使用してエントリを取得
    entries = test_po_file.get_filtered_entries(
        update_filter=True, filter_status=None
    )
    assert len(entries) == 3

    # search_textを使用した検索フィルタリング
    test_po_file.search_text = "test1"
    results = test_po_file.get_filtered_entries(
        update_filter=True, filter_keyword="test1", filter_status=None
    )

    assert len(results) == 1
    assert results[0].msgid == "test1"

    # 検索テキストをクリアして元に戻す
    test_po_file.search_text = ""
    results = test_po_file.get_filtered_entries(
        update_filter=True, filter_keyword="", filter_status=None
    )
    assert len(results) == 3


@pytest.mark.asyncio
async def test_get_stats(test_po_file):
    """統計情報を取得できることを確認する"""
    # get_filtered_entriesを使用してエントリを取得
    entries = test_po_file.get_filtered_entries(
        update_filter=True, filter_status=None
    )
    assert len(entries) == 3, f"エントリ数が期待値と異なります: {len(entries)} != 3"
    
    stats = test_po_file.get_stats()
    assert stats["total"] == 3
    assert stats["translated"] == 1  # test1のみ翻訳済み
    assert stats["fuzzy"] == 1  # test2はfuzzy
    assert stats["untranslated"] == 1  # test3は未翻訳


@pytest.mark.asyncio
async def test_save_po_file(test_po_file, tmp_path):
    """POファイルを保存できることを確認する"""
    # get_filtered_entriesを使用してエントリを取得
    entries = test_po_file.get_filtered_entries(
        update_filter=True, filter_status=None
    )
    assert len(entries) == 3, f"エントリ数が期待値と異なります: {len(entries)} != 3"
    
    save_path = tmp_path / "save.po"
    test_po_file.save(save_path)  # saveメソッドは同期的に動作する
    assert os.path.exists(save_path)
    assert not test_po_file.modified

    # 保存したファイルを読み込んで内容を確認
    loaded = ViewerPOFileRefactored()
    await loaded.load(save_path)
    # get_filtered_entriesを使用してエントリを取得
    entries = loaded.get_filtered_entries(
        update_filter=True, filter_status=None
    )
    assert len(entries) == 3
