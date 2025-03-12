#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
"""レビュー機能関連ウィジェットのテスト"""

import unittest
from unittest.mock import Mock

from sgpo_editor.gui.widgets.review_widgets import (CheckResultWidget,
                                                    QualityScoreWidget,
                                                    ReviewCommentWidget,
                                                    TranslatorCommentWidget)
from sgpo_editor.models.entry import EntryModel


class TestTranslatorCommentWidget(unittest.TestCase):
    """TranslatorCommentウィジェットのテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.widget = TranslatorCommentWidget()
        self.entry = EntryModel(
            key="test_key",
            msgid="Test Message ID",
            msgstr="テストメッセージ",
            tcomment="This is a translator comment",
        )

    def test_widget_creation(self):
        """ウィジェットが正しく作成されるかテスト"""
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget.windowTitle(), "翻訳者コメント")

    def test_set_entry(self):
        """エントリ設定が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        # ウィジェット内のテキストエリアに翻訳者コメントが表示されるか確認
        self.assertEqual(
            self.widget.comment_edit.toPlainText(), "This is a translator comment"
        )

    def test_set_entry_none(self):
        """Noneエントリ設定が正しく動作するかテスト"""
        self.widget.set_entry(None)
        # ウィジェットが空になっているか確認
        self.assertEqual(self.widget.comment_edit.toPlainText(), "")


class TestReviewCommentWidget(unittest.TestCase):
    """ReviewCommentウィジェットのテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.widget = ReviewCommentWidget()
        self.entry = EntryModel(
            key="test_key", msgid="Test Message ID", msgstr="テストメッセージ"
        )
        # レビューコメント追加
        self.entry.add_review_comment(
            author="Reviewer1", comment="This is a review comment"
        )
        self.entry.add_review_comment(author="Reviewer2", comment="Another comment")

        # モックデータベースを設定
        self.mock_db = Mock()
        self.mock_db.add_review_comment = Mock(return_value=True)
        self.mock_db.remove_review_comment = Mock(return_value=True)

        # ウィジェットにデータベースを設定
        self.widget.set_database(self.mock_db)

    def test_widget_creation(self):
        """ウィジェットが正しく作成されるかテスト"""
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget.windowTitle(), "レビューコメント")

    def test_set_entry(self):
        """エントリ設定が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        # コメント数に応じたアイテムが表示されるか確認
        self.assertEqual(self.widget.comment_list.count(), 2)

    def test_add_comment(self):
        """コメント追加が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        initial_count = self.widget.comment_list.count()

        # テキスト入力とボタンクリックをシミュレート
        self.widget.author_edit.setText("TestAuthor")
        self.widget.comment_edit.setPlainText("New test comment")
        self.widget.add_button.click()

        # コメントが追加されているか確認
        self.assertEqual(self.widget.comment_list.count(), initial_count + 1)
        self.assertEqual(len(self.entry.review_comments), initial_count + 1)

        # 最新のコメントを確認
        latest_comment = self.entry.review_comments[-1]
        self.assertEqual(latest_comment["comment"], "New test comment")
        self.assertEqual(latest_comment["author"], "TestAuthor")

        # モックデータベースのadd_review_commentメソッドが呼ばれたか確認
        self.mock_db.add_review_comment.assert_called_once()

    def test_remove_comment(self):
        """コメント削除が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        initial_count = self.widget.comment_list.count()

        # 最初のアイテムを選択
        self.widget.comment_list.setCurrentRow(0)

        # 削除ボタンクリックをシミュレート
        self.widget.remove_button.click()

        # コメントが削除されているか確認
        self.assertEqual(self.widget.comment_list.count(), initial_count - 1)
        self.assertEqual(len(self.entry.review_comments), initial_count - 1)

        # モックデータベースのremove_review_commentメソッドが呼ばれたか確認
        self.mock_db.remove_review_comment.assert_called_once()


class TestQualityScoreWidget(unittest.TestCase):
    """QualityScoreウィジェットのテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.widget = QualityScoreWidget()
        self.entry = EntryModel(
            key="test_key", msgid="Test Message ID", msgstr="テストメッセージ"
        )
        # 品質スコア設定
        self.entry.set_overall_quality_score(85)
        self.entry.set_category_score("accuracy", 90)
        self.entry.set_category_score("fluency", 80)

        # モックデータベースを設定
        self.mock_db = Mock()
        self.mock_db.update_entry_field = Mock(return_value=True)
        self.mock_db.add_review_comment = Mock(return_value=True)
        self.mock_db.remove_review_comment = Mock(return_value=True)

        # ウィジェットにデータベースを設定
        self.widget.set_database(self.mock_db)

    def test_widget_creation(self):
        """ウィジェットが正しく作成されるかテスト"""
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget.windowTitle(), "品質スコア")

    def test_set_entry(self):
        """エントリ設定が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        # 全体スコアの表示を確認
        self.assertEqual(self.widget.overall_score_spinner.value(), 85)
        # カテゴリスコアが表示されているか確認
        self.assertEqual(self.widget.category_scores_table.rowCount(), 2)

    def test_update_overall_score(self):
        """全体スコア更新が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        # スピナーの値を変更
        self.widget.overall_score_spinner.setValue(75)
        self.widget.apply_button.click()

        # エントリのスコアが更新されているか確認
        self.assertEqual(self.entry.overall_quality_score, 75)
        # モックデータベースのupdate_entry_fieldメソッドが呼ばれたか確認
        self.mock_db.update_entry_field.assert_called_with(
            self.entry.key, "overall_quality_score", 75
        )

    def test_add_category_score(self):
        """カテゴリスコア追加が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        initial_row_count = self.widget.category_scores_table.rowCount()

        # カテゴリとスコアを入力
        self.widget.category_edit.setText("style")
        self.widget.category_score_spinner.setValue(95)
        self.widget.add_category_button.click()

        # テーブルに行が追加されているか確認
        self.assertEqual(
            self.widget.category_scores_table.rowCount(), initial_row_count + 1
        )
        # エントリにカテゴリスコアが追加されているか確認
        self.assertEqual(self.entry.category_quality_scores["style"], 95)
        # モックデータベースのupdate_entry_fieldメソッドが呼ばれたか確認
        self.mock_db.update_entry_field.assert_called_with(
            self.entry.key,
            "category_quality_scores",
            self.entry.category_quality_scores,
        )


class TestCheckResultWidget(unittest.TestCase):
    """CheckResultウィジェットのテスト"""

    def setUp(self):
        """テスト前の準備"""
        self.widget = CheckResultWidget()
        self.entry = EntryModel(
            key="test_key", msgid="Test Message ID", msgstr="テストメッセージ"
        )
        # チェック結果追加
        self.entry.add_check_result(1001, "用語の不一致", "warning")
        self.entry.add_check_result(2002, "末尾の句読点がない", "error")

    def test_widget_creation(self):
        """ウィジェットが正しく作成されるかテスト"""
        self.assertIsNotNone(self.widget)
        self.assertEqual(self.widget.windowTitle(), "チェック結果")

    def test_set_entry(self):
        """エントリ設定が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        # チェック結果の数を確認
        self.assertEqual(self.widget.result_table.rowCount(), 2)

    def test_add_check_result(self):
        """チェック結果追加が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        initial_row_count = self.widget.result_table.rowCount()

        # チェック結果情報を入力
        self.widget.code_spinner.setValue(3003)
        self.widget.message_edit.setPlainText("新しいエラー")
        self.widget.severity_combo.setCurrentText("info")
        self.widget.add_button.click()

        # テーブルに行が追加されているか確認
        self.assertEqual(self.widget.result_table.rowCount(), initial_row_count + 1)
        # エントリにチェック結果が追加されているか確認
        self.assertEqual(len(self.entry.check_results), initial_row_count + 1)
        newest_result = self.entry.check_results[-1]
        self.assertEqual(newest_result["code"], 3003)
        self.assertEqual(newest_result["message"], "新しいエラー")
        self.assertEqual(newest_result["severity"], "info")

    def test_remove_check_result(self):
        """チェック結果削除が正しく動作するかテスト"""
        self.widget.set_entry(self.entry)
        initial_row_count = self.widget.result_table.rowCount()

        # 最初の行を選択
        self.widget.result_table.selectRow(0)
        self.widget.remove_button.click()

        # 行が削除されているか確認
        self.assertEqual(self.widget.result_table.rowCount(), initial_row_count - 1)
        # エントリからチェック結果が削除されているか確認
        self.assertEqual(len(self.entry.check_results), initial_row_count - 1)


if __name__ == "__main__":
    unittest.main()
