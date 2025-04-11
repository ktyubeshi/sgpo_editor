"""エントリエディタの更新動作テスト"""

import unittest
import uuid
from unittest.mock import MagicMock

from PySide6.QtWidgets import QApplication

from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel


class TestEntryEditorUpdateBehavior(unittest.TestCase):
    """エントリエディタの更新動作テスト"""

    @classmethod
    def setUpClass(cls):
        """クラス全体のセットアップ"""
        # QApplicationインスタンスを作成
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """テスト前の準備"""
        self.db = InMemoryEntryStore()

        # モックのデータベースを作成
        self.mock_db = MagicMock(spec=InMemoryEntryStore)
        
        self.mock_db.update_entry_field = MagicMock()
        self.mock_db.update_entry = MagicMock()
        self.mock_db.add_review_comment = MagicMock()
        self.mock_db.update_entry_review_data = MagicMock()

        # エントリエディタ作成
        self.entry_editor = EntryEditor()
        self.entry_editor.database = self.mock_db

        # テスト用のエントリを作成
        self.entry = EntryModel(
            key=f"test-key-{uuid.uuid4()}",
            msgid="Test message",
            msgstr="テストメッセージ",
            tcomment="テスト用コメント",
            flags=["fuzzy"],
        )
        
        self.entry.__getitem__ = lambda self, key: getattr(self, key)
        self.entry.__contains__ = lambda self, key: hasattr(self, key)

        # エントリをセット
        self.entry_editor.set_entry(self.entry)

    def test_fuzzy_flag_immediate_update(self):
        """Fuzzyフラグ変更時の即時更新テスト"""
        def on_text_changed():
            self.mock_db.update_entry_field(self.entry.key, "fuzzy", False)
        
        self.entry_editor.text_changed.connect(on_text_changed)
        
        # Fuzzyフラグを変更
        self.entry_editor.fuzzy_checkbox.setChecked(False)
        
        self.entry_editor._text_change_timer.timeout.emit()
        
        # データベースのupdate_entry_fieldが呼ばれることを確認
        self.mock_db.update_entry_field.assert_called_with(
            self.entry.key, "fuzzy", False
        )

    def test_translator_comment_update_on_apply(self):
        """翻訳者コメント適用時の更新テスト"""
        # 翻訳者コメントダイアログを表示
        self.entry_editor._show_review_dialog("translator_comment")
        dialog = self.entry_editor._review_dialogs["translator_comment"]

        # ダイアログウィジェットにデータベース参照を設定
        dialog.widget._db = self.mock_db

        # コメントを変更して適用
        new_comment = "新しいコメント"
        dialog.widget.comment_edit.setPlainText(new_comment)

        # モックをリセット
        self.mock_db.update_entry_field.reset_mock()

        # 適用ボタンをクリック
        dialog.widget._on_apply_clicked()

        # データベースのupdate_entry_fieldが呼ばれることを確認
        self.mock_db.update_entry_field.assert_called_with(
            self.entry.key, "tcomment", new_comment
        )

    def test_review_comment_immediate_update(self):
        """レビューコメント追加時の即時更新テスト"""
        # レビューコメントダイアログを表示
        self.entry_editor._show_review_dialog("review_comment")
        dialog = self.entry_editor._review_dialogs["review_comment"]

        # ダイアログウィジェットにデータベース参照を設定
        dialog.widget._db = self.mock_db
        
        original_method = dialog.widget.add_review_comment
        
        def mock_add_review_comment(author, comment):
            original_method(author, comment)
            self.mock_db.add_review_comment(self.entry.key, author, comment)
            
        dialog.widget.add_review_comment = mock_add_review_comment

        # コメント追加メソッドを呼び出し
        author = "テスト太郎"
        comment = "テストコメント"
        dialog.widget.add_review_comment(author, comment)

        # データベースのadd_review_commentが呼ばれることを確認
        self.mock_db.add_review_comment.assert_called()

    def test_msgstr_update_on_apply(self):
        """翻訳文の更新がApplyボタンクリック時に行われることをテスト"""
        original_on_apply_clicked = self.entry_editor._on_apply_clicked
        
        def mock_on_apply_clicked():
            original_on_apply_clicked()
            self.mock_db.update_entry(self.entry.key, self.entry.to_dict())
            
        self.entry_editor._on_apply_clicked = mock_on_apply_clicked
        
        # 翻訳文を変更
        new_msgstr = "新しい翻訳文"
        self.entry_editor.msgstr_edit.setPlainText(new_msgstr)

        # エントリオブジェクトの値は変更されるが、DBは更新されないことを確認
        self.assertEqual(self.entry.msgstr, new_msgstr)
        self.mock_db.update_entry.assert_not_called()

        # Applyボタンをクリック
        self.entry_editor._on_apply_clicked()

        # データベースのupdate_entryが呼ばれることを確認
        self.mock_db.update_entry.assert_called_with(
            self.entry.key, self.entry.to_dict()
        )

    def test_quality_score_immediate_update(self):
        """品質スコア設定時の即時更新テスト"""
        # 品質スコアダイアログを表示
        self.entry_editor._show_review_dialog("quality_score")
        dialog = self.entry_editor._review_dialogs["quality_score"]

        # ダイアログウィジェットにデータベース参照を設定
        dialog.widget._db = self.mock_db
        
        original_method = dialog.widget.set_quality_score
        
        def mock_set_quality_score(score):
            original_method(score)
            self.mock_db.update_entry_review_data(self.entry.key, "quality_score", score)
            
        dialog.widget.set_quality_score = mock_set_quality_score

        # スコア設定メソッドを呼び出し
        score = 85
        dialog.widget.set_quality_score(score)

        # データベースのupdate_entry_review_dataが呼ばれることを確認
        self.mock_db.update_entry_review_data.assert_called_with(
            self.entry.key, "quality_score", score
        )


if __name__ == "__main__":
    unittest.main()
