"""エントリの状態表示テスト"""

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.core.constants import TranslationStatus


def test_get_status_when_obsolete():
    """廃止済みエントリの状態表示テスト"""
    entry = EntryModel(key="test", msgid="test", msgstr="", obsolete=True)
    assert entry.get_status() == TranslationStatus.OBSOLETE


def test_get_status_when_fuzzy():
    """ファジーエントリの状態表示テスト"""
    entry = EntryModel(key="test", msgid="test", msgstr="テスト", flags=["fuzzy"])
    assert entry.get_status() == TranslationStatus.FUZZY


def test_get_status_when_untranslated():
    """未翻訳エントリの状態表示テスト"""
    entry = EntryModel(key="test", msgid="test", msgstr="")
    assert entry.get_status() == TranslationStatus.UNTRANSLATED


def test_get_status_when_translated():
    """翻訳済みエントリの状態表示テスト"""
    entry = EntryModel(key="test", msgid="test", msgstr="テスト")
    assert entry.get_status() == TranslationStatus.TRANSLATED
