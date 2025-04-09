"""メタデータUI機能のテスト"""

import sys
import json
import pytest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Qt

from sgpo_editor.gui.metadata_dialog import MetadataEditDialog, MetadataValueEditor
from sgpo_editor.gui.metadata_panel import MetadataPanel
from sgpo_editor.models.entry import EntryModel


@pytest.fixture
def app():
    """テスト用QApplicationインスタンス"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def entry():
    """テスト用EntryModelインスタンス"""
    entry = EntryModel(key="test_key", msgid="test_msgid", msgstr="test_msgstr")

    # テスト用メタデータを追加
    entry.add_metadata("category", "UI")
    entry.add_metadata("priority", 1)
    entry.add_metadata("tags", ["important", "needs-review"])
    entry.add_metadata("context", {"screen": "login", "position": "header"})

    return entry


class TestMetadataEditDialog:
    """MetadataEditDialogのテスト"""

    def test_init_and_load_metadata(self, app, entry, qtbot):
        """初期化とメタデータ読み込みのテスト"""
        dialog = MetadataEditDialog(entry)
        qtbot.addWidget(dialog)

        # ダイアログの初期状態を確認
        assert dialog.metadata_table.rowCount() == 4

        # メタデータの内容を確認
        assert dialog.metadata_table.item(0, 0).text() == "category"
        assert dialog.metadata_table.item(0, 1).text() == "UI"

        assert dialog.metadata_table.item(1, 0).text() == "priority"
        assert dialog.metadata_table.item(1, 1).text() == "1"

        assert dialog.metadata_table.item(2, 0).text() == "tags"
        assert json.loads(dialog.metadata_table.item(2, 1).text()) == [
            "important",
            "needs-review",
        ]

        assert dialog.metadata_table.item(3, 0).text() == "context"
        assert json.loads(dialog.metadata_table.item(3, 1).text()) == {
            "screen": "login",
            "position": "header",
        }

    def test_add_metadata(self, app, entry, qtbot):
        """メタデータ追加のテスト"""
        dialog = MetadataEditDialog(entry)
        qtbot.addWidget(dialog)

        # 新しいメタデータを追加
        dialog.key_edit.setText("new_key")
        dialog.value_edit.setText("new_value")

        # 追加ボタンをクリック
        add_button = dialog.findChild(QPushButton, "add_button")
        qtbot.mouseClick(add_button, Qt.MouseButton.LeftButton)

        # テーブルに追加されていることを確認
        assert dialog.metadata_table.rowCount() == 5
        assert dialog.metadata_table.item(4, 0).text() == "new_key"
        assert dialog.metadata_table.item(4, 1).text() == "new_value"

    def test_save_metadata(self, app, entry, qtbot):
        """メタデータ保存のテスト"""
        dialog = MetadataEditDialog(entry)
        qtbot.addWidget(dialog)

        # 新しいメタデータを追加
        dialog.key_edit.setText("new_key")
        dialog.value_edit.setText("new_value")

        # 追加ボタンをクリック
        add_button = dialog.findChild(QPushButton, "add_button")
        qtbot.mouseClick(add_button, Qt.MouseButton.LeftButton)

        # 保存ボタンをクリック
        save_button = dialog.findChild(QPushButton, "save_button")
        with patch.object(dialog, "accept") as mock_accept:
            qtbot.mouseClick(save_button, Qt.MouseButton.LeftButton)
            assert mock_accept.called

        # エントリのメタデータが更新されていることを確認
        assert "new_key" in entry.get_all_metadata()
        assert entry.get_metadata("new_key") == "new_value"

    def test_convert_value(self, app, entry, qtbot):
        """値の型変換のテスト"""
        dialog = MetadataEditDialog(entry)
        qtbot.addWidget(dialog)

        # 文字列
        assert dialog.convert_value("test", "文字列") == "test"

        # 数値
        assert dialog.convert_value("123", "数値") == 123
        assert isinstance(dialog.convert_value("123.45", "数値"), float)
        assert dialog.convert_value("123.45", "数値") == 123.45

        # 真偽値
        assert dialog.convert_value("true", "真偽値") is True
        assert dialog.convert_value("false", "真偽値") is False
        assert dialog.convert_value("1", "真偽値") is True
        assert dialog.convert_value("0", "真偽値") is False

        # リスト
        assert dialog.convert_value("[1, 2, 3]", "リスト") == [1, 2, 3]
        assert dialog.convert_value('["a", "b", "c"]', "リスト") == ["a", "b", "c"]

        # 辞書
        assert dialog.convert_value('{"a": 1, "b": 2}', "辞書") == {"a": 1, "b": 2}

    def test_format_value_for_display(self, app, entry, qtbot):
        """表示用の値フォーマットのテスト"""
        dialog = MetadataEditDialog(entry)
        qtbot.addWidget(dialog)

        # 文字列
        assert dialog.format_value_for_display("test") == "test"

        # 数値
        assert dialog.format_value_for_display(123) == "123"
        assert dialog.format_value_for_display(123.45) == "123.45"

        # 真偽値
        assert dialog.format_value_for_display(True) == "True"
        assert dialog.format_value_for_display(False) == "False"

        # リスト
        assert dialog.format_value_for_display([1, 2, 3]) == "[1, 2, 3]"

        # 辞書
        assert dialog.format_value_for_display({"a": 1, "b": 2}) == '{"a": 1, "b": 2}'

    def test_get_value_type(self, app, entry, qtbot):
        """値の型判定のテスト"""
        dialog = MetadataEditDialog(entry)
        qtbot.addWidget(dialog)

        # 文字列
        assert dialog.get_value_type("test") == "文字列"

        # 数値
        assert dialog.get_value_type(123) == "数値"
        assert dialog.get_value_type(123.45) == "数値"

        # 真偽値
        assert dialog.get_value_type(True) == "真偽値"
        assert dialog.get_value_type(False) == "真偽値"

        # リスト
        assert dialog.get_value_type([1, 2, 3]) == "リスト"

        # 辞書
        assert dialog.get_value_type({"a": 1, "b": 2}) == "辞書"


class TestMetadataValueEditor:
    """MetadataValueEditorのテスト"""

    def test_init(self, app, qtbot):
        """初期化のテスト"""
        # 文字列
        editor = MetadataValueEditor("test", "文字列")
        qtbot.addWidget(editor)
        assert editor.text_edit.text() == "test"

        # 数値
        editor = MetadataValueEditor(123, "数値")
        qtbot.addWidget(editor)
        assert editor.text_edit.text() == "123"

        # リスト
        editor = MetadataValueEditor([1, 2, 3], "リスト")
        qtbot.addWidget(editor)
        assert json.loads(editor.text_edit.text()) == [1, 2, 3]

        # 辞書
        editor = MetadataValueEditor({"a": 1, "b": 2}, "辞書")
        qtbot.addWidget(editor)
        assert json.loads(editor.text_edit.text()) == {"a": 1, "b": 2}

    def test_get_value(self, app, qtbot):
        """値の取得のテスト"""
        # 文字列
        editor = MetadataValueEditor("test", "文字列")
        qtbot.addWidget(editor)
        assert editor.get_value() == "test"

        # 数値
        editor = MetadataValueEditor(123, "数値")
        qtbot.addWidget(editor)
        assert editor.get_value() == 123

        # 真偽値
        editor = MetadataValueEditor(True, "真偽値")
        qtbot.addWidget(editor)
        assert editor.get_value() is True

        # リスト
        editor = MetadataValueEditor([1, 2, 3], "リスト")
        qtbot.addWidget(editor)
        assert editor.get_value() == [1, 2, 3]

        # 辞書
        editor = MetadataValueEditor({"a": 1, "b": 2}, "辞書")
        qtbot.addWidget(editor)
        assert editor.get_value() == {"a": 1, "b": 2}


class TestMetadataPanel:
    """MetadataPanelのテスト"""

    def test_init(self, app, qtbot):
        """初期化のテスト"""
        panel = MetadataPanel()
        qtbot.addWidget(panel)

        # 初期状態では空
        assert panel.tree.topLevelItemCount() == 0
        assert panel.edit_button.isEnabled() is False

    def test_set_entry(self, app, entry, qtbot):
        """エントリ設定のテスト"""
        panel = MetadataPanel()
        qtbot.addWidget(panel)

        # エントリを設定
        panel.set_entry(entry)

        # メタデータが表示されていることを確認
        assert panel.tree.topLevelItemCount() == 4

        # 編集ボタンが有効化されていることを確認
        assert panel.edit_button.isEnabled() is True

        # エントリがNoneの場合
        panel.set_entry(None)
        assert panel.edit_button.isEnabled() is False

    def test_update_display(self, app, entry, qtbot):
        """表示更新のテスト"""
        panel = MetadataPanel()
        qtbot.addWidget(panel)

        # エントリを設定
        panel.set_entry(entry)

        # メタデータの内容を確認
        category_item = panel.tree.topLevelItem(0)
        assert category_item.text(0) == "category"
        assert category_item.text(1) == "UI"

        priority_item = panel.tree.topLevelItem(1)
        assert priority_item.text(0) == "priority"
        assert priority_item.text(1) == "1"

        tags_item = panel.tree.topLevelItem(2)
        assert tags_item.text(0) == "tags"
        assert tags_item.text(1) == ""  # 複合型は空文字列
        assert tags_item.childCount() == 2

        context_item = panel.tree.topLevelItem(3)
        assert context_item.text(0) == "context"
        assert context_item.text(1) == ""  # 複合型は空文字列
        assert context_item.childCount() == 2

        # メタデータがない場合
        entry.clear_metadata()
        panel.update_display()
        assert panel.tree.topLevelItemCount() == 1
        assert panel.tree.topLevelItem(0).text(1) == "メタデータなし"

    def test_request_edit(self, app, entry, qtbot):
        """編集リクエストのテスト"""
        panel = MetadataPanel()
        qtbot.addWidget(panel)

        # シグナルをモック
        panel.edit_requested = MagicMock()

        # エントリを設定
        panel.set_entry(entry)

        # 編集ボタンをクリック
        qtbot.mouseClick(panel.edit_button, Qt.MouseButton.LeftButton)

        # シグナルが発行されたことを確認
        panel.edit_requested.emit.assert_called_once_with(entry)
