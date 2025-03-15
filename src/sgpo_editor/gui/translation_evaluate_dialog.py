"""翻訳品質評価ダイアログ

このモジュールは、LLMを利用した翻訳品質評価機能のUIを提供します。
"""

import logging
import json
from typing import Dict, List, Optional, Any, Callable

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QCheckBox,
    QProgressBar,
    QWidget,
    QTextEdit,
    QSpinBox,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
)

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.models.evaluation_state import EvaluationState
from sgpo_editor.models.database import Database

logger = logging.getLogger(__name__)

# メタデータキー定数
METADATA_EVALUATION_PREFIX = "translation_evaluation"
METADATA_EVALUATION_SCORE = f"{METADATA_EVALUATION_PREFIX}_score"
METADATA_EVALUATION_STATE = f"{METADATA_EVALUATION_PREFIX}_state"
METADATA_EVALUATION_METRICS = f"{METADATA_EVALUATION_PREFIX}_metrics"
METADATA_EVALUATION_COMMENTS = f"{METADATA_EVALUATION_PREFIX}_comments"
METADATA_EVALUATION_MODEL = f"{METADATA_EVALUATION_PREFIX}_model"
METADATA_EVALUATION_DATE = f"{METADATA_EVALUATION_PREFIX}_date"


class TranslationEvaluateDialog(QDialog):
    """翻訳品質評価ダイアログ

    LLMを利用して翻訳品質を評価するためのダイアログです。
    """

    # 評価完了時に発行されるシグナル
    evaluation_completed = Signal(str, int)  # エントリキー, スコア

    def __init__(self, parent=None):
        """初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle("翻訳品質評価")
        self.resize(600, 500)

        # データ
        self._entries: List[EntryModel] = []
        self._current_entry: Optional[EntryModel] = None
        self._database: Optional[Database] = None
        self._evaluation_in_progress = False

        # UI初期化
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout(self)

        # 評価設定
        self._setup_settings_ui(main_layout)

        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # ボタンレイアウト
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        # 実行ボタン
        self.run_button = QPushButton("評価実行")
        self.run_button.clicked.connect(self._run_evaluation)
        button_layout.addWidget(self.run_button)

        # キャンセルボタン
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

    def _setup_settings_ui(self, parent_layout: QVBoxLayout) -> None:
        """評価設定UIの初期化

        Args:
            parent_layout: 親レイアウト
        """
        # 評価対象の選択
        target_group = QGroupBox("評価対象")
        target_layout = QVBoxLayout(target_group)
        parent_layout.addWidget(target_group)

        # 評価対象ラジオボタン
        self.target_current_radio = QRadioButton("現在選択中のエントリのみ")
        self.target_all_radio = QRadioButton("すべてのエントリ")
        self.target_untranslated_radio = QRadioButton("未評価のエントリのみ")
        self.target_current_radio.setChecked(True)

        target_layout.addWidget(self.target_current_radio)
        target_layout.addWidget(self.target_all_radio)
        target_layout.addWidget(self.target_untranslated_radio)

        # ボタングループの作成
        self.target_button_group = QButtonGroup(self)
        self.target_button_group.addButton(self.target_current_radio, 0)
        self.target_button_group.addButton(self.target_all_radio, 1)
        self.target_button_group.addButton(self.target_untranslated_radio, 2)

        # 評価モデルの選択
        model_group = QGroupBox("評価モデル")
        model_layout = QVBoxLayout(model_group)
        parent_layout.addWidget(model_group)

        model_label = QLabel("使用するLLMモデル:")
        self.model_combo = QComboBox()
        self.model_combo.addItems(["GPT-4", "GPT-3.5", "Claude", "Gemini"])
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)

        # 評価指標の選択
        metrics_group = QGroupBox("評価指標")
        metrics_layout = QVBoxLayout(metrics_group)
        parent_layout.addWidget(metrics_group)

        # 評価指標チェックボックス
        self.accuracy_check = QCheckBox("正確性 (Accuracy)")
        self.fluency_check = QCheckBox("流暢さ (Fluency)")
        self.consistency_check = QCheckBox("一貫性 (Consistency)")
        self.style_check = QCheckBox("スタイル (Style)")
        self.terminology_check = QCheckBox("用語 (Terminology)")

        # デフォルトで全てチェック
        self.accuracy_check.setChecked(True)
        self.fluency_check.setChecked(True)
        self.consistency_check.setChecked(True)
        self.style_check.setChecked(True)
        self.terminology_check.setChecked(True)

        metrics_layout.addWidget(self.accuracy_check)
        metrics_layout.addWidget(self.fluency_check)
        metrics_layout.addWidget(self.consistency_check)
        metrics_layout.addWidget(self.style_check)
        metrics_layout.addWidget(self.terminology_check)

        # 評価言語の選択
        language_group = QGroupBox("評価言語")
        language_layout = QVBoxLayout(language_group)
        parent_layout.addWidget(language_group)

        language_label = QLabel("評価結果の言語:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["日本語", "英語"])
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)

    def set_entries(self, entries: List[EntryModel]) -> None:
        """評価対象のエントリを設定

        Args:
            entries: 評価対象のエントリリスト
        """
        self._entries = entries
        logger.debug(f"Set {len(entries)} entries for evaluation")

    def set_current_entry(self, entry: EntryModel) -> None:
        """現在選択中のエントリを設定

        Args:
            entry: 現在選択中のエントリ
        """
        self._current_entry = entry
        logger.debug(f"Set current entry: {entry.key}")

    def set_database(self, database: Database) -> None:
        """データベースを設定

        Args:
            database: データベース
        """
        self._database = database
        logger.debug("Database set for translation evaluation dialog")

    def _run_evaluation(self) -> None:
        """評価を実行"""
        if self._evaluation_in_progress:
            QMessageBox.warning(self, "警告", "評価が既に実行中です")
            return

        # 評価対象の決定
        target_entries = []
        target_mode = self.target_button_group.checkedId()
        
        if target_mode == 0:  # 現在選択中のエントリのみ
            if self._current_entry:
                target_entries = [self._current_entry]
            else:
                QMessageBox.warning(self, "警告", "現在選択中のエントリがありません")
                return
        elif target_mode == 1:  # すべてのエントリ
            target_entries = self._entries
        elif target_mode == 2:  # 未評価のエントリのみ
            target_entries = [e for e in self._entries if e.evaluation_state == EvaluationState.NOT_EVALUATED]
        
        if not target_entries:
            QMessageBox.information(self, "情報", "評価対象のエントリがありません")
            return
            
        # 評価指標の取得
        metrics = []
        if self.accuracy_check.isChecked():
            metrics.append("accuracy")
        if self.fluency_check.isChecked():
            metrics.append("fluency")
        if self.consistency_check.isChecked():
            metrics.append("consistency")
        if self.style_check.isChecked():
            metrics.append("style")
        if self.terminology_check.isChecked():
            metrics.append("terminology")
            
        if not metrics:
            QMessageBox.warning(self, "警告", "少なくとも1つの評価指標を選択してください")
            return
            
        # 評価モデルの取得
        model = self.model_combo.currentText()
        
        # 評価言語の取得
        language = self.language_combo.currentText()
        
        # 評価の実行（ここではモック実装）
        self._evaluation_in_progress = True
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(target_entries))
        self.progress_bar.setValue(0)
        
        # TODO: 実際のLLM評価処理を実装
        # 現在はモック実装のみ
        QMessageBox.information(
            self, 
            "情報", 
            f"評価を開始します:\n"
            f"- 対象: {len(target_entries)}件のエントリ\n"
            f"- モデル: {model}\n"
            f"- 指標: {', '.join(metrics)}\n"
            f"- 言語: {language}"
        )
        
        # モック評価の実行
        import random
        from datetime import datetime
        
        for i, entry in enumerate(target_entries):
            # 評価状態を更新
            entry.evaluation_state = EvaluationState.EVALUATED
            
            # 総合スコアを設定
            overall_score = random.randint(70, 100)
            entry.score = overall_score
            
            # 指標別スコアを設定
            metric_scores = {}
            for metric in metrics:
                score = random.randint(60, 100)
                entry.set_metric_score(metric, score)
                metric_scores[metric] = score
            
            # レビューコメントを追加（languageパラメータなし）
            if language == "日本語":
                comment = f"翻訳の品質は{overall_score}点です。改善の余地があります。"
                entry.add_review_comment("AI評価者", comment)
            else:
                comment = f"The translation quality is {overall_score} points. There is room for improvement."
                entry.add_review_comment("AI Evaluator", comment)
                
            # メタデータとして評価結果を保存
            self._save_evaluation_to_metadata(entry, overall_score, metric_scores, model, language)
            
            # 進捗バーを更新
            self.progress_bar.setValue(i + 1)
            
            # 評価完了シグナルを発行
            self.evaluation_completed.emit(entry.key, overall_score)
        
        # 評価完了後の処理
        self._evaluation_in_progress = False
        self.progress_bar.setVisible(False)
        
        # 評価が完了したら、評価結果表示ダイアログを表示
        if target_entries:
            self._show_evaluation_result(target_entries[0])
        
        # ダイアログを閉じる
        self.accept()
        
    def _save_evaluation_to_metadata(self, entry: EntryModel, score: int, 
                                    metric_scores: Dict[str, int], model: str, 
                                    language: str) -> None:
        """評価結果をメタデータとして保存
        
        Args:
            entry: 評価対象のエントリ
            score: 総合スコア
            metric_scores: 指標別スコア
            model: 使用したモデル
            language: 評価言語
        """
        from datetime import datetime
        
        # 評価状態をメタデータに保存
        entry.add_metadata(METADATA_EVALUATION_STATE, str(entry.evaluation_state))
        
        # 総合スコアをメタデータに保存
        entry.add_metadata(METADATA_EVALUATION_SCORE, score)
        
        # 指標別スコアをメタデータに保存
        entry.add_metadata(METADATA_EVALUATION_METRICS, metric_scores)
        
        # 使用したモデルをメタデータに保存
        entry.add_metadata(METADATA_EVALUATION_MODEL, model)
        
        # 評価日時をメタデータに保存
        entry.add_metadata(METADATA_EVALUATION_DATE, datetime.now().isoformat())
        
        # レビューコメントをメタデータに保存（言語情報を含む）
        comments = []
        for comment in entry.review_comments:
            # コメントオブジェクトをコピー
            comment_with_lang = comment.copy()
            
            # 言語情報を追加
            if "AI評価者" in comment.get("author", ""):
                comment_with_lang["language"] = "ja"
            elif "AI Evaluator" in comment.get("author", ""):
                comment_with_lang["language"] = "en"
            else:
                # デフォルトは評価言語
                comment_with_lang["language"] = "ja" if language == "日本語" else "en"
                
            comments.append(comment_with_lang)
        
        entry.add_metadata(METADATA_EVALUATION_COMMENTS, comments)
        
    def _show_evaluation_result(self, entry: EntryModel) -> None:
        """評価結果表示ウィンドウを表示

        Args:
            entry: 評価結果を表示するエントリ
        """
        # メインウィンドウを取得
        main_window = self.parent()
        while main_window and not isinstance(main_window, QMainWindow):
            main_window = main_window.parent()
            
        # 既存のウィンドウがあれば、そのウィンドウを表示
        result_window = getattr(main_window, "_evaluation_result_window", None)
        if result_window:
            result_window.set_entry(entry)
            result_window.show()
            result_window.raise_()
            result_window.activateWindow()
        else:
            # 新しいウィンドウを作成
            result_window = TranslationEvaluationResultWindow(entry, main_window)
            if main_window:
                main_window._evaluation_result_window = result_window
            result_window.show()


class TranslationEvaluationResultWindow(QMainWindow):
    """翻訳品質評価結果ウィンドウ

    LLMによる翻訳品質評価の結果を表示するフローティングウィンドウです。
    """

    def __init__(self, entry: Optional[EntryModel] = None, parent=None):
        """初期化

        Args:
            entry: 評価結果を表示するエントリ（省略可能）
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.setWindowTitle("翻訳品質評価結果")
        self.resize(700, 600)
        
        self._entry = entry
        
        # 中央ウィジェットの作成
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # UI初期化
        self._setup_ui()
        
        # 評価結果の表示
        self._update_ui()
        
    def _setup_ui(self) -> None:
        """UIの初期化"""
        # メインレイアウト
        main_layout = QVBoxLayout(self.central_widget)
        
        # 最前面表示チェックボックス
        top_layout = QHBoxLayout()
        self.always_on_top_check = QCheckBox("常に最前面に表示")
        self.always_on_top_check.setToolTip("チェックすると、このウィンドウが常に他のウィンドウの前面に表示されます")
        self.always_on_top_check.stateChanged.connect(self._toggle_always_on_top)
        top_layout.addWidget(self.always_on_top_check)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)
        
        # 評価結果の概要
        summary_group = QGroupBox("評価概要")
        summary_layout = QVBoxLayout(summary_group)
        main_layout.addWidget(summary_group)

        # 翻訳元テキスト
        source_layout = QVBoxLayout()
        source_label = QLabel("翻訳元テキスト:")
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source_text)
        summary_layout.addLayout(source_layout)
        
        # 翻訳テキスト
        translation_layout = QVBoxLayout()
        translation_label = QLabel("翻訳テキスト:")
        self.translation_text = QTextEdit()
        self.translation_text.setReadOnly(True)
        translation_layout.addWidget(translation_label)
        translation_layout.addWidget(self.translation_text)
        summary_layout.addLayout(translation_layout)

        # 総合スコア
        score_layout = QHBoxLayout()
        score_label = QLabel("総合スコア:")
        self.score_value = QLabel("--")
        score_layout.addWidget(score_label)
        score_layout.addWidget(self.score_value)
        score_layout.addStretch()
        summary_layout.addLayout(score_layout)

        # 評価状態
        state_layout = QHBoxLayout()
        state_label = QLabel("評価状態:")
        self.state_value = QLabel("未評価")
        state_layout.addWidget(state_label)
        state_layout.addWidget(self.state_value)
        state_layout.addStretch()
        summary_layout.addLayout(state_layout)
        
        # 評価モデル
        model_layout = QHBoxLayout()
        model_label = QLabel("評価モデル:")
        self.model_value = QLabel("--")
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_value)
        model_layout.addStretch()
        summary_layout.addLayout(model_layout)
        
        # 評価日時
        date_layout = QHBoxLayout()
        date_label = QLabel("評価日時:")
        self.date_value = QLabel("--")
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_value)
        date_layout.addStretch()
        summary_layout.addLayout(date_layout)

        # 指標別スコア
        metrics_group = QGroupBox("指標別スコア")
        metrics_layout = QVBoxLayout(metrics_group)
        main_layout.addWidget(metrics_group)

        # 各指標のスコア表示
        self.metric_scores = {}
        for metric in ["正確性", "流暢さ", "一貫性", "スタイル", "用語"]:
            metric_layout = QHBoxLayout()
            metric_label = QLabel(f"{metric}:")
            metric_value = QLabel("--")
            metric_layout.addWidget(metric_label)
            metric_layout.addWidget(metric_value)
            metric_layout.addStretch()
            metrics_layout.addLayout(metric_layout)
            self.metric_scores[metric] = metric_value

        # レビューコメント
        comments_group = QGroupBox("レビューコメント")
        comments_layout = QVBoxLayout(comments_group)
        main_layout.addWidget(comments_group)

        # コメント言語選択
        language_layout = QHBoxLayout()
        language_label = QLabel("コメント言語:")
        self.comment_language_combo = QComboBox()
        self.comment_language_combo.addItems(["日本語", "英語"])
        self.comment_language_combo.currentIndexChanged.connect(self._update_comment_display)
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.comment_language_combo)
        language_layout.addStretch()
        comments_layout.addLayout(language_layout)

        # コメント表示エリア
        self.comment_text = QTextEdit()
        self.comment_text.setReadOnly(True)
        comments_layout.addWidget(self.comment_text)
        
    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定

        Args:
            entry: 評価結果を表示するエントリ
        """
        try:
            if entry:
                logger.debug(f"TranslationEvaluationResultWindow.set_entry: エントリを設定 msgid='{entry.msgid[:30]}...'")
                # エントリのキーとメタデータを確認
                entry_key = getattr(entry, "key", None)
                metadata = entry.get_all_metadata() if hasattr(entry, "get_all_metadata") else {}
                logger.debug(f"TranslationEvaluationResultWindow.set_entry: エントリキー={entry_key}, メタデータキー数={len(metadata)}")
                
                # 評価関連のメタデータを確認
                score = metadata.get(METADATA_EVALUATION_SCORE, getattr(entry, "score", None))
                state = metadata.get(METADATA_EVALUATION_STATE, getattr(entry, "evaluation_state", None))
                logger.debug(f"TranslationEvaluationResultWindow.set_entry: スコア={score}, 状態={state}")
            else:
                logger.debug("TranslationEvaluationResultWindow.set_entry: Noneエントリを設定")
                
            self._entry = entry
            self._update_ui()
        except Exception as e:
            logger.error(f"TranslationEvaluationResultWindow.set_entry: エラー発生 {e}", exc_info=True)
        
    def _update_ui(self) -> None:
        """UI表示を更新"""
        logger.debug("TranslationEvaluationResultWindow._update_ui: 開始")
        
        try:
            if not self._entry:
                logger.debug("TranslationEvaluationResultWindow._update_ui: エントリがないため表示をクリア")
                # エントリがない場合は表示をクリア
                self.source_text.setText("")
                self.translation_text.setText("")
                self.state_value.setText("未評価")
                self.score_value.setText("--")
                self.model_value.setText("--")
                self.date_value.setText("--")
                
                for metric_value in self.metric_scores.values():
                    metric_value.setText("--")
                    
                self.comment_text.setText("エントリが選択されていません")
                logger.debug("TranslationEvaluationResultWindow._update_ui: 表示クリア完了")
                return

            logger.debug(f"TranslationEvaluationResultWindow._update_ui: エントリ情報を表示 msgid='{self._entry.msgid[:30]}...'")
            
            # 翻訳元テキストと翻訳テキストの設定
            self.source_text.setText(self._entry.msgid)
            self.translation_text.setText(self._entry.msgstr)
            logger.debug("TranslationEvaluationResultWindow._update_ui: 翻訳テキスト設定完了")

            # メタデータから評価情報を取得
            metadata = self._entry.get_all_metadata()
            logger.debug(f"TranslationEvaluationResultWindow._update_ui: メタデータキー数={len(metadata)}")
            
            # 評価状態の更新
            evaluation_state = metadata.get(METADATA_EVALUATION_STATE, str(self._entry.evaluation_state))
            self.state_value.setText(evaluation_state)
            logger.debug(f"TranslationEvaluationResultWindow._update_ui: 評価状態={evaluation_state}")

            # スコアの更新
            score = metadata.get(METADATA_EVALUATION_SCORE, self._entry.score)
            score_text = str(score) if score is not None else "--"
            self.score_value.setText(score_text)
            logger.debug(f"TranslationEvaluationResultWindow._update_ui: スコア={score_text}")
            
            # 評価モデルの更新
            model = metadata.get(METADATA_EVALUATION_MODEL, "--")
            self.model_value.setText(model)
            logger.debug(f"TranslationEvaluationResultWindow._update_ui: 評価モデル={model}")
            
            # 評価日時の更新
            date = metadata.get(METADATA_EVALUATION_DATE, "--")
            if date != "--":
                from datetime import datetime
                try:
                    date_obj = datetime.fromisoformat(date)
                    date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    logger.error(f"TranslationEvaluationResultWindow._update_ui: 日時変換エラー {e}")
            self.date_value.setText(date)
            logger.debug(f"TranslationEvaluationResultWindow._update_ui: 評価日時={date}")

            # 指標別スコアの更新
            metric_mapping = {
                "accuracy": "正確性",
                "fluency": "流暢さ",
                "consistency": "一貫性",
                "style": "スタイル",
                "terminology": "用語"
            }
            
            # メタデータから指標別スコアを取得
            metric_scores = metadata.get(METADATA_EVALUATION_METRICS, {})
            if not metric_scores:
                # メタデータになければエントリから直接取得
                metric_scores = self._entry.metric_scores
                logger.debug("TranslationEvaluationResultWindow._update_ui: メタデータにスコアがないためエントリから直接取得")
                
            logger.debug(f"TranslationEvaluationResultWindow._update_ui: 指標別スコア数={len(metric_scores)}")
                
            for key, display_name in metric_mapping.items():
                if display_name in self.metric_scores:
                    value = metric_scores.get(key)
                    value_text = str(value) if value is not None else "--"
                    self.metric_scores[display_name].setText(value_text)
                    logger.debug(f"TranslationEvaluationResultWindow._update_ui: 指標 {display_name}={value_text}")

            # コメント表示の更新
            logger.debug("TranslationEvaluationResultWindow._update_ui: コメント表示更新開始")
            self._update_comment_display()
            logger.debug("TranslationEvaluationResultWindow._update_ui: UI更新完了")
        except Exception as e:
            logger.error(f"TranslationEvaluationResultWindow._update_ui: エラー発生 {e}", exc_info=True)

    def _update_comment_display(self) -> None:
        """コメント表示を更新"""
        logger.debug("TranslationEvaluationResultWindow._update_comment_display: 開始")
        
        if not self._entry:
            logger.debug("TranslationEvaluationResultWindow._update_comment_display: エントリがないためコメント表示をクリア")
            self.comment_text.setText("エントリが選択されていません")
            return

        # 選択された言語に基づいてコメントを表示
        language = self.comment_language_combo.currentText()
        logger.debug(f"TranslationEvaluationResultWindow._update_comment_display: 選択言語={language}")
        
        # メタデータからコメントを取得
        metadata = self._entry.get_all_metadata()
        comments = metadata.get(METADATA_EVALUATION_COMMENTS, [])
        
        # メタデータになければエントリから直接取得
        if not comments:
            logger.debug("TranslationEvaluationResultWindow._update_comment_display: メタデータにコメントがないためエントリから直接取得")
            comments = self._entry.review_comments
        
        logger.debug(f"TranslationEvaluationResultWindow._update_comment_display: 取得したコメント数={len(comments)}")
        
        comment = None
        if language == "日本語":
            # 日本語のコメントを探す
            comment = next((c["comment"] for c in comments if "ja" in c.get("language", "").lower() 
                          or "japanese" in c.get("language", "").lower()), None)
            if comment:
                logger.debug("TranslationEvaluationResultWindow._update_comment_display: 日本語コメントを見つけました")
        else:
            # 英語のコメントを探す
            comment = next((c["comment"] for c in comments if "en" in c.get("language", "").lower() 
                          or "english" in c.get("language", "").lower()), None)
            if comment:
                logger.debug("TranslationEvaluationResultWindow._update_comment_display: 英語コメントを見つけました")
        
        # コメントが見つからない場合は最初のコメントを表示
        if comment is None and comments:
            logger.debug("TranslationEvaluationResultWindow._update_comment_display: 言語に一致するコメントがないため最初のコメントを使用")
            comment = comments[0].get("comment", "")
            
        self.comment_text.setText(comment if comment else "コメントはありません")
        logger.debug("TranslationEvaluationResultWindow._update_comment_display: コメント表示更新完了")
        
    def closeEvent(self, event):
        """ウィンドウが閉じられるときのイベント処理"""
        logger.debug("TranslationEvaluationResultWindow.closeEvent: ウィンドウが閉じられます")
        
        # 親ウィンドウの参照を削除
        parent = self.parent()
        if parent and hasattr(parent, "_evaluation_result_window"):
            logger.debug("TranslationEvaluationResultWindow.closeEvent: 親ウィンドウの参照を削除")
            parent._evaluation_result_window = None
        
        logger.debug("TranslationEvaluationResultWindow.closeEvent: イベント受理")
        event.accept()

    def _toggle_always_on_top(self, state: int) -> None:
        """最前面表示の切り替え
        
        Args:
            state: チェックボックスの状態
        """
        # 現在のウィンドウの位置とサイズを保存
        geometry = self.geometry()
        
        # 現在のウィンドウフラグを取得
        current_flags = self.windowFlags()
        
        # 最前面表示フラグの状態を確認
        is_on_top = bool(current_flags & Qt.WindowType.WindowStaysOnTopHint)
        
        # チェックボックスの状態を確認
        is_checked = (state == Qt.CheckState.Checked)
        
        # 状態が変わる場合のみ処理
        if is_checked != is_on_top:
            if is_checked:
                # 最前面に表示
                new_flags = current_flags | Qt.WindowType.WindowStaysOnTopHint
                logger.debug("翻訳評価結果ウィンドウを最前面に表示に設定")
            else:
                # 通常表示
                new_flags = current_flags & ~Qt.WindowType.WindowStaysOnTopHint
                logger.debug("翻訳評価結果ウィンドウを通常表示に設定")
            
            # ウィンドウが表示されている場合のみ処理
            if self.isVisible():
                # ウィンドウフラグを変更
                self.setWindowFlags(new_flags)
                # 元の位置とサイズに戻す
                self.setGeometry(geometry)
                # ウィンドウを再表示
                self.show()
                # ウィンドウをアクティブにする
                self.activateWindow()
                
                # 設定後の状態を確認してログ出力
                after_flags = self.windowFlags()
                is_on_top_after = bool(after_flags & Qt.WindowType.WindowStaysOnTopHint)
                logger.debug(f"翻訳評価結果ウィンドウの最前面表示状態: {is_on_top_after}")
            else:
                # 非表示の場合はフラグのみ設定
                self.setWindowFlags(new_flags)
                logger.debug(f"翻訳評価結果ウィンドウのフラグを設定（非表示状態）: 最前面={is_checked}")


# 後方互換性のために残す
TranslationEvaluationResultDialog = TranslationEvaluationResultWindow 