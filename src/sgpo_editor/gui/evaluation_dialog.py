"""翻訳評価ダイアログ

このモジュールは、LLMを使用した翻訳評価を行うためのダイアログを提供します。
"""

import json
import logging
import time
import os
from typing import Tuple

from PySide6.QtCore import Signal, QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.models.evaluation_db import EvaluationDatabase
from sgpo_editor.models.evaluation_state import EvaluationState
from sgpo_editor.utils.llm_utils import (
    DEFAULT_METRICS,
    EvaluationMetric,
    EvaluationResult,
    LLMEvaluator,
    LLMProvider,
)

logger = logging.getLogger(__name__)


class APIKeyDialog(QDialog):
    """APIキー入力ダイアログ"""

    def __init__(self, parent=None):
        """初期化"""
        super().__init__(parent)
        self.setWindowTitle("APIキーの設定")
        self.resize(400, 150)

        # レイアウト
        layout = QVBoxLayout(self)

        # APIキー入力フォーム
        form_layout = QFormLayout()
        self.openai_api_key = QLineEdit()
        self.openai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.claude_api_key = QLineEdit()
        self.claude_api_key.setEchoMode(QLineEdit.EchoMode.Password)

        form_layout.addRow("OpenAI APIキー:", self.openai_api_key)
        form_layout.addRow("Claude APIキー:", self.claude_api_key)
        layout.addLayout(form_layout)

        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_api_keys(self) -> Tuple[str, str]:
        """APIキーを取得

        Returns:
            Tuple[str, str]: OpenAI APIキーとClaude APIキー
        """
        return self.openai_api_key.text(), self.claude_api_key.text()


class EvaluationWorker(QThread):
    """評価処理を行うワーカースレッド"""

    # 進捗シグナル
    progress_updated = Signal(int)

    # 結果シグナル
    evaluation_finished = Signal(object)
    evaluation_error = Signal(str)

    def __init__(self, evaluator, entry, metrics, language, db=None):
        """初期化

        Args:
            evaluator: LLMEvaluator
            entry: 評価対象のエントリ
            metrics: 評価指標
            language: 評価言語
            db: 評価データベース
        """
        super().__init__()
        self.evaluator = evaluator
        self.entry = entry
        self.metrics = metrics
        self.language = language
        self.db = db
        # タイムアウト設定（秒）
        self.timeout = 180

    def run(self):
        """評価処理を実行"""
        logger.debug(
            f"評価処理開始: エントリキー={self.entry.key}, 言語={self.language}"
        )
        try:
            # 評価状態を更新
            self.entry.evaluation_state = EvaluationState.EVALUATING
            if self.db:
                try:
                    self.db.save_evaluation_state(
                        self.entry, EvaluationState.EVALUATING
                    )
                    logger.debug("評価状態をEVALUATINGに更新しました")
                except Exception as e:
                    logger.error(f"評価状態の更新に失敗しました: {e}", exc_info=True)

            # 進捗通知
            self.progress_updated.emit(10)
            logger.debug("進捗: 10% - 評価準備完了")

            # 評価パラメータを表示
            metrics_names = [m.name for m in self.metrics]
            logger.debug(
                f"評価パラメータ: 指標数={len(self.metrics)}, 指標={metrics_names}"
            )

            # タイムアウト設定
            is_timedout = False
            start_time = time.time()

            # 進捗通知 - API接続開始
            self.progress_updated.emit(20)
            logger.debug("進捗: 20% - LLM APIに接続")

            # 評価実行
            try:
                result = self.evaluator.evaluate_translation(
                    source_text=self.entry.msgid,
                    translated_text=self.entry.msgstr,
                    metrics=self.metrics,
                    language=self.language,
                    context=self.entry.msgctxt,
                )

                # タイムアウトチェック
                elapsed_time = time.time() - start_time
                if elapsed_time > self.timeout:
                    is_timedout = True
                    raise TimeoutError(
                        f"評価がタイムアウトしました (経過時間: {elapsed_time:.1f}秒)"
                    )

                logger.debug("LLMからの評価結果を受信しました")

            except Exception as api_error:
                logger.error(
                    f"LLM API呼び出し中にエラー発生: {api_error}", exc_info=True
                )

                # API特有のエラーメッセージをフォーマット
                if (
                    "rate limits" in str(api_error).lower()
                    or "rate_limit" in str(api_error).lower()
                ):
                    error_msg = f"APIレート制限に達しました。しばらく待ってから再試行してください。\n詳細: {api_error}"
                elif (
                    "auth" in str(api_error).lower()
                    or "key" in str(api_error).lower()
                    or "token" in str(api_error).lower()
                ):
                    error_msg = f"APIキー認証エラーが発生しました。APIキー設定を確認してください。\n詳細: {api_error}"
                elif is_timedout or "timeout" in str(api_error).lower():
                    error_msg = f"API呼び出しがタイムアウトしました。ネットワーク接続を確認してください。\n詳細: {api_error}"
                else:
                    error_msg = f"LLM APIエラー: {api_error}"

                # エラーを通知
                self.evaluation_error.emit(error_msg)

                # 評価状態をエラーに更新
                self.entry.evaluation_state = EvaluationState.ERROR
                if self.db:
                    try:
                        self.db.save_evaluation_state(self.entry, EvaluationState.ERROR)
                    except Exception as e:
                        logger.error(
                            f"評価状態の更新に失敗しました: {e}", exc_info=True
                        )

                return

            # 進捗通知
            self.progress_updated.emit(80)
            logger.debug("進捗: 80% - 評価結果の処理")

            # 評価結果のログ
            log_message = f"評価結果: 総合評価={result.overall_score:.1f}, "
            log_message += ", ".join(
                [f"{score.name}={score.score:.1f}" for score in result.scores]
            )
            logger.debug(log_message)

            # 進捗通知
            self.progress_updated.emit(90)
            logger.debug("進捗: 90% - 評価結果の保存")

            # 評価状態を更新
            self.entry.evaluation_state = EvaluationState.EVALUATED
            if self.db:
                try:
                    self.db.save_evaluation_state(self.entry, EvaluationState.EVALUATED)
                    self.db.save_evaluation_result(self.entry.key, result)
                    logger.debug("評価結果をデータベースに保存しました")
                except Exception as e:
                    logger.error(f"評価結果の保存に失敗しました: {e}", exc_info=True)

            # 完了通知
            self.progress_updated.emit(100)
            logger.debug("進捗: 100% - 評価完了")

            # 結果を通知
            self.evaluation_finished.emit(result)

        except Exception as e:
            # 一般的なエラーの処理
            logger.error(f"評価処理中にエラーが発生しました: {e}", exc_info=True)
            error_msg = f"評価処理エラー: {str(e)}\n\n詳細なエラーログはアプリケーションログを確認してください。"

            # エラーを通知
            self.evaluation_error.emit(error_msg)

            # 評価状態をエラーに更新
            self.entry.evaluation_state = EvaluationState.ERROR
            if self.db:
                try:
                    self.db.save_evaluation_state(self.entry, EvaluationState.ERROR)
                except Exception as save_error:
                    logger.error(
                        f"評価状態の更新に失敗しました: {save_error}", exc_info=True
                    )


class EvaluationDialog(QDialog):
    """翻訳評価ダイアログ"""

    # 評価完了シグナル
    evaluation_completed = Signal(EntryModel, EvaluationResult)

    def __init__(self, entry: EntryModel, db: EvaluationDatabase, parent=None):
        """初期化

        Args:
            entry: 評価対象のエントリ
            db: 評価データベース
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.entry = entry
        self.db = db
        self.evaluator = None
        self.api_keys = {"openai": "", "claude": ""}
        self.metrics = DEFAULT_METRICS.copy()

        # 設定から保存されたAPIキーを読み込む
        self._load_api_keys()

        self.setWindowTitle("翻訳評価")
        self.resize(800, 600)

        self._setup_ui()

    def _setup_ui(self):
        """UIをセットアップ"""
        layout = QVBoxLayout(self)

        # タブウィジェット
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_evaluation_tab(), "評価")
        self.tab_widget.addTab(self._create_settings_tab(), "設定")
        self.tab_widget.addTab(self._create_history_tab(), "履歴")
        layout.addWidget(self.tab_widget)

        # 状態表示ラベル
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # ボタン
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_evaluation_tab(self) -> QWidget:
        """評価タブを作成

        Returns:
            QWidget: 評価タブウィジェット
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # エントリ情報
        entry_group = QGroupBox("エントリ情報")
        entry_layout = QFormLayout(entry_group)
        entry_layout.addRow("原文:", QLabel(self.entry.msgid))
        entry_layout.addRow("翻訳:", QLabel(self.entry.msgstr))
        if self.entry.msgctxt:
            entry_layout.addRow("コンテキスト:", QLabel(self.entry.msgctxt))
        layout.addWidget(entry_group)

        # 評価設定
        eval_group = QGroupBox("評価設定")
        eval_layout = QVBoxLayout(eval_group)

        # LLMプロバイダー選択
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("LLMプロバイダー:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("OpenAI", LLMProvider.OPENAI)
        self.provider_combo.addItem("Claude", LLMProvider.ANTHROPIC)
        provider_layout.addWidget(self.provider_combo)
        eval_layout.addLayout(provider_layout)

        # モデル選択
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("モデル:"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("GPT-4o", "gpt-4o")
        self.model_combo.addItem("GPT-4", "gpt-4")
        self.model_combo.addItem("GPT-3.5 Turbo", "gpt-3.5-turbo")
        self.model_combo.addItem("Claude 3 Opus", "claude-3-opus-20240229")
        self.model_combo.addItem("Claude 3 Sonnet", "claude-3-sonnet-20240229")
        self.model_combo.addItem("Claude 3 Haiku", "claude-3-haiku-20240307")
        model_layout.addWidget(self.model_combo)
        eval_layout.addLayout(model_layout)

        # 評価言語
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("評価言語:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("日本語", "日本語")
        self.lang_combo.addItem("英語", "英語")
        lang_layout.addWidget(self.lang_combo)
        eval_layout.addLayout(lang_layout)

        # 評価ボタン
        self.evaluate_button = QPushButton("評価実行")
        self.evaluate_button.clicked.connect(self._evaluate)
        eval_layout.addWidget(self.evaluate_button)

        # 進捗バー
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        eval_layout.addWidget(self.progress_bar)

        layout.addWidget(eval_group)

        # 評価結果
        result_group = QGroupBox("評価結果")
        result_layout = QVBoxLayout(result_group)

        # 総合スコア
        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("総合スコア:"))
        self.overall_score_label = QLabel("未評価")
        score_layout.addWidget(self.overall_score_label)
        result_layout.addLayout(score_layout)

        # 評価指標スコア
        self.metric_score_labels = {}
        for metric in self.metrics:
            metric_layout = QHBoxLayout()
            metric_layout.addWidget(QLabel(f"{metric.name}:"))
            score_label = QLabel("未評価")
            self.metric_score_labels[metric.name] = score_label
            metric_layout.addWidget(score_label)
            result_layout.addLayout(metric_layout)

        # レビューコメント
        result_layout.addWidget(QLabel("レビューコメント:"))
        self.review_comment_edit = QTextEdit()
        self.review_comment_edit.setReadOnly(True)
        result_layout.addWidget(self.review_comment_edit)

        layout.addWidget(result_group)

        return tab

    def _create_settings_tab(self) -> QWidget:
        """設定タブを作成

        Returns:
            QWidget: 設定タブウィジェット
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # APIキー設定
        api_group = QGroupBox("APIキー設定")
        api_layout = QVBoxLayout(api_group)
        self.set_api_key_button = QPushButton("APIキーを設定")
        self.set_api_key_button.clicked.connect(self._set_api_keys)
        api_layout.addWidget(self.set_api_key_button)
        layout.addWidget(api_group)

        # 評価指標設定
        metrics_group = QGroupBox("評価指標設定")
        metrics_layout = QVBoxLayout(metrics_group)

        # デフォルト指標
        for metric in self.metrics:
            checkbox = QCheckBox(f"{metric.name}: {metric.description}")
            checkbox.setChecked(True)
            metrics_layout.addWidget(checkbox)

        # カスタム指標追加
        add_metric_layout = QHBoxLayout()
        self.metric_name_edit = QLineEdit()
        self.metric_name_edit.setPlaceholderText("指標名")
        self.metric_desc_edit = QLineEdit()
        self.metric_desc_edit.setPlaceholderText("説明")
        add_metric_button = QPushButton("追加")
        add_metric_button.clicked.connect(self._add_custom_metric)
        add_metric_layout.addWidget(self.metric_name_edit)
        add_metric_layout.addWidget(self.metric_desc_edit)
        add_metric_layout.addWidget(add_metric_button)
        metrics_layout.addLayout(add_metric_layout)

        layout.addWidget(metrics_group)

        # 評価パラメータ設定
        params_group = QGroupBox("評価パラメータ")
        params_layout = QFormLayout(params_group)

        self.temperature_spin = QSpinBox()
        self.temperature_spin.setRange(0, 10)
        self.temperature_spin.setValue(0)
        self.temperature_spin.setToolTip("0.0 - 1.0の範囲で設定（0.1単位）")
        params_layout.addRow("Temperature:", self.temperature_spin)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 4000)
        self.max_tokens_spin.setValue(1000)
        self.max_tokens_spin.setSingleStep(100)
        params_layout.addRow("最大トークン数:", self.max_tokens_spin)

        layout.addWidget(params_group)

        return tab

    def _create_history_tab(self) -> QWidget:
        """履歴タブを作成

        Returns:
            QWidget: 履歴タブウィジェット
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 履歴リスト
        layout.addWidget(QLabel("評価履歴:"))
        self.history_edit = QTextEdit()
        self.history_edit.setReadOnly(True)
        layout.addWidget(self.history_edit)

        # 履歴を読み込む
        self._load_history()

        return tab

    def _load_history(self):
        """評価履歴を読み込む"""
        if not self.db:
            return

        try:
            history = self.db.get_evaluation_history(self.entry)
            if not history:
                self.history_edit.setText("評価履歴はありません。")
                return

            history_text = ""
            for i, item in enumerate(history):
                history_text += (
                    f"=== 評価 #{i + 1} ({item.get('created_at', '不明')}) ===\n"
                )
                history_text += f"総合スコア: {item.get('overall_score', '不明')}\n"

                if "metric_scores" in item:
                    history_text += "指標スコア:\n"
                    for metric, score in item["metric_scores"].items():
                        history_text += f"  - {metric}: {score}\n"

                if "category_scores" in item:
                    history_text += "カテゴリスコア:\n"
                    for category, score in item["category_scores"].items():
                        history_text += f"  - {category}: {score}\n"

                history_text += "\n"

            self.history_edit.setText(history_text)
        except Exception as e:
            logger.error(f"履歴読み込みエラー: {e}")
            self.history_edit.setText(f"履歴の読み込み中にエラーが発生しました: {e}")

    def _load_api_keys(self) -> None:
        """APIキー設定を読み込む"""
        try:
            # APIキー設定を保存するファイルパス
            api_key_file = os.path.join(
                os.path.expanduser("~"), ".sgpo_editor", "api_keys.json"
            )

            # ファイルが存在しない場合は空の辞書を返す
            if not os.path.exists(api_key_file):
                logger.debug("APIキーファイルが存在しません: " + api_key_file)
                return

            with open(api_key_file, "r", encoding="utf-8") as f:
                api_keys = json.load(f)

            # APIキーを設定
            self._set_api_keys(api_keys)
            logger.info("APIキー設定を読み込みました")

        except json.JSONDecodeError as e:
            logger.error(f"APIキーファイルの解析に失敗しました: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "APIキー読み込みエラー",
                f"APIキー設定ファイルの解析に失敗しました。\n"
                f"ファイルが破損している可能性があります。\n"
                f"詳細: {str(e)}",
            )
        except Exception as e:
            logger.error(f"APIキー設定の読み込みに失敗しました: {e}", exc_info=True)
            QMessageBox.warning(
                self,
                "APIキー読み込みエラー",
                f"APIキー設定の読み込み中にエラーが発生しました。\n詳細: {str(e)}",
            )

    def _save_api_keys(self) -> None:
        """APIキー設定を保存する"""
        api_keys = {}

        # OpenAI APIキーを取得
        openai_api_key = self.openai_api_key.text().strip()
        if openai_api_key:
            api_keys["openai"] = openai_api_key

        # Claude APIキーを取得
        claude_api_key = self.claude_api_key.text().strip()
        if claude_api_key:
            api_keys["claude"] = claude_api_key

        # Gemini APIキーを取得
        gemini_api_key = self.gemini_api_key.text().strip()
        if gemini_api_key:
            api_keys["gemini"] = gemini_api_key

        try:
            # APIキー設定を保存するディレクトリ
            config_dir = os.path.join(os.path.expanduser("~"), ".sgpo_editor")
            os.makedirs(config_dir, exist_ok=True)

            # APIキー設定を保存するファイルパス
            api_key_file = os.path.join(config_dir, "api_keys.json")

            with open(api_key_file, "w", encoding="utf-8") as f:
                json.dump(api_keys, f)

            logger.info("APIキー設定を保存しました")

            # 確認メッセージを表示
            QMessageBox.information(self, "設定保存完了", "APIキー設定を保存しました。")

        except PermissionError as e:
            logger.error(
                f"APIキーファイルの書き込み権限がありません: {e}", exc_info=True
            )
            QMessageBox.critical(
                self,
                "権限エラー",
                f"APIキー設定の保存に失敗しました。\n"
                f"ファイルの書き込み権限がない可能性があります。\n"
                f"詳細: {str(e)}",
            )
        except Exception as e:
            logger.error(f"APIキー設定の保存に失敗しました: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "保存エラー",
                f"APIキー設定の保存中にエラーが発生しました。\n詳細: {str(e)}",
            )

    def _set_api_keys(self, api_keys: dict) -> None:
        """APIキーを設定フォームにセット

        Args:
            api_keys: APIキー辞書
        """
        # キーが無い場合は何もしない
        if not api_keys:
            logger.debug("APIキーがありません")
            return

        # OpenAI APIキーをセット
        if "openai" in api_keys:
            self.openai_api_key.setText(api_keys["openai"])
            logger.debug("OpenAI APIキーを設定しました")

        # Claude APIキーをセット
        if "claude" in api_keys:
            self.claude_api_key.setText(api_keys["claude"])
            logger.debug("Claude APIキーを設定しました")

        # Gemini APIキーをセット
        if "gemini" in api_keys:
            self.gemini_api_key.setText(api_keys["gemini"])
            logger.debug("Gemini APIキーを設定しました")

        # 設定されたAPIキーの数を確認
        api_key_count = sum(1 for k in ["openai", "claude", "gemini"] if k in api_keys)
        logger.debug(f"設定されたAPIキー数: {api_key_count}")

        # APIキーが設定されていない場合は警告
        if api_key_count == 0:
            logger.warning("APIキーが設定されていません")
            # 初回起動時はメッセージボックスを表示しない
            if hasattr(self, "_first_load") and not self._first_load:
                QMessageBox.warning(
                    self,
                    "APIキー未設定",
                    "評価を実行するには、少なくとも1つのAPIキーを設定してください。",
                )
        else:
            logger.info(f"{api_key_count}個のAPIキーが設定されています")

    def _add_custom_metric(self):
        """カスタム評価指標を追加"""
        name = self.metric_name_edit.text().strip()
        desc = self.metric_desc_edit.text().strip()

        if not name or not desc:
            QMessageBox.warning(self, "入力エラー", "指標名と説明を入力してください。")
            return

        # 指標を追加
        metric = EvaluationMetric(name=name, description=desc)
        self.metrics.append(metric)

        # チェックボックスを追加
        checkbox = QCheckBox(f"{name}: {desc}")
        checkbox.setChecked(True)
        self.tab_widget.widget(1).layout().itemAt(1).widget().layout().addWidget(
            checkbox
        )

        # スコアラベルを追加
        metric_layout = QHBoxLayout()
        metric_layout.addWidget(QLabel(f"{name}:"))
        score_label = QLabel("未評価")
        self.metric_score_labels[name] = score_label
        metric_layout.addWidget(score_label)
        self.tab_widget.widget(0).layout().itemAt(2).widget().layout().addLayout(
            metric_layout
        )

        # 入力フィールドをクリア
        self.metric_name_edit.clear()
        self.metric_desc_edit.clear()

        QMessageBox.information(self, "指標追加", f"評価指標「{name}」を追加しました。")

    def _evaluate(self):
        """評価を実行"""
        # 評価対象エントリのチェック
        if not self.entry:
            logger.warning("評価対象エントリがありません")
            QMessageBox.warning(self, "評価エラー", "評価対象のエントリがありません。")
            return

        # 原文と訳文があるか確認
        if not self.entry.msgid or not self.entry.msgstr:
            QMessageBox.warning(self, "エラー", "原文または訳文が空です。")
            return

        # プロバイダーを取得
        provider_idx = self.provider_combo.currentIndex()
        provider = self.provider_combo.itemData(provider_idx)
        logger.debug(f"選択されたプロバイダー: {provider}")

        # APIキーを確認
        api_key = ""
        if provider == LLMProvider.OPENAI:
            api_key = self.openai_api_key.text()
            if not api_key:
                QMessageBox.warning(
                    self,
                    "APIキーエラー",
                    "OpenAI APIキーが設定されていません。\n"
                    "「設定」タブの「APIキー設定」ボタンで設定してください。",
                )
                # 設定タブに切り替え
                self.tab_widget.setCurrentIndex(1)
                return
            logger.debug("OpenAI APIキーが設定されています")
        elif provider == LLMProvider.ANTHROPIC:
            api_key = self.claude_api_key.text()
            if not api_key:
                QMessageBox.warning(
                    self,
                    "APIキーエラー",
                    "Claude APIキーが設定されていません。\n"
                    "「設定」タブの「APIキー設定」ボタンで設定してください。",
                )
                # 設定タブに切り替え
                self.tab_widget.setCurrentIndex(1)
                return
            logger.debug("Claude APIキーが設定されています")

        # モデルを取得
        model_idx = self.model_combo.currentIndex()
        model = self.model_combo.itemData(model_idx)
        logger.debug(f"選択されたモデル: {model}")

        # 評価言語を取得
        lang_idx = self.lang_combo.currentIndex()
        language = self.lang_combo.itemData(lang_idx)
        logger.debug(f"選択された言語: {language}")

        # 温度パラメータを取得
        temperature = self.temperature_spin.value() / 10.0
        logger.debug(f"温度パラメータ: {temperature}")

        # 最大トークン数を取得
        max_tokens = self.max_tokens_spin.value()
        logger.debug(f"最大トークン数: {max_tokens}")

        # 選択された評価指標を取得
        selected_metrics = []
        for i in range(len(self.metrics)):
            metric_layout = (
                self.tab_widget.widget(1).layout().itemAt(1).widget().layout()
            )
            if i < metric_layout.count():
                checkbox_item = metric_layout.itemAt(i)
                if (
                    checkbox_item
                    and checkbox_item.widget()
                    and isinstance(checkbox_item.widget(), QCheckBox)
                ):
                    checkbox = checkbox_item.widget()
                    if checkbox.isChecked():
                        selected_metrics.append(self.metrics[i])

        # 評価指標が選択されているか確認
        if not selected_metrics:
            QMessageBox.warning(
                self, "設定エラー", "少なくとも1つの評価指標を選択してください。"
            )
            self.tab_widget.setCurrentIndex(1)
            return

        logger.debug(f"選択された評価指標: {[m.name for m in selected_metrics]}")

        # 評価器を初期化
        logger.debug("評価器を初期化")
        try:
            self.evaluator = LLMEvaluator(
                provider=provider,
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"評価器の初期化エラー: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "評価器エラー",
                f"評価器の初期化中にエラーが発生しました: {str(e)}",
            )
            return

        # 進捗バーを表示
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        logger.debug("進捗バー: 10%")

        # 評価ボタンを無効化
        self.evaluate_button.setEnabled(False)

        # 状態表示を更新
        self.status_label.setText("評価中...")

        # ワーカースレッドを作成
        self.worker = EvaluationWorker(
            self.evaluator,
            self.entry,
            selected_metrics,  # 選択された評価指標のみを使用
            language,
            self.db,
        )

        # シグナルを接続
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.evaluation_finished.connect(self._on_evaluation_finished)
        self.worker.evaluation_error.connect(self._on_evaluation_error)

        # スレッド開始
        self.worker.start()
        logger.debug("評価ワーカースレッドを開始しました")

    def _on_evaluation_finished(self, result):
        """評価完了時の処理

        Args:
            result: 評価結果
        """
        logger.debug("評価完了")

        # 結果を表示
        self._display_evaluation_result(result)

        # 評価結果を保存
        self._save_evaluation_result(result)

        # 進捗バーを100%に
        self.progress_bar.setValue(100)

        # 評価完了シグナルを発行
        self.evaluation_completed.emit(self.entry, result)

        # UI状態を復元
        self.progress_bar.setVisible(False)
        self.evaluate_button.setEnabled(True)
        self.status_label.setText("評価が完了しました")

        # 完了メッセージ
        QMessageBox.information(self, "評価完了", "翻訳の評価が完了しました。")

        # 評価タブに切り替え
        self.tab_widget.setCurrentIndex(0)

    def _on_evaluation_error(self, error_message):
        """評価エラー時の処理

        Args:
            error_message: エラーメッセージ
        """
        logger.error(f"評価エラー: {error_message}")

        # エラーメッセージを表示
        QMessageBox.critical(
            self,
            "評価エラー",
            f"評価中にエラーが発生しました:\n{error_message}\n\n"
            "APIキーの設定と接続状態を確認してください。",
        )

        # UI状態を復元
        self.progress_bar.setVisible(False)
        self.evaluate_button.setEnabled(True)
        self.status_label.setText("評価に失敗しました")

        # エントリの評価状態を更新
        self.entry.evaluation_state = EvaluationState.ERROR
        if self.db:
            try:
                self.db.save_evaluation_state(self.entry, EvaluationState.ERROR)
            except Exception as e:
                logger.error(f"評価状態の保存に失敗しました: {e}", exc_info=True)

    def _display_evaluation_result(self, result: EvaluationResult):
        """評価結果を表示

        Args:
            result: 評価結果
        """
        # 総合スコア
        self.overall_score_label.setText(f"{result.overall_score}")

        # 指標スコア
        for metric_name, score in result.metric_scores.items():
            if metric_name in self.metric_score_labels:
                self.metric_score_labels[metric_name].setText(f"{score}")

        # レビューコメント
        comments_text = ""
        for metric_name, comment in result.comments.items():
            comments_text += f"【{metric_name}】\n{comment}\n\n"

        self.review_comment_edit.setText(comments_text)

        # 履歴タブを更新
        self._load_history()

    def _save_evaluation_result(self, result: EvaluationResult):
        """評価結果を保存

        Args:
            result: 評価結果
        """
        # エントリに評価結果を設定
        self.entry.overall_quality_score = result.overall_score

        # 指標スコアを設定
        for metric_name, score in result.metric_scores.items():
            self.entry.set_metric_score(metric_name, score)

        # レビューコメントを追加
        for metric_name, comment in result.comments.items():
            self.entry.add_review_comment(
                author=f"LLM ({self.provider_combo.currentText()})",
                comment=f"【{metric_name}】\n{comment}",
            )

        # 評価状態を更新
        self.entry.evaluation_state = EvaluationState.EVALUATED

        # データベースに保存
        if self.db:
            self.db.save_entry_evaluation_data(self.entry)
