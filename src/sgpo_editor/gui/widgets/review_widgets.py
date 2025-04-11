"""レビュー関連ウィジェット"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class TranslatorCommentWidget(QWidget):
    """翻訳者コメント表示ウィジェット"""

    comment_changed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry = None
        self._db = None

        self.setWindowTitle("翻訳者コメント")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI構築"""
        layout = QVBoxLayout(self)

        # ヘッダーラベル
        header_label = QLabel("翻訳者コメント：")
        layout.addWidget(header_label)

        # コメント編集エリア
        self.comment_edit = QPlainTextEdit(self)
        self.comment_edit.setPlaceholderText("ここに翻訳者コメントを入力してください")
        self.comment_edit.textChanged.connect(self._on_comment_changed)
        layout.addWidget(self.comment_edit)

        # ボタンエリア
        button_layout = QHBoxLayout()

        self.apply_button = QPushButton("適用", self)
        self.apply_button.clicked.connect(self._on_apply_clicked)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定"""
        self._current_entry = entry

        if entry is None:
            self.comment_edit.setPlainText("")
            return

        # tcommentを表示
        self.comment_edit.setPlainText(entry.tcomment or "")

    def set_database(self, db: InMemoryEntryStore) -> None:
        """データベース参照を設定"""
        self._db = db

    def _on_comment_changed(self) -> None:
        """コメントが変更されたときの処理"""
        self.comment_changed.emit()

    def _on_apply_clicked(self) -> None:
        """適用ボタンがクリックされたときの処理"""
        if not self._current_entry or not self._db:
            return

        # 現在のコメントを取得
        new_comment = self.comment_edit.toPlainText()

        # エントリのコメントを更新
        self._current_entry.tcomment = new_comment

        # データベース更新
        self._db.update_entry_field(self._current_entry.key, "tcomment", new_comment)

        # 変更通知
        self.comment_changed.emit()

    def get_comment(self) -> str:
        """現在のコメントを取得"""
        return self.comment_edit.toPlainText()


class ReviewCommentWidget(QWidget):
    """レビューコメント表示・追加ウィジェット"""

    comment_added = Signal()
    comment_removed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry = None
        self._db = None

        self.setWindowTitle("レビューコメント")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI初期化"""
        layout = QVBoxLayout()

        # コメントリスト
        list_label = QLabel("既存のコメント：")
        layout.addWidget(list_label)

        self.comment_list = QListWidget()
        layout.addWidget(self.comment_list)

        # 新規コメント追加セクション
        add_section = QGroupBox("新規コメント追加")
        add_layout = QVBoxLayout()

        # 作成者入力
        author_layout = QHBoxLayout()
        author_label = QLabel("作成者：")
        self.author_edit = QLineEdit()
        author_layout.addWidget(author_label)
        author_layout.addWidget(self.author_edit)
        add_layout.addLayout(author_layout)

        # コメント入力
        comment_label = QLabel("コメント：")
        add_layout.addWidget(comment_label)
        self.comment_edit = QPlainTextEdit()
        add_layout.addWidget(self.comment_edit)

        # 操作ボタン
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("追加")
        self.add_button.clicked.connect(self._on_add_comment)
        self.remove_button = QPushButton("削除")
        self.remove_button.clicked.connect(self._on_remove_comment)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)

        add_layout.addLayout(button_layout)
        add_section.setLayout(add_layout)
        layout.addWidget(add_section)

        self.setLayout(layout)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定"""
        self._current_entry = entry
        self.comment_list.clear()

        if entry is None:
            return

        # レビューコメントをリストに表示
        for comment in entry.review_comments:
            item = QListWidgetItem()
            timestamp = comment.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass

            author = comment.get("author", "")
            text = comment.get("comment", "")
            item.setText(f"[{timestamp}] {author}: {text}")
            item.setData(Qt.ItemDataRole.UserRole, comment)
            self.comment_list.addItem(item)

    def set_database(self, db: InMemoryEntryStore) -> None:
        """データベース参照を設定"""
        self._db = db

    def _on_add_comment(self) -> None:
        """コメント追加ボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        author = self.author_edit.text().strip()
        comment = self.comment_edit.toPlainText().strip()

        if not author or not comment:
            return  # 作成者またはコメントが空の場合は追加しない

        # コメントを追加
        comment_id = self._current_entry.add_review_comment(
            author=author, comment=comment
        )

        # コメントIDからオブジェクトを取得
        comment_obj = next(
            (
                c
                for c in self._current_entry.review_comments
                if c.get("id") == comment_id
            ),
            None,
        )

        if comment_obj:
            # データベースにも即時反映
            self._db.update_entry_field(
                self._current_entry.key,
                "review_comments",
                self._current_entry.review_comments,
            )

        # UIを更新
        self.set_entry(self._current_entry)

        # 入力フィールドをクリア
        self.comment_edit.clear()

        # シグナル発行
        self.comment_added.emit()

    def _on_remove_comment(self) -> None:
        """コメント削除ボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        # 選択されたアイテムを取得
        selected_item = self.comment_list.currentItem()
        if not selected_item:
            return

        # アイテムからコメントデータを取得
        comment_data = selected_item.data(Qt.ItemDataRole.UserRole)
        if not comment_data:
            return

        # コメントIDを取得して削除
        comment_id = comment_data.get("id")
        if comment_id:
            # エントリからコメント削除
            self._current_entry.remove_review_comment(comment_id)

            # データベースからも即時削除
            self._db.update_entry_field(
                self._current_entry.key,
                "review_comments",
                self._current_entry.review_comments,
            )

            # UIを更新
            self.set_entry(self._current_entry)

            # シグナル発行
            self.comment_removed.emit()

    def add_review_comment(self, author: str, comment: str) -> None:
        """レビューコメントを追加

        Args:
            author: コメント作成者
            comment: コメント内容
        """
        if not self._current_entry or not self._db:
            return

        # 追加するコメントを作成
        comment_obj = {
            "id": str(uuid.uuid4()),
            "author": author,
            "comment": comment,
            "timestamp": datetime.now().isoformat(),
        }

        # エントリにコメントを追加
        self._current_entry.review_comments.append(comment_obj)

        # データベースにも即時反映
        self._db.update_entry_field(
            self._current_entry.key,
            "review_comments",
            self._current_entry.review_comments,
        )

        # UIを更新
        self.set_entry(self._current_entry)

        # シグナル発行
        self.comment_added.emit()


class QualityScoreWidget(QWidget):
    """品質スコア表示・編集ウィジェット"""

    score_updated = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry = None
        self._db = None

        self.setWindowTitle("品質スコア")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI初期化"""
        layout = QVBoxLayout()

        # 全体スコアセクション
        overall_group = QGroupBox("全体スコア")
        overall_layout = QVBoxLayout()

        overall_score_layout = QHBoxLayout()
        overall_score_label = QLabel("スコア（0-100）：")
        self.overall_score_spinner = QSpinBox()
        self.overall_score_spinner.setRange(0, 100)
        overall_score_layout.addWidget(overall_score_label)
        overall_score_layout.addWidget(self.overall_score_spinner)

        self.apply_button = QPushButton("適用")
        self.apply_button.clicked.connect(self._on_apply_score)
        overall_score_layout.addWidget(self.apply_button)

        overall_layout.addLayout(overall_score_layout)
        overall_group.setLayout(overall_layout)
        layout.addWidget(overall_group)

        # カテゴリ別スコアセクション
        category_group = QGroupBox("カテゴリ別スコア")
        category_layout = QVBoxLayout()

        # カテゴリスコア一覧表
        self.category_scores_table = QTableWidget(0, 2)
        self.category_scores_table.setHorizontalHeaderLabels(["カテゴリ", "スコア"])
        self.category_scores_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        category_layout.addWidget(self.category_scores_table)

        # 新規カテゴリスコア追加
        add_layout = QHBoxLayout()
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("カテゴリ名")
        self.category_score_spinner = QSpinBox()
        self.category_score_spinner.setRange(0, 100)
        self.add_category_button = QPushButton("追加")
        self.add_category_button.clicked.connect(self._on_add_category_score)

        add_layout.addWidget(self.category_edit)
        add_layout.addWidget(self.category_score_spinner)
        add_layout.addWidget(self.add_category_button)

        category_layout.addLayout(add_layout)
        category_group.setLayout(category_layout)
        layout.addWidget(category_group)

        # リセットボタン
        self.reset_button = QPushButton("すべてリセット")
        self.reset_button.clicked.connect(self._on_reset_scores)
        layout.addWidget(self.reset_button)

        self.setLayout(layout)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定"""
        self._current_entry = entry

        if not entry:
            self.overall_score_spinner.setValue(0)
            self.category_scores_table.setRowCount(0)
            return

        # 全体スコアを設定
        self.overall_score_spinner.setValue(entry.overall_quality_score or 0)

        # カテゴリ別スコアをテーブルに反映
        self.category_scores_table.setRowCount(0)
        if entry.category_quality_scores:
            for category, score in entry.category_quality_scores.items():
                row = self.category_scores_table.rowCount()
                self.category_scores_table.insertRow(row)
                self.category_scores_table.setItem(row, 0, QTableWidgetItem(category))
                self.category_scores_table.setItem(row, 1, QTableWidgetItem(str(score)))

    def set_database(self, db: InMemoryEntryStore) -> None:
        """データベース参照を設定"""
        self._db = db

    def _on_apply_score(self) -> None:
        """スコア適用ボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        # 全体スコアを更新
        score = self.overall_score_spinner.value()
        self._current_entry.set_overall_quality_score(score)

        # データベースに即時反映
        self._db.update_entry_field(
            self._current_entry.key, "overall_quality_score", score
        )

        # 変更通知
        self.score_updated.emit()

    def _on_add_category_score(self) -> None:
        """カテゴリスコア追加ボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        category = self.category_edit.text().strip()
        score = self.category_score_spinner.value()

        if not category:
            return  # カテゴリ名が空の場合は追加しない

        # カテゴリスコアを追加
        self._current_entry.set_category_score(category, score)

        # データベースに即時反映
        if not self._current_entry.category_quality_scores:
            self._db.update_entry_field(
                self._current_entry.key, "category_quality_scores", {category: score}
            )
        else:
            self._db.update_entry_field(
                self._current_entry.key,
                "category_quality_scores",
                self._current_entry.category_quality_scores,
            )

        # UIを更新
        self.set_entry(self._current_entry)

        # フォームをクリア
        self.category_edit.clear()
        self.category_score_spinner.setValue(50)  # デフォルト値にリセット

        # 変更通知
        self.score_updated.emit()

    def _on_reset_scores(self) -> None:
        """スコアリセットボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        # 確認ダイアログを表示
        reply = QMessageBox.question(
            self,
            "確認",
            "すべての品質スコアをリセットしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # スコアをクリア
            self._current_entry.clear_quality_scores()

            # データベースに即時反映
            self._db.update_entry_field(
                self._current_entry.key, "overall_quality_score", None
            )
            self._db.update_entry_field(
                self._current_entry.key, "category_quality_scores", {}
            )

            # UIを更新
            self.set_entry(self._current_entry)

            # 変更通知
            self.score_updated.emit()

    def set_quality_score(self, score: int) -> None:
        """品質スコアを設定

        Args:
            score: 設定する品質スコア（0-100）
        """
        if not self._current_entry or not self._db:
            return

        # スピナーの値を更新
        self.overall_score_spinner.setValue(score)

        # エントリの品質スコアを更新
        self._current_entry.overall_quality_score = score

        # データベースに即時反映
        self._db.update_entry_review_data(
            self._current_entry.key, "quality_score", score
        )

        # 変更通知
        self.score_updated.emit()


class CheckResultWidget(QWidget):
    """チェック結果表示・追加ウィジェット"""

    result_added = Signal()
    result_removed = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry = None
        self._db = None

        self.setWindowTitle("チェック結果")
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI初期化"""
        layout = QVBoxLayout()

        # チェック結果一覧表
        result_label = QLabel("チェック結果一覧：")
        layout.addWidget(result_label)

        self.result_table = QTableWidget(0, 3)
        self.result_table.setHorizontalHeaderLabels(["コード", "メッセージ", "重要度"])
        self.result_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.result_table)

        # 新規チェック結果追加セクション
        add_section = QGroupBox("新規チェック結果追加")
        add_layout = QVBoxLayout()

        # コード入力
        code_layout = QHBoxLayout()
        code_label = QLabel("コード：")
        self.code_spinner = QSpinBox()
        self.code_spinner.setRange(1000, 9999)
        code_layout.addWidget(code_label)
        code_layout.addWidget(self.code_spinner)
        add_layout.addLayout(code_layout)

        # メッセージ入力
        message_label = QLabel("メッセージ：")
        add_layout.addWidget(message_label)
        self.message_edit = QPlainTextEdit()
        self.message_edit.setMaximumHeight(80)
        add_layout.addWidget(self.message_edit)

        # 重要度選択
        severity_layout = QHBoxLayout()
        severity_label = QLabel("重要度：")
        self.severity_combo = QComboBox()
        self.severity_combo.addItems(["error", "warning", "info"])
        severity_layout.addWidget(severity_label)
        severity_layout.addWidget(self.severity_combo)
        add_layout.addLayout(severity_layout)

        # 操作ボタン
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("追加")
        self.add_button.clicked.connect(self._on_add_result)
        self.remove_button = QPushButton("削除")
        self.remove_button.clicked.connect(self._on_remove_result)
        self.clear_button = QPushButton("すべてクリア")
        self.clear_button.clicked.connect(self._on_clear_results)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.clear_button)
        add_layout.addLayout(button_layout)

        add_section.setLayout(add_layout)
        layout.addWidget(add_section)

        self.setLayout(layout)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定"""
        self._current_entry = entry
        self.result_table.setRowCount(0)

        if entry is None:
            return

        # チェック結果をテーブルに表示
        for i, result in enumerate(entry.check_results):
            self.result_table.insertRow(i)
            self.result_table.setItem(
                i, 0, QTableWidgetItem(str(result.get("code", "")))
            )
            self.result_table.setItem(i, 1, QTableWidgetItem(result.get("message", "")))
            self.result_table.setItem(
                i, 2, QTableWidgetItem(result.get("severity", ""))
            )

            # チェック結果データをユーザーロールに保存
            for col in range(3):
                item = self.result_table.item(i, col)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, result)

    def set_database(self, db: InMemoryEntryStore) -> None:
        """データベース参照を設定"""
        self._db = db

    def _on_add_result(self) -> None:
        """チェック結果追加ボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        code = self.code_spinner.value()
        message = self.message_edit.text().strip()
        severity = self.severity_combo.currentText()

        if not message:
            QMessageBox.warning(self, "入力エラー", "メッセージを入力してください")
            return

        # エントリにチェック結果を追加
        if not self._current_entry.check_results:
            self._current_entry.check_results = []

        check_result = {
            "code": code,
            "message": message,
            "severity": severity,
        }

        self._current_entry.check_results.append(check_result)

        # データベースに即時反映
        try:
            check_result = {
                "code": code,
                "message": message,
                "severity": severity,
            }
            self._db.add_check_result(self._current_entry.key, check_result)
            logger.debug(f"チェック結果を追加しました: {code} - {message}")
        except Exception as e:
            logger.error(f"チェック結果追加エラー: {e}")
            QMessageBox.warning(
                self, "エラー", f"チェック結果の追加に失敗しました: {e}"
            )
            # エントリの状態を元に戻す
            self._current_entry.check_results.pop()
            return

        # テーブルに追加
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setItem(row, 0, QTableWidgetItem(str(code)))
        self.result_table.setItem(row, 1, QTableWidgetItem(message))
        self.result_table.setItem(row, 2, QTableWidgetItem(severity))

        # フォームをクリア
        self.message_edit.clear()

        # 変更通知
        self.result_added.emit()

    def _on_remove_result(self) -> None:
        """チェック結果削除ボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        # 現在選択されている行を取得
        current_row = self.result_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(
                self, "エラー", "削除するチェック結果を選択してください"
            )
            return

        # 削除確認
        reply = QMessageBox.question(
            self,
            "確認",
            "選択したチェック結果を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            # 選択された行のコードとメッセージを取得
            code_item = self.result_table.item(current_row, 0)
            message_item = self.result_table.item(current_row, 1)

            if code_item and message_item:
                code = int(code_item.text())
                message = message_item.text()

                # データベースから削除
                self._db.remove_check_result(self._current_entry.key, str(code))
                logger.debug(f"チェック結果を削除しました: {code} - {message}")

                # エントリオブジェクトからも削除
                if self._current_entry.check_results:
                    for i, result in enumerate(self._current_entry.check_results):
                        if (
                            result.get("code") == code
                            and result.get("message") == message
                        ):
                            self._current_entry.check_results.pop(i)
                            break

                # テーブルから行を削除
                self.result_table.removeRow(current_row)

                # 変更通知
                self.result_removed.emit()

        except Exception as e:
            logger.error(f"チェック結果削除エラー: {e}")
            QMessageBox.warning(
                self, "エラー", f"チェック結果の削除に失敗しました: {e}"
            )

    def _on_clear_results(self) -> None:
        """チェック結果クリアボタンクリック時の処理"""
        if not self._current_entry or not self._db:
            return

        # 削除確認
        reply = QMessageBox.question(
            self,
            "確認",
            "すべてのチェック結果をクリアしますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            if self._current_entry.check_results:
                for result in list(self._current_entry.check_results):
                    code = result.get("code", "")
                    if code:
                        self._db.remove_check_result(self._current_entry.key, str(code))
            
            logger.debug(f"チェック結果をクリアしました: {self._current_entry.key}")

            # エントリオブジェクトからも削除
            self._current_entry.check_results = []

            # テーブルをクリア
            self.result_table.setRowCount(0)

            # 変更通知
            self.result_removed.emit()

        except Exception as e:
            logger.error(f"チェック結果クリアエラー: {e}")
            QMessageBox.warning(
                self, "エラー", f"チェック結果のクリアに失敗しました: {e}"
            )
