"""エントリ編集用ウィジェット"""

import logging
from typing import Optional, cast, Dict, Any, List
from enum import Enum, auto

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QFrame,
    QComboBox,
    QSizePolicy,
    QCheckBox,
    QSplitter,
    QTabWidget,
    QDialog,
)
from PySide6.QtCore import Signal, Qt, QSize, QTimer

from sgpo_editor.models import EntryModel
from sgpo_editor.models.database import Database
from sgpo_editor.gui.widgets.review_widgets import (
    TranslatorCommentWidget,
    ReviewCommentWidget,
    QualityScoreWidget,
    CheckResultWidget,
)
from sgpo_editor.gui.widgets.debug_widgets import EntryDebugWidget

logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """レイアウトタイプ"""

    LAYOUT1 = auto()  # msgctxt上部、msgid/msgstr下部横並び
    LAYOUT2 = auto()  # 前のレイアウト（左右分割）


class EditBox(QWidget):
    """編集ボックス"""

    text_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._placeholder = ""
        self._current_text = ""

        # エディタの設定
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText(self._placeholder)
        self.editor.textChanged.connect(self._on_text_changed)
        # msgctxt の高さを1行分に固定
        single_line_height = self.editor.fontMetrics().height() + 8
        self.editor.setFixedHeight(single_line_height)

        # レイアウトの設定
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.editor)
        self.setLayout(layout)

    def _on_text_changed(self) -> None:
        """テキストが変更されたときの処理"""
        text = self.editor.toPlainText()
        logger.debug("EditBox._on_text_changed(): text='%s'", text)
        self._current_text = text
        self.text_changed.emit(text)

    def setText(self, text: str) -> None:
        """テキストを設定"""
        logger.debug("EditBox.setText(): text='%s'", text)
        if text is None:
            text = ""
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self._current_text = text
        self.editor.blockSignals(False)
        self.text_changed.emit(text)

    def text(self) -> str:
        """テキストを取得"""
        logger.debug("EditBox.text(): text='%s'", self._current_text)
        return self._current_text


class EntryEditor(QWidget):
    """POエントリ編集用ウィジェット"""

    text_changed = Signal()
    apply_clicked = Signal()
    entry_changed = Signal(int)  # エントリが変更されたときのシグナル

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry = None
        self._current_layout = LayoutType.LAYOUT1
        self._database = None  # データベース参照
        # テキスト変更通知を遅延させるためのタイマー
        self._text_change_timer = QTimer(self)
        self._text_change_timer.setSingleShot(True)
        self._text_change_timer.timeout.connect(self._emit_text_changed)
        
        # レビュー関連ダイアログの参照を保持
        self._review_dialogs: Dict[str, QDialog] = {}

        # メインレイアウト
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 上部ヘッダー部分（msgctxt）
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # msgctxt
        self.context_edit = EditBox(self)
        self.context_edit.text_changed.connect(self._on_text_changed)
        header_layout.addWidget(self.context_edit)

        header_widget.setLayout(header_layout)
        main_layout.addWidget(header_widget)

        # エディタ部分（msgidとmsgstr）
        self.editor_widget = QWidget()
        self.editor_layout = QHBoxLayout()
        self.editor_layout.setContentsMargins(0, 0, 0, 0)

        # msgid
        self.msgid_edit = QPlainTextEdit(self)
        self.msgid_edit.setReadOnly(True)
        self.editor_layout.addWidget(self.msgid_edit)

        # msgstr
        self.msgstr_edit = QPlainTextEdit(self)
        self.msgstr_edit.textChanged.connect(self._on_msgstr_changed)
        self.editor_layout.addWidget(self.msgstr_edit)

        self.editor_widget.setLayout(self.editor_layout)
        main_layout.addWidget(self.editor_widget)

        # 下部コントロール部分（fuzzyチェックボックスとApplyボタン、各種機能ボタン）
        control_widget = QWidget()
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)

        # fuzzyチェックボックス
        self.fuzzy_checkbox = QCheckBox("Fuzzy", self)
        self.fuzzy_checkbox.stateChanged.connect(self._on_fuzzy_changed)
        control_layout.addWidget(self.fuzzy_checkbox)

        # スペーサーを追加して右寄せにする
        control_layout.addStretch()
        
        # 各機能ボタン
        self.tcomment_button = QPushButton("翻訳者コメント", self)
        self.tcomment_button.clicked.connect(lambda: self._show_review_dialog("translator_comment"))
        control_layout.addWidget(self.tcomment_button)
        
        self.review_comment_button = QPushButton("レビューコメント", self)
        self.review_comment_button.clicked.connect(lambda: self._show_review_dialog("review_comment"))
        control_layout.addWidget(self.review_comment_button)
        
        self.quality_score_button = QPushButton("品質スコア", self)
        self.quality_score_button.clicked.connect(lambda: self._show_review_dialog("quality_score"))
        control_layout.addWidget(self.quality_score_button)
        
        self.check_result_button = QPushButton("チェック結果", self)
        self.check_result_button.clicked.connect(lambda: self._show_review_dialog("check_result"))
        control_layout.addWidget(self.check_result_button)
        
        # デバッグボタン
        self.debug_button = QPushButton("デバッグ", self)
        self.debug_button.clicked.connect(lambda: self._show_review_dialog("debug"))
        control_layout.addWidget(self.debug_button)

        # Applyボタン
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.clicked.connect(self._on_apply_clicked)
        self.apply_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        control_layout.addWidget(self.apply_button)

        control_widget.setLayout(control_layout)
        main_layout.addWidget(control_widget)

        self.setLayout(main_layout)
        self.setEnabled(False)  # 初期状態では無効化
        
    def _show_review_dialog(self, dialog_type: str) -> None:
        """レビュー関連ダイアログを表示"""
        logger.debug(f"Show review dialog: {dialog_type}")
        
        if not self._current_entry:
            logger.warning("Entry is not set. Cannot show review dialog.")
            return
            
        if dialog_type not in self._review_dialogs:
            # ダイアログが未作成の場合は新規作成
            dialog = QDialog(self)
            dialog.setWindowTitle(f"対訳表示: {dialog_type}")
            # 常に最前面に表示されるようにウィンドウフラグを設定
            dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            
            # ダイアログにレイアウトを設定
            layout = QVBoxLayout(dialog)
            
            # ダイアログの種類に応じたウィジェットを作成
            widget = None
            if dialog_type == "translator_comment":
                widget = TranslatorCommentWidget(dialog)
                # シグナルを接続
                widget.comment_changed.connect(self._on_text_changed)
            elif dialog_type == "review_comment":
                widget = ReviewCommentWidget(dialog)
            elif dialog_type == "quality_score":
                widget = QualityScoreWidget(dialog)
            elif dialog_type == "check_result":
                widget = CheckResultWidget(dialog)
            elif dialog_type == "debug":
                widget = EntryDebugWidget(dialog)
                
            # ウィジェットがNoneでない場合はレイアウトに追加
            if widget:
                layout.addWidget(widget)
                widget.set_entry(self._current_entry)
                
                # データベース参照を設定（対応するメソッドがある場合）
                if hasattr(widget, "set_database") and self._database:
                    widget.set_database(self._database)
                
            # ダイアログを保存
            dialog.widget = widget  # ウィジェットへの参照を保持
            self._review_dialogs[dialog_type] = dialog
        else:
            dialog = self._review_dialogs[dialog_type]
            # 現在のエントリを更新
            if hasattr(dialog.widget, "set_entry"):
                dialog.widget.set_entry(self._current_entry)
            
            # データベース参照を更新（対応するメソッドがある場合）
            if hasattr(dialog.widget, "set_database") and self._database:
                dialog.widget.set_database(self._database)
        
        # ダイアログを表示
        dialog.show()
        dialog.raise_()  # 前面に表示
        dialog.activateWindow()  # ウィンドウをアクティブにする

    def _update_open_review_dialogs(self) -> None:
        """開いているすべてのレビューダイアログを更新"""
        if not self._current_entry:
            return
            
        for dialog_type, dialog in self._review_dialogs.items():
            if dialog.isVisible() and hasattr(dialog.widget, "set_entry"):
                # ダイアログが表示中の場合のみ更新
                dialog.widget.set_entry(self._current_entry)

    @property
    def current_entry(self) -> Optional[EntryModel]:
        """現在のエントリを取得"""
        return self._current_entry

    @property
    def current_entry_number(self) -> Optional[int]:
        """現在のエントリ番号を取得"""
        if not self._current_entry:
            return None

        # MainWindowを取得
        main_window = self.parent()
        while main_window and not hasattr(main_window, "_display_entries"):
            main_window = main_window.parent()

        if not main_window or not hasattr(main_window, "_display_entries"):
            return None

        # 現在のエントリのインデックスを取得
        try:
            entries = getattr(main_window, "_display_entries", [])
            if not entries:
                return None
            return entries.index(self._current_entry.key)
        except (ValueError, AttributeError):
            return None

    def _on_apply_clicked(self) -> None:
        """適用ボタンクリック時の処理"""
        if not self.current_entry or not self._database:
            return

        # エントリを更新
        entry = self.current_entry
        
        # データベースの更新
        self._database.update_entry(entry.key, entry.to_dict())
        
        self.text_changed.emit()
        self.apply_clicked.emit()

    def _on_text_changed(self) -> None:
        """テキストが変更されたときの処理"""
        # 頻繁な通知を避けるため、タイマーをリセットして一定時間後に通知
        self._text_change_timer.stop()
        self._text_change_timer.start(5)

    def _on_msgstr_changed(self) -> None:
        """翻訳文が変更されたときの処理"""
        if not self._current_entry:
            return
            
        # エントリのmsgstrを更新
        new_msgstr = self.msgstr_edit.toPlainText()
        self._current_entry.msgstr = new_msgstr
        
        # 変更通知タイマーをリセット
        self._text_change_timer.start(200)

    def _emit_text_changed(self) -> None:
        """テキスト変更シグナルを発行"""
        if not self._current_entry:
            return

        # エントリオブジェクトを更新（ただしデータベースには書き込まない）
        if self.msgstr_edit:
            self._current_entry.msgstr = self.msgstr_edit.toPlainText()
        if self.context_edit:
            self._current_entry.msgctxt = self.context_edit.text() or None

        self.text_changed.emit()

    def _on_fuzzy_changed(self, state: int) -> None:
        """Fuzzyチェックボックスの状態が変更されたときの処理"""
        if not self.fuzzy_checkbox or not self._current_entry or not self._database:
            return
            
        is_fuzzy = state == Qt.CheckState.Checked
        # エントリオブジェクトを更新
        self._current_entry.fuzzy = is_fuzzy
        
        # データベースに即時反映
        self._database.update_entry_field(self._current_entry.key, "fuzzy", is_fuzzy)
        
        self.text_changed.emit()

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定"""
        self._current_entry = entry
        if entry is None:
            logger.debug("set_entry: entry is None")
            if self.msgid_edit:
                self.msgid_edit.blockSignals(True)
                self.msgid_edit.setPlainText("")
                self.msgid_edit.blockSignals(False)
            if self.msgstr_edit:
                self.msgstr_edit.blockSignals(True)
                self.msgstr_edit.setPlainText("")
                self.msgstr_edit.blockSignals(False)
            if self.fuzzy_checkbox:
                self.fuzzy_checkbox.blockSignals(True)
                self.fuzzy_checkbox.setChecked(False)
                self.fuzzy_checkbox.blockSignals(False)
            if self.context_edit:
                self.context_edit.setText("")
            
            # 開いているダイアログがあれば更新
            self._update_open_review_dialogs()
            
            self.setEnabled(False)
            return

        logger.debug("set_entry: entry.msgctxt='%s'", entry.msgctxt)
        self.setEnabled(True)
        if self.msgid_edit:
            self.msgid_edit.blockSignals(True)
            self.msgid_edit.setPlainText(entry.msgid or "")
            self.msgid_edit.blockSignals(False)
        if self.msgstr_edit:
            self.msgstr_edit.blockSignals(True)
            self.msgstr_edit.setPlainText(entry.msgstr or "")
            self.msgstr_edit.blockSignals(False)
        if self.fuzzy_checkbox:
            self.fuzzy_checkbox.blockSignals(True)
            self.fuzzy_checkbox.setChecked(entry.fuzzy)
            self.fuzzy_checkbox.blockSignals(False)
        if self.context_edit:
            context_text = entry.msgctxt if entry.msgctxt is not None else ""
            logger.debug("set_entry: setting context_edit.text to '%s'", context_text)
            self.context_edit.setText(context_text)
            
        # 開いているダイアログがあれば更新
        self._update_open_review_dialogs()
        
        self.entry_changed.emit(self.current_entry_number or -1)

    @property
    def database(self) -> Optional[Database]:
        """データベース参照を取得"""
        return self._database
        
    @database.setter
    def database(self, db: Database) -> None:
        """データベース参照を設定"""
        self._database = db
        
        # 開いているダイアログがある場合は、それらにもデータベース参照を設定
        for dialog_type, dialog in self._review_dialogs.items():
            if hasattr(dialog.widget, "set_database"):
                dialog.widget.set_database(db)
        
    def get_layout_type(self) -> LayoutType:
        """現在のレイアウトタイプを取得"""
        return self._current_layout

    def set_layout_type(self, layout_type: LayoutType) -> None:
        """レイアウトタイプを設定"""
        if self._current_layout == layout_type:
            return

        # 現在の値を保存
        current_msgid = self.msgid_edit.toPlainText() if self.msgid_edit else ""
        current_msgstr = self.msgstr_edit.toPlainText() if self.msgstr_edit else ""
        current_context = self.context_edit.text() if self.context_edit else ""
        current_fuzzy = self.fuzzy_checkbox.isChecked() if self.fuzzy_checkbox else False

        self._current_layout = layout_type
        
        # 現在のレイアウトをクリア
        while self.editor_layout.count():
            item = self.editor_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if layout_type == LayoutType.LAYOUT1:
            # msgctxt上部、msgid/msgstr下部横並び
            self.editor_layout.addWidget(self.msgid_edit)
            self.editor_layout.addWidget(self.msgstr_edit)
        else:
            # 左右分割
            self.editor_layout.addWidget(self.msgid_edit)
            self.editor_layout.addWidget(self.msgstr_edit)

        # 値を復元
        if self.msgid_edit:
            self.msgid_edit.setPlainText(current_msgid)
        if self.msgstr_edit:
            self.msgstr_edit.setPlainText(current_msgstr)
        if self.context_edit:
            self.context_edit.setText(current_context)
        if self.fuzzy_checkbox:
            self.fuzzy_checkbox.setChecked(current_fuzzy)

    def sizeHint(self) -> QSize:
        # デフォルトの幅はスーパークラスのサイズヒントから取得し、高さは 300px に設定（レビューウィジェット用に拡大）
        return QSize(super().sizeHint().width(), 300)
