"""メタデータ永続化のテスト"""

import json
import pytest
from polib import POEntry

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.utils.metadata_utils import (
    extract_metadata_from_comment,
    create_comment_with_metadata,
    METADATA_PREFIX,
)


def test_add_metadata():
    """エントリにメタデータを追加できることをテスト"""
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳")
    
    # メタデータの追加
    entry.add_metadata("category", "UI")
    entry.add_metadata("priority", 1)
    
    # メタデータが正しく追加されていることを確認
    assert entry.metadata["category"] == "UI"
    assert entry.metadata["priority"] == 1


def test_get_metadata():
    """エントリからメタデータを取得できることをテスト"""
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳")
    
    # メタデータの追加
    entry.add_metadata("category", "Document")
    entry.add_metadata("priority", 2)
    
    # メタデータが正しく取得できることを確認
    assert entry.get_metadata("category") == "Document"
    assert entry.get_metadata("priority") == 2
    
    # 存在しないキーにはデフォルト値が返ることを確認
    assert entry.get_metadata("not_exist") is None
    assert entry.get_metadata("not_exist", "default") == "default"


def test_remove_metadata():
    """エントリからメタデータを削除できることをテスト"""
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳")
    
    # メタデータの追加
    entry.add_metadata("category", "UI")
    entry.add_metadata("priority", 1)
    
    # メタデータが存在することを確認
    assert "category" in entry.metadata
    assert "priority" in entry.metadata
    
    # メタデータを削除
    result = entry.remove_metadata("category")
    
    # 削除に成功したことを確認
    assert result is True
    assert "category" not in entry.metadata
    assert "priority" in entry.metadata
    
    # 存在しないキーの削除を試みる
    result = entry.remove_metadata("not_exist")
    assert result is False


def test_clear_metadata():
    """エントリのすべてのメタデータをクリアできることをテスト"""
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳")
    
    # メタデータの追加
    entry.add_metadata("category", "UI")
    entry.add_metadata("priority", 1)
    
    # メタデータが存在することを確認
    assert len(entry.metadata) == 2
    
    # すべてのメタデータをクリア
    entry.clear_metadata()
    
    # すべてのメタデータが削除されたことを確認
    assert len(entry.metadata) == 0


def test_get_all_metadata():
    """エントリのすべてのメタデータを取得できることをテスト"""
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳")
    
    # メタデータの追加
    entry.add_metadata("category", "UI")
    entry.add_metadata("priority", 1)
    
    # すべてのメタデータを取得
    all_metadata = entry.get_all_metadata()
    
    # すべてのメタデータが正しく取得できたことを確認
    assert len(all_metadata) == 2
    assert all_metadata["category"] == "UI"
    assert all_metadata["priority"] == 1
    
    # 返されたオブジェクトが元のメタデータのコピーであることを確認
    all_metadata["new_key"] = "value"
    assert "new_key" not in entry.metadata


def test_metadata_persistence_to_po_entry():
    """メタデータがPOEntryに永続化されることをテスト"""
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳")
    
    # メタデータの追加
    entry.add_metadata("category", "UI")
    entry.add_metadata("priority", 1)
    entry.add_metadata("complex", {"key": "value", "list": [1, 2, 3]})
    
    # POEntryに変換
    po_entry = entry.to_po_entry()
    
    # POEntryのcommentフィールドにメタデータが含まれていることを確認
    assert METADATA_PREFIX in po_entry.comment
    
    # commentからメタデータを抽出
    metadata = extract_metadata_from_comment(po_entry.comment)
    
    # 抽出したメタデータが元のメタデータと一致することを確認
    assert metadata["category"] == "UI"
    assert metadata["priority"] == 1
    assert metadata["complex"]["key"] == "value"
    assert metadata["complex"]["list"] == [1, 2, 3]


def test_metadata_persistence_with_existing_comment():
    """既存のコメントがある場合でもメタデータが正しく永続化されることをテスト"""
    existing_comment = "This is an existing comment."
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳", comment=existing_comment)
    
    # メタデータの追加
    entry.add_metadata("category", "UI")
    
    # POEntryに変換
    po_entry = entry.to_po_entry()
    
    # 既存のコメントとメタデータ両方が含まれていることを確認
    assert existing_comment in po_entry.comment
    assert METADATA_PREFIX in po_entry.comment
    
    # コメントからメタデータを抽出
    metadata = extract_metadata_from_comment(po_entry.comment)
    
    # 抽出したメタデータが元のメタデータと一致することを確認
    assert metadata["category"] == "UI"


def test_metadata_extraction_from_po_entry():
    """POEntryからメタデータが正しく抽出されることをテスト"""
    # メタデータを含むコメントを作成
    metadata = {"category": "UI", "priority": 1}
    comment = create_comment_with_metadata(None, metadata)
    
    # メタデータを含むPOEntryを作成
    po_entry = POEntry(msgid="source", msgstr="翻訳", comment=comment)
    
    # POEntryからEntryModelを作成
    entry = EntryModel.from_po_entry(po_entry)
    
    # メタデータが正しく抽出されたことを確認
    assert entry.metadata["category"] == "UI"
    assert entry.metadata["priority"] == 1


def test_round_trip_metadata():
    """メタデータのラウンドトリップ変換をテスト"""
    # 元のメタデータ
    original_metadata = {
        "category": "UI",
        "priority": 1,
        "tags": ["important", "visible"],
        "nested": {"key1": "value1", "key2": "value2"}
    }
    
    # メタデータを含むEntryModelを作成
    entry = EntryModel(key="test", msgid="source", msgstr="翻訳")
    for key, value in original_metadata.items():
        entry.add_metadata(key, value)
    
    # POEntryに変換
    po_entry = entry.to_po_entry()
    
    # 再度EntryModelに変換
    new_entry = EntryModel.from_po_entry(po_entry)
    
    # メタデータが正しく保持されていることを確認
    assert new_entry.metadata == original_metadata
