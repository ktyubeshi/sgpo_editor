"""モデルのテスト"""
from unittest.mock import Mock

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.models.stats import StatsModel


def test_entry_model():
    """EntryModelのテスト"""
    # 基本的なエントリのテスト
    entry = EntryModel(
        key="context\x04test",
        msgid="test",
        msgstr="テスト",
        msgctxt="context",
        obsolete=False,
        references=["test.py:10"],
        comment="コメント",
        tcomment="翻訳者コメント",
        flags=["fuzzy"]  # fuzzyフラグをflagsリストで設定
    )

    assert entry.key == "context\x04test"
    assert entry.msgid == "test"
    assert entry.msgstr == "テスト"
    assert entry.msgctxt == "context"
    assert entry.fuzzy  # fuzzyプロパティで確認
    assert not entry.obsolete
    assert entry.references == ["test.py:10"]
    assert entry.comment == "コメント"
    assert entry.tcomment == "翻訳者コメント"

    # キーのテスト
    assert entry.key == "context\x04test"
    entry_without_context = EntryModel(msgid="test", msgstr="テスト")
    assert entry_without_context.key == "|test"

    # 翻訳状態のテスト
    assert not entry.translated()  # fuzzyがTrueなので未翻訳
    entry_not_translated = EntryModel(msgid="test", msgstr="")
    assert not entry_not_translated.translated()  # msgstrが空なので未翻訳
    entry_translated = EntryModel(msgid="test", msgstr="テスト")  # fuzzyフラグなし
    assert entry_translated.translated()  # msgstrがあり、fuzzyがFalseなので翻訳済み

    # 未翻訳のテスト
    untranslated = EntryModel(msgid="test", msgstr="")  # 空文字列を指定
    assert not untranslated.translated()
    assert not untranslated.fuzzy
    assert untranslated.get_status() == "未翻訳"

    # 翻訳済みのテスト
    translated = EntryModel(msgid="test", msgstr="テスト")  # fuzzyフラグなし
    assert translated.translated()
    assert not translated.fuzzy
    assert translated.get_status() == "完了"  # 状態は「完了」

    # フラグのテスト
    entry = EntryModel(msgid="test", msgstr="テスト")
    assert not entry.fuzzy
    assert len(entry.flags) == 0

    # fuzzyプロパティのテスト
    entry.fuzzy = True
    assert entry.fuzzy
    assert "fuzzy" in entry.flags

    entry.fuzzy = False
    assert not entry.fuzzy
    assert "fuzzy" not in entry.flags

    # フラグの追加と削除
    entry.add_flag("python-format")
    assert "python-format" in entry.flags
    assert len(entry.flags) == 1

    entry.add_flag("fuzzy")
    assert entry.fuzzy
    assert len(entry.flags) == 2

    entry.remove_flag("python-format")
    assert "python-format" not in entry.flags
    assert entry.fuzzy
    assert len(entry.flags) == 1

    # 重複フラグの防止
    entry.add_flag("fuzzy")
    assert len(entry.flags) == 1

    # POEntryからの変換テスト
    po_entry = Mock()
    po_entry.msgid = "test"
    po_entry.msgstr = "テスト"
    po_entry.msgctxt = None
    po_entry.flags = ["fuzzy", "python-format"]
    po_entry.obsolete = False
    po_entry.comment = None
    po_entry.tcomment = None
    po_entry.occurrences = []  # イテラブルなリストとして設定
    # previous_msgid と previous_msgctxt 属性を持っていないようにする
    delattr(po_entry, "previous_msgid")
    delattr(po_entry, "previous_msgctxt")
    model = EntryModel.from_po_entry(po_entry)
    assert model.msgid == "test"
    assert model.msgstr == "テスト"
    assert model.msgctxt is None
    assert model.fuzzy
    assert "python-format" in model.flags
    assert not model.obsolete
    assert model.previous_msgid is None
    assert model.previous_msgctxt is None
    assert model.references == []

    # 辞書形式への変換
    data = model.to_dict()
    assert data["key"] == "|test"
    assert data["msgid"] == "test"
    assert data["msgstr"] == "テスト"
    assert data["msgctxt"] is None
    assert data["fuzzy"] is True
    assert "python-format" in data["flags"]
    assert data["obsolete"] is False
    assert data["references"] == []

    # 辞書からの復元
    restored = EntryModel.from_dict(data)
    assert restored.key == model.key
    assert restored.msgid == model.msgid
    assert restored.msgstr == model.msgstr
    assert restored.msgctxt == model.msgctxt
    assert restored.fuzzy == model.fuzzy
    assert "python-format" in restored.flags
    assert restored.obsolete == model.obsolete
    assert restored.references == model.references


def test_stats_model():
    """StatsModelのテスト"""
    stats = StatsModel(
        total=100,
        translated=60,
        untranslated=30,
        fuzzy=10,
        file_name="test.po"
    )

    assert stats.total == 100
    assert stats.translated == 60
    assert stats.untranslated == 30
    assert stats.fuzzy == 10
    assert stats.file_name == "test.po"
    assert stats.progress == 60  # translated / total * 100
