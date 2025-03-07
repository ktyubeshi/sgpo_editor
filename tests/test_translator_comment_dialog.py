"""翻訳者コメントダイアログのテスト"""
import unittest
from unittest.mock import MagicMock, patch
import uuid

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.gui.widgets.review_widgets import TranslatorCommentWidget


class TestTranslatorCommentDialog(unittest.TestCase):
    """翻訳者コメントダイアログのテスト"""

    @classmethod
    def setUpClass(cls):
        """クラス全体のセットアップ"""
        # QApplicationインスタンスを作成
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """各テスト前の準備"""
        # エントリエディタ作成
        self.entry_editor = EntryEditor()
        
        # モックのシグナルハンドラを設定
        self.entry_editor.text_changed = MagicMock()
        
        # テスト用のエントリを作成
        self.entry1 = EntryModel(
            key=f"test-key-1-{uuid.uuid4()}",
            msgid="Test message 1",
            msgstr="テストメッセージ1",
            tcomment="テスト用コメント1"
        )
        
        self.entry2 = EntryModel(
            key=f"test-key-2-{uuid.uuid4()}",
            msgid="Test message 2",
            msgstr="テストメッセージ2",
            tcomment="テスト用コメント2"
        )

    def tearDown(self):
        """各テスト後のクリーンアップ"""
        # 開いているダイアログを閉じる
        for dialog in self.entry_editor._review_dialogs.values():
            dialog.close()
        self.entry_editor._review_dialogs = {}

    def test_translator_comment_dialog_creation(self):
        """翻訳者コメントダイアログの作成テスト"""
        # エントリをセット
        self.entry_editor.set_entry(self.entry1)
        
        # ダイアログが存在しないことを確認
        self.assertNotIn("translator_comment", self.entry_editor._review_dialogs)
        
        # 翻訳者コメントダイアログを表示
        self.entry_editor._show_review_dialog("translator_comment")
        
        # ダイアログが作成されたことを確認
        self.assertIn("translator_comment", self.entry_editor._review_dialogs)
        dialog = self.entry_editor._review_dialogs["translator_comment"]
        self.assertIsInstance(dialog, QDialog)
        
        # ウィジェットが設定されていることを確認
        self.assertTrue(hasattr(dialog, "widget"))
        self.assertIsInstance(dialog.widget, TranslatorCommentWidget)
        
        # 翻訳者コメントが正しく表示されていることを確認
        self.assertEqual(dialog.widget.comment_edit.toPlainText(), "テスト用コメント1")

    def test_translator_comment_update_on_entry_change(self):
        """エントリ変更時に翻訳者コメントが更新されるかテスト"""
        # エントリをセット
        self.entry_editor.set_entry(self.entry1)
        
        # 翻訳者コメントダイアログを表示
        self.entry_editor._show_review_dialog("translator_comment")
        dialog = self.entry_editor._review_dialogs["translator_comment"]
        
        # 初期状態のコメントを確認
        self.assertEqual(dialog.widget.comment_edit.toPlainText(), "テスト用コメント1")
        
        # 別のエントリに切り替え
        self.entry_editor.set_entry(self.entry2)
        
        # コメントが更新されていることを確認
        self.assertEqual(dialog.widget.comment_edit.toPlainText(), "テスト用コメント2")

    def test_translator_comment_edit_and_apply(self):
        """翻訳者コメントの編集と適用のテスト"""
        # エントリをセット
        self.entry_editor.set_entry(self.entry1)
        
        # 翻訳者コメントダイアログを表示
        self.entry_editor._show_review_dialog("translator_comment")
        dialog = self.entry_editor._review_dialogs["translator_comment"]
        
        # コメントを編集
        new_comment = "編集後のコメント"
        dialog.widget.comment_edit.setPlainText(new_comment)
        
        # 適用ボタンをクリック
        dialog.widget._on_apply_clicked()
        
        # エントリのtcommentが更新されていることを確認
        self.assertEqual(self.entry1.tcomment, new_comment)
        
        # シグナルが発行されたことを確認
        self.entry_editor.text_changed.emit.assert_called()
        
        # エントリを切り替えてから元に戻すと、編集後のコメントが保持されていることを確認
        self.entry_editor.set_entry(self.entry2)
        self.entry_editor.set_entry(self.entry1)
        self.assertEqual(dialog.widget.comment_edit.toPlainText(), new_comment)

    def test_comment_persistence_when_dialog_reopened(self):
        """ダイアログを閉じて再度開いた時にコメントが保持されるかテスト"""
        # エントリをセット
        self.entry_editor.set_entry(self.entry1)
        
        # 翻訳者コメントダイアログを表示
        self.entry_editor._show_review_dialog("translator_comment")
        dialog = self.entry_editor._review_dialogs["translator_comment"]
        
        # コメントを編集して適用
        new_comment = "保存されるべきコメント"
        dialog.widget.comment_edit.setPlainText(new_comment)
        dialog.widget._on_apply_clicked()
        
        # ダイアログを閉じる
        dialog.close()
        
        # 再度ダイアログを開く
        self.entry_editor._show_review_dialog("translator_comment")
        new_dialog = self.entry_editor._review_dialogs["translator_comment"]
        
        # 編集されたコメントが表示されていることを確認
        self.assertEqual(new_dialog.widget.comment_edit.toPlainText(), new_comment)


if __name__ == "__main__":
    unittest.main()
