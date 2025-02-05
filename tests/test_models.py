"""モデルのテスト"""
import pytest
from po_viewer.gui.models.entry import EntryModel
from po_viewer.gui.models.stats import StatsModel
from unittest.mock import Mock

def test_entry_model():
    """EntryModelのテスト"""
    entry = EntryModel(
        msgid="test",
        msgstr="テスト",
        msgctxt="context",
        fuzzy=True,
        obsolete=False,
        references=["test.py:10"],
        comment="コメント",
        tcomment="翻訳者コメント"
    )
    
    assert entry.msgid == "test"
    assert entry.msgstr == "テスト"
    assert entry.msgctxt == "context"
    assert entry.fuzzy
    assert not entry.obsolete
    assert entry.references == ["test.py:10"]
    assert entry.comment == "コメント"
    assert entry.tcomment == "翻訳者コメント"

    # キーのテスト
    assert entry.key == "context|test"
    entry_without_context = EntryModel(msgid="test", msgstr="テスト")
    assert entry_without_context.key == "|test"

    # 翻訳状態のテスト
    assert entry.translated()
    assert entry.is_fuzzy()
    assert entry.get_status() == "ファジー"

    # 未翻訳のテスト
    untranslated = EntryModel(msgid="test")
    assert not untranslated.translated()
    assert not untranslated.is_fuzzy()
    assert untranslated.get_status() == "未翻訳"

    # 翻訳済みのテスト
    translated = EntryModel(msgid="test", msgstr="テスト", fuzzy=False)
    assert translated.translated()
    assert not translated.is_fuzzy()
    assert translated.get_status() == "翻訳済み"

    # POEntryからの変換テスト
    po_entry = Mock()
    po_entry.msgid = "test"
    po_entry.msgstr = "テスト"
    po_entry.msgctxt = None
    po_entry.flags = ["fuzzy"]
    po_entry.obsolete = False
    po_entry.comment = None
    po_entry.tcomment = None
    po_entry.references = []
    # previous_msgid と previous_msgstr 属性を持っていないようにする
    delattr(po_entry, "previous_msgid")
    delattr(po_entry, "previous_msgstr")
    model = EntryModel.from_po_entry(po_entry)
    assert model.msgid == "test"
    assert model.msgstr == "テスト"
    assert model.msgctxt is None
    assert model.fuzzy
    assert not model.obsolete
    assert model.previous_msgid is None
    assert model.previous_msgstr is None
    assert model.references == []

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
