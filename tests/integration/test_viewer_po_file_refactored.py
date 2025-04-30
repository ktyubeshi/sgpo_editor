"""ViewerPOFileRefactoredのテスト"""

import os

import pytest
import pytest_asyncio

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored


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
    assert po_file.is_loaded() is True


@pytest.mark.asyncio
async def test_get_entries(test_po_file):
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


@pytest.mark.asyncio
async def test_update_entry(test_po_file):
    """エントリを更新できることを確認する"""
    # エントリを取得
    entry = test_po_file.get_entry_by_key("0")
    assert entry is not None
    assert entry.msgid == "test1"
    assert entry.msgstr == "テスト1"

    # エントリを更新
    entry.msgstr = "更新されたテスト1"
    result = test_po_file.update_entry_model(entry)
    assert result is True

    # 更新されたエントリを確認
    updated_entry = test_po_file.get_entry_by_key("0")
    assert updated_entry is not None
    assert updated_entry.msgid == "test1"
    assert updated_entry.msgstr == "更新されたテスト1"


@pytest.mark.asyncio
async def test_search_entries(test_po_file):
    """エントリを検索できることを確認する"""
    # フィルタリングされたエントリを取得
    entries = test_po_file.get_filtered_entries(filter_keyword="test")
    assert len(entries) == 3

    # 翻訳済みのエントリを取得
    from sgpo_editor.core.constants import TranslationStatus

    # translation_statusを使用して翻訳済みエントリをフィルタリング
    test_po_file.translation_status = TranslationStatus.TRANSLATED
    entries = test_po_file.get_filtered_entries(update_filter=True)
    print(f"Filtered entries (translated): {[ (e.msgid, e.msgstr) for e in entries ]}")
    assert len(entries) == 1
    assert entries[0].msgid == "test1"


@pytest.mark.asyncio
async def test_get_stats(test_po_file):
    """統計情報を取得できることを確認する"""
    stats = test_po_file.get_stats()
    assert stats["total"] == 3
    assert stats["translated"] == 2
    assert stats["fuzzy"] == 1
    assert stats["untranslated"] == 1


@pytest.mark.asyncio
async def test_save_po_file(test_po_file, tmp_path):
    """POファイルを保存できることを確認する"""
    # エントリを更新
    entry = test_po_file.get_entry_by_key("0")
    entry.msgstr = "更新されたテスト1"
    test_po_file.update_entry_model(entry)

    # 保存
    save_path = tmp_path / "saved.po"
    result = await test_po_file.save(save_path)
    assert result is True
    assert os.path.exists(save_path)

    # 保存したファイルを読み込んで確認
    new_po_file = ViewerPOFileRefactored()
    await new_po_file.load(save_path)
    saved_entry = new_po_file.get_entry_by_key("0")
    assert saved_entry is not None
    assert saved_entry.msgstr == "更新されたテスト1"


@pytest.mark.asyncio
async def test_empty_po_file(tmp_path):
    """空のPOファイルを読み込んでもエラーが発生しないことを確認する"""
    empty_po_path = tmp_path / "empty.po"
    with open(empty_po_path, "w", encoding="utf-8") as f:
        f.write("# Empty PO file\nmsgid \"\"\nmsgstr \"\"\n")

    viewer = ViewerPOFileRefactored()
    await viewer.load(empty_po_path)
    assert viewer.is_loaded() is True
    entries = viewer.get_filtered_entries()
    assert len(entries) == 0
    stats = viewer.get_stats()
    assert stats["total"] == 0


@pytest.mark.asyncio
async def test_all_untranslated_entries(tmp_path):
    """すべてのエントリが未翻訳の場合のフィルタリングを確認する"""
    untranslated_po_path = tmp_path / "untranslated.po"
    with open(untranslated_po_path, "w", encoding="utf-8") as f:
        f.write("# Untranslated PO file\n")
        for i in range(3):
            f.write(f"msgid \"untranslated_{i}\"\nmsgstr \"\"\n\n")

    viewer = ViewerPOFileRefactored()
    await viewer.load(untranslated_po_path)
    assert viewer.is_loaded() is True
    
    # 全エントリを確認
    entries = viewer.get_filtered_entries()
    assert len(entries) == 3
    
    # 翻訳済みフィルタを適用
    from sgpo_editor.core.constants import TranslationStatus
    viewer.translation_status = TranslationStatus.TRANSLATED
    entries = viewer.get_filtered_entries(update_filter=True)
    assert len(entries) == 0
    
    # 未翻訳フィルタを適用
    viewer.translation_status = TranslationStatus.UNTRANSLATED
    entries = viewer.get_filtered_entries(update_filter=True)
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_all_fuzzy_entries(tmp_path):
    """すべてのエントリがあいまい (fuzzy) 状態の場合のフィルタリングを確認する"""
    fuzzy_po_path = tmp_path / "fuzzy.po"
    with open(fuzzy_po_path, "w", encoding="utf-8") as f:
        f.write("# Fuzzy PO file\n")
        for i in range(3):
            f.write(f"#, fuzzy\nmsgid \"fuzzy_{i}\"\nmsgstr \"fuzzy translation {i}\"\n\n")

    viewer = ViewerPOFileRefactored()
    await viewer.load(fuzzy_po_path)
    assert viewer.is_loaded() is True
    
    # 全エントリを確認
    entries = viewer.get_filtered_entries()
    assert len(entries) == 3
    
    # 翻訳済みフィルタを適用
    from sgpo_editor.core.constants import TranslationStatus
    viewer.translation_status = TranslationStatus.TRANSLATED
    entries = viewer.get_filtered_entries(update_filter=True)
    assert len(entries) == 0  # Fuzzy entries are not considered translated
    
    # 未翻訳フィルタを適用
    viewer.translation_status = TranslationStatus.UNTRANSLATED
    entries = viewer.get_filtered_entries(update_filter=True)
    assert len(entries) == 0  # Fuzzy entries are not considered untranslated


@pytest.mark.asyncio
async def test_special_characters_entries(tmp_path):
    """特殊文字を含むエントリでの検索とフィルタリングを確認する"""
    special_po_path = tmp_path / "special.po"
    with open(special_po_path, "w", encoding="utf-8") as f:
        f.write("# Special characters PO file\n")
        f.write("msgid \"Hello@World!\"\nmsgstr \"こんにちは@世界！\"\n\n")
        f.write("msgid \"Test#123\"\nmsgstr \"テスト#123\"\n\n")
        f.write("msgid \"Simple\"\nmsgstr \"シンプル\"\n\n")

    viewer = ViewerPOFileRefactored()
    await viewer.load(special_po_path)
    assert viewer.is_loaded() is True
    
    # 全エントリを確認
    entries = viewer.get_filtered_entries()
    assert len(entries) == 3
    
    # 特殊文字で検索
    entries = viewer.get_filtered_entries(filter_keyword="@")
    assert len(entries) == 1
    assert entries[0].msgid == "Hello@World!"
    
    # 別の特殊文字で検索
    entries = viewer.get_filtered_entries(filter_keyword="#")
    assert len(entries) == 1
    assert entries[0].msgid == "Test#123"
