"""翻訳品質評価ダイアログのテスト"""

import sys
import pytest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QMainWindow

from sgpo_editor.gui.translation_evaluate_dialog import (
    TranslationEvaluateDialog,
    TranslationEvaluationResultWindow,
    METADATA_EVALUATION_SCORE,
    METADATA_EVALUATION_STATE,
    METADATA_EVALUATION_METRICS,
    METADATA_EVALUATION_COMMENTS,
    METADATA_EVALUATION_MODEL,
    METADATA_EVALUATION_DATE
)
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.models.evaluation_state import EvaluationState


@pytest.fixture
def app():
    """QApplicationのフィクスチャ"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def dialog(app, qtbot):
    """翻訳品質評価ダイアログのフィクスチャ"""
    dialog = TranslationEvaluateDialog()
    qtbot.addWidget(dialog)
    return dialog


@pytest.fixture
def result_window(app, qtbot, sample_entries):
    """翻訳品質評価結果ウィンドウのフィクスチャ"""
    window = TranslationEvaluationResultWindow(sample_entries[1])
    qtbot.addWidget(window)
    return window


@pytest.fixture
def sample_entries():
    """サンプルエントリのフィクスチャ"""
    entries = [
        EntryModel(
            key="entry1",
            msgid="Hello",
            msgstr="こんにちは",
            evaluation_state=EvaluationState.NOT_EVALUATED,
        ),
        EntryModel(
            key="entry2",
            msgid="Goodbye",
            msgstr="さようなら",
            evaluation_state=EvaluationState.EVALUATED,
        ),
        EntryModel(
            key="entry3",
            msgid="Thank you",
            msgstr="ありがとう",
            evaluation_state=EvaluationState.EVALUATING,
        ),
    ]
    
    # 2番目のエントリにスコアとレビューコメントを設定
    entries[1].score = 85
    entries[1].set_metric_score("accuracy", 90)
    entries[1].set_metric_score("fluency", 80)
    
    # レビューコメントを追加（languageパラメータなし）
    entries[1].add_review_comment("テスト太郎", "翻訳の品質は良好です")
    entries[1].add_review_comment("Test User", "The translation quality is good")
    
    # 2番目のエントリにメタデータとして評価結果を保存
    entries[1].add_metadata(METADATA_EVALUATION_SCORE, 85)
    entries[1].add_metadata(METADATA_EVALUATION_STATE, str(EvaluationState.EVALUATED))
    entries[1].add_metadata(METADATA_EVALUATION_METRICS, {"accuracy": 90, "fluency": 80})
    entries[1].add_metadata(METADATA_EVALUATION_MODEL, "GPT-4")
    entries[1].add_metadata(METADATA_EVALUATION_DATE, "2025-03-16T12:34:56")
    
    # メタデータにコメントを直接設定（言語情報を含む）
    entries[1].add_metadata(METADATA_EVALUATION_COMMENTS, [
        {"author": "テスト太郎", "comment": "翻訳の品質は良好です", "language": "ja"},
        {"author": "Test User", "comment": "The translation quality is good", "language": "en"}
    ])
    
    return entries


class TestTranslationEvaluateDialog:
    """翻訳品質評価ダイアログのテストクラス"""

    def test_dialog_creation(self, dialog):
        """ダイアログの作成テスト"""
        # ダイアログが正しく作成されていることを確認
        assert dialog.windowTitle() == "翻訳品質評価"
        
        # 評価設定の要素を確認
        assert dialog.target_current_radio.isChecked()
        assert dialog.model_combo.count() > 0
        assert dialog.accuracy_check.isChecked()
        assert dialog.fluency_check.isChecked()

    def test_set_entries(self, dialog, sample_entries):
        """エントリリスト設定テスト"""
        # エントリリストを設定
        dialog.set_entries(sample_entries)
        
        # エントリリストが正しく設定されていることを確認
        assert len(dialog._entries) == 3
        assert dialog._entries[0].key == "entry1"
        assert dialog._entries[1].key == "entry2"
        assert dialog._entries[2].key == "entry3"

    @patch("sgpo_editor.gui.translation_evaluate_dialog.QMessageBox.warning")
    def test_run_evaluation_no_entry(self, mock_warning, dialog):
        """エントリなしでの評価実行テスト"""
        # 現在のエントリが設定されていない状態で評価実行
        dialog.target_current_radio.setChecked(True)
        dialog._run_evaluation()
        
        # 警告メッセージが表示されることを確認
        mock_warning.assert_called_once()

    @patch("sgpo_editor.gui.translation_evaluate_dialog.QMessageBox.information")
    @patch("sgpo_editor.gui.translation_evaluate_dialog.TranslationEvaluationResultWindow")
    def test_run_evaluation_with_entry(self, mock_result_window, mock_info, dialog, sample_entries):
        """エントリありでの評価実行テスト"""
        # エントリを設定
        dialog.set_current_entry(sample_entries[0])
        dialog.set_entries(sample_entries)
        
        # モックメインウィンドウを作成
        mock_main_window = MagicMock(spec=QMainWindow)
        dialog.parent = MagicMock(return_value=mock_main_window)
        
        # モック結果ウィンドウのインスタンスを設定
        mock_result_instance = MagicMock()
        mock_result_window.return_value = mock_result_instance
        
        # 評価実行
        dialog.target_current_radio.setChecked(True)
        dialog._run_evaluation()
        
        # 情報メッセージが表示されることを確認
        mock_info.assert_called_once()
        
        # 進捗バーが非表示になっていることを確認
        assert not dialog.progress_bar.isVisible()
        
        # 結果ウィンドウが表示されることを確認
        mock_result_window.assert_called_once_with(sample_entries[0], mock_main_window)
        mock_result_instance.show.assert_called_once()
        
        # メタデータに評価結果が保存されていることを確認
        metadata = sample_entries[0].get_all_metadata()
        assert METADATA_EVALUATION_SCORE in metadata
        assert METADATA_EVALUATION_STATE in metadata
        assert METADATA_EVALUATION_METRICS in metadata
        assert METADATA_EVALUATION_MODEL in metadata
        assert METADATA_EVALUATION_DATE in metadata
        assert METADATA_EVALUATION_COMMENTS in metadata

    @patch("sgpo_editor.gui.translation_evaluate_dialog.QMessageBox.information")
    def test_run_evaluation_all_entries(self, mock_info, dialog, sample_entries):
        """全エントリ評価テスト"""
        # エントリを設定
        dialog.set_entries(sample_entries)
        
        # 全エントリを評価対象に設定
        dialog.target_all_radio.setChecked(True)
        
        # _show_evaluation_resultをモック
        dialog._show_evaluation_result = MagicMock()
        
        # 評価実行
        dialog._run_evaluation()
        
        # 情報メッセージが表示されることを確認
        mock_info.assert_called_once()
        
        # メッセージに「3件のエントリ」が含まれていることを確認
        args, kwargs = mock_info.call_args
        assert "3件のエントリ" in args[2]
        
        # 結果ウィンドウが表示されることを確認
        dialog._show_evaluation_result.assert_called_once()
        
        # すべてのエントリにメタデータが設定されていることを確認
        for entry in sample_entries:
            metadata = entry.get_all_metadata()
            assert METADATA_EVALUATION_SCORE in metadata
            assert METADATA_EVALUATION_STATE in metadata
            assert METADATA_EVALUATION_METRICS in metadata

    @patch("sgpo_editor.gui.translation_evaluate_dialog.QMessageBox.information")
    def test_run_evaluation_unevaluated_entries(self, mock_info, dialog, sample_entries):
        """未評価エントリのみの評価テスト"""
        # エントリを設定
        dialog.set_entries(sample_entries)
        
        # 未評価エントリのみを評価対象に設定
        dialog.target_untranslated_radio.setChecked(True)
        
        # _show_evaluation_resultをモック
        dialog._show_evaluation_result = MagicMock()
        
        # 評価実行
        dialog._run_evaluation()
        
        # 情報メッセージが表示されることを確認
        mock_info.assert_called_once()
        
        # メッセージに「1件のエントリ」が含まれていることを確認
        args, kwargs = mock_info.call_args
        assert "1件のエントリ" in args[2]
        
        # 結果ウィンドウが表示されることを確認
        dialog._show_evaluation_result.assert_called_once()

    def test_evaluation_metrics_selection(self, dialog, sample_entries, monkeypatch):
        """評価指標選択テスト"""
        # エントリを設定
        dialog.set_current_entry(sample_entries[0])
        
        # すべての指標をオフにする
        dialog.accuracy_check.setChecked(False)
        dialog.fluency_check.setChecked(False)
        dialog.consistency_check.setChecked(False)
        dialog.style_check.setChecked(False)
        dialog.terminology_check.setChecked(False)
        
        # QMessageBox.warningをモック
        warning_called = False
        def mock_warning(*args, **kwargs):
            nonlocal warning_called
            warning_called = True
            return QMessageBox.Ok
        
        monkeypatch.setattr(QMessageBox, "warning", mock_warning)
        
        # 評価実行
        dialog._run_evaluation()
        
        # 警告メッセージが表示されることを確認
        assert warning_called
        
        # 1つの指標をオンにする
        dialog.accuracy_check.setChecked(True)
        
        # QMessageBox.informationをモック
        info_called = False
        def mock_info(*args, **kwargs):
            nonlocal info_called
            info_called = True
            return QMessageBox.Ok
        
        monkeypatch.setattr(QMessageBox, "information", mock_info)
        
        # _show_evaluation_resultをモック
        dialog._show_evaluation_result = MagicMock()
        
        # 評価実行
        dialog._run_evaluation()
        
        # 情報メッセージが表示されることを確認
        assert info_called
        
    def test_save_evaluation_to_metadata(self, dialog, sample_entries):
        """評価結果のメタデータ保存テスト"""
        # エントリを設定
        entry = sample_entries[0]
        
        # 評価結果をメタデータに保存
        metric_scores = {"accuracy": 90, "fluency": 85}
        dialog._save_evaluation_to_metadata(entry, 88, metric_scores, "GPT-4", "日本語")
        
        # メタデータに保存されていることを確認
        metadata = entry.get_all_metadata()
        assert metadata[METADATA_EVALUATION_SCORE] == 88
        assert metadata[METADATA_EVALUATION_STATE] == str(entry.evaluation_state)
        assert metadata[METADATA_EVALUATION_METRICS] == metric_scores
        assert metadata[METADATA_EVALUATION_MODEL] == "GPT-4"
        assert METADATA_EVALUATION_DATE in metadata


class TestTranslationEvaluationResultWindow:
    """翻訳品質評価結果ウィンドウのテストクラス"""
    
    def test_window_creation(self, result_window):
        """ウィンドウの作成テスト"""
        # ウィンドウが正しく作成されていることを確認
        assert result_window.windowTitle() == "翻訳品質評価結果"
        
        # 翻訳元テキストと翻訳テキストが表示されていることを確認
        assert result_window.source_text.toPlainText() == "Goodbye"
        assert result_window.translation_text.toPlainText() == "さようなら"
        
        # 評価結果の要素を確認
        assert result_window.state_value.text() == str(EvaluationState.EVALUATED)
        assert result_window.score_value.text() == "85"
        assert result_window.model_value.text() == "GPT-4"
        assert "2025-03-16" in result_window.date_value.text()
        
        # 指標別スコアが表示されていることを確認
        assert result_window.metric_scores["正確性"].text() == "90"
        assert result_window.metric_scores["流暢さ"].text() == "80"
        
        # 日本語のコメントが表示されていることを確認
        assert "翻訳の品質は良好です" in result_window.comment_text.toPlainText()
        
        # 最前面表示チェックボックスが存在することを確認
        assert hasattr(result_window, "always_on_top_check")
        assert not result_window.always_on_top_check.isChecked()
    
    def test_always_on_top_toggle(self, result_window):
        """最前面表示切り替えテスト"""
        # 初期状態では最前面表示がオフであることを確認
        assert not result_window.always_on_top_check.isChecked()
        
        # _toggle_always_on_topメソッドをモック化
        original_toggle = result_window._toggle_always_on_top
        result_window._toggle_always_on_top = MagicMock()
        
        # showメソッドをモック化（実際のウィンドウ表示を避けるため）
        original_show = result_window.show
        result_window.show = MagicMock()
        
        try:
            # 最前面表示をオンにする
            result_window.always_on_top_check.setChecked(True)
            
            # _toggle_always_on_topメソッドが呼び出されたことを確認
            result_window._toggle_always_on_top.assert_called_once()
            assert result_window._toggle_always_on_top.call_args[0][0] == 2  # Qt.CheckState.Checked の値は2
            result_window._toggle_always_on_top.reset_mock()
            
            # 最前面表示をオフにする
            result_window.always_on_top_check.setChecked(False)
            
            # _toggle_always_on_topメソッドが再度呼び出されたことを確認
            result_window._toggle_always_on_top.assert_called_once()
            assert result_window._toggle_always_on_top.call_args[0][0] == 0  # Qt.CheckState.Unchecked の値は0
        finally:
            # 元のメソッドを復元
            result_window._toggle_always_on_top = original_toggle
            result_window.show = original_show
    
    def test_comment_language_switch(self, result_window):
        """コメント言語切り替えテスト"""
        # 初期状態では日本語のコメントが表示されていることを確認
        assert "翻訳の品質は良好です" in result_window.comment_text.toPlainText()
        
        # コメント言語を英語に切り替え
        result_window.comment_language_combo.setCurrentText("英語")
        
        # 英語のコメントが表示されていることを確認
        assert "The translation quality is good" in result_window.comment_text.toPlainText()
        
    def test_metadata_display(self, app, qtbot, sample_entries):
        """メタデータからの表示テスト"""
        # エントリのスコアとメタデータのスコアを異なる値に設定
        entry = sample_entries[1].copy()
        entry.score = 75  # エントリ自体のスコアは75
        entry.add_metadata(METADATA_EVALUATION_SCORE, 90)  # メタデータのスコアは90
        
        # 結果ウィンドウを作成
        window = TranslationEvaluationResultWindow(entry)
        qtbot.addWidget(window)
        
        # メタデータの値が優先されて表示されることを確認
        assert window.score_value.text() == "90"
        
    def test_set_entry(self, app, qtbot, sample_entries):
        """エントリ設定テスト"""
        # 結果ウィンドウを作成（初期エントリなし）
        window = TranslationEvaluationResultWindow()
        qtbot.addWidget(window)
        
        # 初期状態では表示がクリアされていることを確認
        assert window.source_text.toPlainText() == ""
        assert window.translation_text.toPlainText() == ""
        assert window.state_value.text() == "未評価"
        assert window.score_value.text() == "--"
        
        # エントリを設定
        window.set_entry(sample_entries[1])
        
        # 表示が更新されることを確認
        assert window.source_text.toPlainText() == "Goodbye"
        assert window.translation_text.toPlainText() == "さようなら"
        assert window.state_value.text() == str(EvaluationState.EVALUATED)
        assert window.score_value.text() == "85"
        
        # エントリをNoneに設定
        window.set_entry(None)
        
        # 表示がクリアされることを確認
        assert window.source_text.toPlainText() == ""
        assert window.translation_text.toPlainText() == ""
        assert window.state_value.text() == "未評価"
        assert window.score_value.text() == "--" 