"""デバッグウィンドウのテスト"""
import unittest
from unittest.mock import MagicMock, patch
import json
import uuid

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.gui.widgets.debug_widgets import EntryDebugWidget


class TestDebugWindow(unittest.TestCase):
    """デバッグウィンドウのテスト"""

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
        
        # テスト用のエントリを作成
        self.test_entry = EntryModel(
            key=f"test-key-{uuid.uuid4()}",
            msgid="Test message",
            msgstr="テストメッセージ",
            tcomment="テスト用コメント",
            flags=["fuzzy"],
            references=["test.py:10", "sample.py:20"],
        )
        
        # レビューデータを追加
        self.test_entry.add_review_comment("テスト太郎", "これはテストコメントです")
        self.test_entry.set_quality_score(85)
        self.test_entry.set_category_score("正確性", 90)
        self.test_entry.add_check_result("warning", "警告テスト", "warning")
        
        # エントリをセット
        self.entry_editor.set_entry(self.test_entry)

    def tearDown(self):
        """各テスト後のクリーンアップ"""
        # 開いているダイアログを閉じる
        for dialog in self.entry_editor._review_dialogs.values():
            dialog.close()
        self.entry_editor._review_dialogs = {}

    def test_debug_window_creation(self):
        """デバッグウィンドウの作成テスト"""
        # デバッグウィンドウが存在しないことを確認
        self.assertNotIn("debug", self.entry_editor._review_dialogs)
        
        # デバッグウィンドウを表示
        self.entry_editor._show_review_dialog("debug")
        
        # ダイアログが作成されたことを確認
        self.assertIn("debug", self.entry_editor._review_dialogs)
        dialog = self.entry_editor._review_dialogs["debug"]
        self.assertIsInstance(dialog, QDialog)
        
        # ウィジェットが設定されていることを確認
        self.assertTrue(hasattr(dialog, "widget"))
        self.assertIsInstance(dialog.widget, EntryDebugWidget)
        
        # デバッグテキストにエントリ情報が含まれていることを確認
        debug_text = dialog.widget.debug_text.toPlainText()
        
        # 基本情報の確認
        self.assertIn("key", debug_text)
        self.assertIn("msgid", debug_text)
        self.assertIn("msgstr", debug_text)
        self.assertIn("tcomment", debug_text)
        
        # フラグ情報の確認
        self.assertIn("fuzzy", debug_text)
        
        # 参照情報の確認
        self.assertIn("test.py:10", debug_text)
        self.assertIn("sample.py:20", debug_text)
        
        # レビューデータの確認
        self.assertIn("テスト太郎", debug_text)
        self.assertIn("これはテストコメントです", debug_text)
        self.assertIn("85", debug_text)  # 品質スコア
        self.assertIn("90", debug_text)  # カテゴリスコア
        self.assertIn("warning", debug_text)  # チェック結果

    def test_debug_window_update_on_entry_change(self):
        """エントリ変更時にデバッグウィンドウが更新されるかテスト"""
        # デバッグウィンドウを表示
        self.entry_editor._show_review_dialog("debug")
        dialog = self.entry_editor._review_dialogs["debug"]
        
        # 初期状態のデバッグテキストを記録
        initial_debug_text = dialog.widget.debug_text.toPlainText()
        
        # 別のエントリを作成
        new_entry = EntryModel(
            key=f"new-key-{uuid.uuid4()}",
            msgid="New message",
            msgstr="新しいメッセージ",
            tcomment="新しいコメント",
        )
        
        # 新しいエントリをセット
        self.entry_editor.set_entry(new_entry)
        
        # デバッグテキストが更新されたことを確認
        updated_debug_text = dialog.widget.debug_text.toPlainText()
        self.assertNotEqual(initial_debug_text, updated_debug_text)
        
        # 新しいエントリの情報が表示されていることを確認
        self.assertIn("New message", updated_debug_text)
        self.assertIn("新しいメッセージ", updated_debug_text)
        self.assertIn("新しいコメント", updated_debug_text)
        self.assertNotIn("テスト太郎", updated_debug_text)  # 古いエントリのデータがないことを確認


if __name__ == "__main__":
    unittest.main()
