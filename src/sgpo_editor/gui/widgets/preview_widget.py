"""プレビューウィジェット

このモジュールは、エントリのプレビュー表示機能を提供します。
エスケープシーケンスやHTMLタグを適切に表示します。
"""

import logging
import re
import html
from typing import Optional, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from sgpo_editor.models import EntryModel

logger = logging.getLogger(__name__)


class PreviewWidget(QWidget):
    """エントリプレビューウィジェット"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry: Optional[EntryModel] = None
        self._preview_mode = "all"  # 'all', 'escape', 'html'

        # レイアウト設定
        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIの設定"""
        main_layout = QVBoxLayout(self)

        # プレビューモード選択
        mode_layout = QHBoxLayout()
        mode_label = QLabel("プレビューモード:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("すべて適用", "all")
        self.mode_combo.addItem("エスケープシーケンスのみ", "escape")
        self.mode_combo.addItem("HTMLタグのみ", "html")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)

        # 翻訳前の原文表示
        self.source_label = QLabel("翻訳前の原文:")
        main_layout.addWidget(self.source_label)

        self.source_text = QTextBrowser()
        self.source_text.setReadOnly(True)
        self.source_text.setFont(QFont("Courier", 10))
        self.source_text.setMaximumHeight(100)  # 高さを制限
        main_layout.addWidget(self.source_text)

        # 元のテキスト表示
        self.original_label = QLabel("元のテキスト:")
        main_layout.addWidget(self.original_label)

        self.original_text = QTextBrowser()
        self.original_text.setReadOnly(True)
        self.original_text.setFont(QFont("Courier", 10))
        main_layout.addWidget(self.original_text)

        # プレビュー表示
        self.preview_label = QLabel("プレビュー:")
        main_layout.addWidget(self.preview_label)

        self.preview_text = QTextBrowser()
        self.preview_text.setReadOnly(True)
        self.preview_text.setOpenExternalLinks(False)
        main_layout.addWidget(self.preview_text)

    def _on_mode_changed(self, index: int) -> None:
        """プレビューモードが変更されたときの処理"""
        self._preview_mode = self.mode_combo.currentData()
        self._update_preview()

    def _process_escape_sequences(self, text: str) -> str:
        """エスケープシーケンスを処理する

        標準的なPython文字列のエスケープシーケンスとHTML実体参照を解決します。

        Args:
            text: 処理対象のテキスト

        Returns:
            処理後のテキスト
        """
        if not text:
            return ""

        # デバッグ用に入力テキストをログ出力
        logger.debug(f"Processing escape sequences in: {repr(text)}")

        # HTMLエンティティをデコード
        text = html.unescape(text)
        logger.debug(f"After HTML unescape: {repr(text)}")
        
        # Pythonのエスケープシーケンスを処理するための関数
        def replace_escapes(match):
            escape_seq = match.group(0)
            # 一般的なエスケープシーケンスを処理
            escape_map = {
                "\\n": "\n",   # 改行
                "\\r": "\r",   # キャリッジリターン
                "\\t": "\t",   # タブ
                '\\"': '"',    # ダブルクォート
                "\\'": "'",    # シングルクォート
                "\\\\": "\\",  # バックスラッシュ
                "\\a": "\a",   # ベル
                "\\b": "\b",   # バックスペース
                "\\f": "\f",   # フォームフィード
                "\\v": "\v"    # 垂直タブ
            }
            
            # 正規表現のエスケープシーケンスを処理
            regex_escape_chars = "dwsDS+*?.()[]{}|^$"
            if len(escape_seq) == 2 and escape_seq[0] == "\\" and escape_seq[1] in regex_escape_chars:
                return escape_seq[1]
                
            # マップに定義されたエスケープシーケンスを置換
            return escape_map.get(escape_seq, escape_seq)
            
        # 正規表現でエスケープシーケンスを検出して置換
        processed_text = re.sub(r'\\[nrtabfv"\'\\]|\\[dwsDS+*?.()\[\]{}|^$]', replace_escapes, text)
        
        # 16進数エスケープシーケンス (\xHH) の処理
        processed_text = re.sub(r'\\x([0-9a-fA-F]{2})', 
                              lambda m: chr(int(m.group(1), 16)), 
                              processed_text)
        
        # Unicodeエスケープシーケンス (\uHHHH) の処理
        processed_text = re.sub(r'\\u([0-9a-fA-F]{4})', 
                              lambda m: chr(int(m.group(1), 16)), 
                              processed_text)
        
        logger.debug(f"After processing escapes: {repr(processed_text)}")
        return processed_text

    def _process_html_tags(self, text: str) -> str:
        """HTMLタグを処理する

        Args:
            text: 処理対象のテキスト

        Returns:
            処理後のテキスト
        """
        if not text:
            return ""

        # HTMLタグをそのまま表示するためにエスケープ
        processed = text

        # ただし、一部の基本的なHTMLタグは解釈する
        # この例では、<b>, <i>, <u>, <br> タグを解釈する

        return processed

    def _update_preview(self) -> None:
        """プレビューを更新する"""
        if not self._current_entry:
            self.source_text.setPlainText("")
            self.original_text.setPlainText("")
            self.preview_text.setPlainText("")
            return

        # 翻訳前の原文を表示
        source_text = self._current_entry.msgid or ""
        self.source_text.setPlainText(source_text)

        # 元のテキストを表示
        original_text = self._current_entry.msgstr or ""
        self.original_text.setPlainText(original_text)

        # デバッグ用にログ出力
        logger.debug(f"Source text: {repr(source_text)}")
        logger.debug(f"Original text: {repr(original_text)}")
        logger.debug(f"Preview mode: {self._preview_mode}")

        # プレビューモードに応じて処理
        processed_text = original_text

        # エスケープシーケンスの処理
        if self._preview_mode in ["all", "escape"]:
            processed_text = self._process_escape_sequences(processed_text)
            logger.debug(f"After escape processing: {repr(processed_text)}")

        # HTMLタグの処理
        if self._preview_mode in ["all", "html"]:
            processed_text = self._process_html_tags(processed_text)
            logger.debug(f"After HTML processing: {repr(processed_text)}")

        # プレビューを表示
        if self._preview_mode in ["all", "escape"]:
            # エスケープ処理後のテキストをHTML形式で表示するための処理
            html_text = ""
            for char in processed_text:
                if char == "\n":
                    html_text += "<br>"
                elif char == "\t":
                    html_text += "&nbsp;&nbsp;&nbsp;&nbsp;"
                elif char == " ":
                    html_text += "&nbsp;"
                elif char == "<":
                    html_text += "&lt;"
                elif char == ">":
                    html_text += "&gt;"
                elif char == "&":
                    html_text += "&amp;"
                else:
                    html_text += char

            logger.debug(f"HTML text for display: {repr(html_text)}")

            # HTMLとして表示
            self.preview_text.setHtml(html_text)
        else:
            # エスケープ処理をしない場合はプレーンテキストとして表示
            self.preview_text.setPlainText(processed_text)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定

        Args:
            entry: 設定するエントリ
        """
        self._current_entry = entry
        self._update_preview()


class PreviewDialog(QDialog):
    """プレビューダイアログ"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self.setWindowTitle("プレビュー")
        self.resize(600, 400)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # イベントハンドラーへの参照（後で設定）
        self._event_handler = None

        # レイアウト設定
        layout = QVBoxLayout(self)

        # プレビューウィジェット
        self.preview_widget = PreviewWidget(self)
        layout.addWidget(self.preview_widget)

        # 閉じるボタン
        button_layout = QHBoxLayout()
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.close)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

    def set_event_handler(self, event_handler: Any) -> None:
        """イベントハンドラーを設定し、エントリ選択変更イベントを接続する

        Args:
            event_handler: イベントハンドラー
        """
        self._event_handler = event_handler

        # エントリ選択変更イベントを接続
        if hasattr(event_handler, "entry_updated"):
            event_handler.entry_updated.connect(self._on_entry_updated)

    def _on_entry_updated(self, position: int) -> None:
        """エントリが更新されたときの処理

        Args:
            position: 更新されたエントリの位置
        """
        if self._event_handler:
            current_entry = self._event_handler.get_current_entry()
            self.set_entry(current_entry)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定

        Args:
            entry: 設定するエントリ
        """
        self.preview_widget.set_entry(entry)
        
    def closeEvent(self, event) -> None:
        """ウィンドウが閉じられるときのイベント処理"""
        # 親ウィンドウの参照を削除
        parent = self.parent()
        if parent and hasattr(parent, "_preview_dialog"):
            parent._preview_dialog = None
        event.accept()
