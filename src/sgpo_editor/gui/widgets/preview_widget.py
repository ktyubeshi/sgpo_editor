"""プレビューウィジェット

このモジュールは、エントリのプレビュー表示機能を提供します。
エスケープシーケンスやHTMLタグを適切に表示します。
"""

import logging
import re
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
                               QPushButton, QTextBrowser, QVBoxLayout, QWidget)

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

        Args:
            text: 処理対象のテキスト

        Returns:
            処理後のテキスト
        """
        if not text:
            return ""

        # デバッグ用に入力テキストをログ出力
        logger.debug(f"Processing escape sequences in: {repr(text)}")

        # HTMLタグを一時的に置き換える（処理から保護するため）
        html_tags = {}
        tag_pattern = r"<[^>]+>"

        def save_tag(match):
            tag = match.group(0)
            key = f"__HTML_TAG_{len(html_tags)}__"
            html_tags[key] = tag
            return key

        # HTMLタグを一時的に置き換え
        text_without_tags = re.sub(tag_pattern, save_tag, text)
        logger.debug(
            f"Text with HTML tags replaced: {
                repr(text_without_tags)}"
        )

        # 基本的なエスケープシーケンスを処理
        basic_escapes = {
            "\\n": "\n",  # 改行
            "\\r": "\r",  # キャリッジリターン
            "\\t": "\t",  # タブ
            '\\"': '"',  # ダブルクォート
            "\\'": "'",  # シングルクォート
        }

        # HTMLエンティティを処理
        html_entities = {
            "&lt;": "<",  # 小なり
            "&gt;": ">",  # 大なり
            "&amp;": "&",  # アンパサンド
            "&quot;": '"',  # ダブルクォート
            "&apos;": "'",  # シングルクォート
            "&nbsp;": " ",  # 空白
        }

        processed = text_without_tags

        # まず二重バックスラッシュを処理（\\）
        processed = processed.replace("\\\\", "\\")
        logger.debug(f"After processing double backslashes: {repr(processed)}")

        # 次に基本的なエスケープシーケンスを処理
        for escape_seq, replacement in basic_escapes.items():
            if escape_seq in processed:
                logger.debug(
                    f"Replacing {
                        repr(escape_seq)} with {
                        repr(replacement)}"
                )
                processed = processed.replace(escape_seq, replacement)

        # 正規表現のエスケープシーケンスを処理
        # これらは実際の文字に変換する（表示用途なので）
        regex_escapes = {
            "\\d": "d",  # 数字
            "\\w": "w",  # 単語文字
            "\\s": "s",  # 空白文字
            "\\+": "+",  # 1回以上の繰り返し
            "\\*": "*",  # 0回以上の繰り返し
            "\\.": ".",  # 任意の1文字
            "\\?": "?",  # 0回または1回の繰り返し
            "\\(": "(",  # 開き括弧
            "\\)": ")",  # 閉じ括弧
            "\\[": "[",  # 文字クラスの開始
            "\\]": "]",  # 文字クラスの終了
            "\\{": "{",  # 繰り返し回数の開始
            "\\}": "}",  # 繰り返し回数の終了
            "\\|": "|",  # 選択
            "\\^": "^",  # 行の先頭
            "\\$": "$",  # 行の末尾
        }

        for escape_seq, replacement in regex_escapes.items():
            if escape_seq in processed:
                logger.debug(
                    f"Replacing regex escape {
                        repr(escape_seq)} with {
                        repr(replacement)}"
                )
                processed = processed.replace(escape_seq, replacement)

        # HTMLエンティティを処理
        for entity, replacement in html_entities.items():
            if entity in processed:
                logger.debug(
                    f"Replacing HTML entity {
                        repr(entity)} with {
                        repr(replacement)}"
                )
                processed = processed.replace(entity, replacement)

        # HTMLタグを元に戻す
        for key, tag in html_tags.items():
            processed = processed.replace(key, tag)

        logger.debug(f"After processing escapes: {repr(processed)}")

        return processed

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

    def set_event_handler(self, event_handler) -> None:
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
        """ダイアログが閉じられるときの処理

        Args:
            event: クローズイベント
        """
        # イベントハンドラーからの接続を解除
        if self._event_handler and hasattr(self._event_handler, "entry_updated"):
            self._event_handler.entry_updated.disconnect(self._on_entry_updated)
        super().closeEvent(event)
