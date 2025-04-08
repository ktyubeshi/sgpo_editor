#!/usr/bin/env python
"""POフォーマットエディタウィジェット"""

import logging
import re
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
)

from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class POSyntaxHighlighter(QSyntaxHighlighter):
    """POファイル形式の構文ハイライト"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._formats = {}
        self._setup_formats()

    def _setup_formats(self):
        """フォーマットの設定"""
        # msgid用のフォーマット (青)
        msgid_format = QTextCharFormat()
        msgid_format.setForeground(QColor(0, 0, 200))
        msgid_format.setFontWeight(QFont.Bold)
        self._formats["msgid"] = msgid_format

        # msgstr用のフォーマット (緑)
        msgstr_format = QTextCharFormat()
        msgstr_format.setForeground(QColor(0, 150, 0))
        msgstr_format.setFontWeight(QFont.Bold)
        self._formats["msgstr"] = msgstr_format

        # msgctxt用のフォーマット (紫)
        msgctxt_format = QTextCharFormat()
        msgctxt_format.setForeground(QColor(150, 0, 150))
        msgctxt_format.setFontWeight(QFont.Bold)
        self._formats["msgctxt"] = msgctxt_format

        # コメント用のフォーマット (灰色)
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(100, 100, 100))
        self._formats["comment"] = comment_format

        # 文字列用のフォーマット
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(200, 100, 0))
        self._formats["string"] = string_format

    def highlightBlock(self, text: str):
        """テキストブロックのハイライト処理"""
        # msgid, msgstr, msgctxtのハイライト
        for keyword in ["msgid", "msgstr", "msgctxt"]:
            pattern = f"^{keyword}\\s+"
            for match in re.finditer(pattern, text):
                self.setFormat(
                    match.start(), match.end() - match.start(), self._formats[keyword]
                )

        # コメントのハイライト
        if text.startswith("#"):
            self.setFormat(0, len(text), self._formats["comment"])

        # 文字列のハイライト (引用符で囲まれた部分)
        for match in re.finditer(r'"(.*?)"', text):
            self.setFormat(
                match.start(), match.end() - match.start(), self._formats["string"]
            )


class POFormatEditor(QDialog):
    """POフォーマットエディタダイアログ"""

    entry_updated = Signal(str, str)  # key, msgstr

    def __init__(self, parent=None, get_current_po=None):
        """初期化

        Args:
            parent: 親ウィジェット
            get_current_po: 現在のPOファイルを取得するコールバック
        """
        super().__init__(parent)
        self.setWindowTitle("POフォーマットエディタ")
        self.resize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self._get_current_po = get_current_po
        self._entry_map = {}  # キーとEntryModelのマッピング
        self._setup_ui()

    def _setup_ui(self):
        """UIの初期化"""
        layout = QVBoxLayout(self)

        # 説明ラベル
        info_label = QLabel(
            "POファイルのエントリと同じフォーマットでエントリを確認・編集できます。\n"
            "LLMのチャットウィンドウに投げるなどの操作に便利です。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # スプリッター
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter, 1)

        # エディタ
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.setLineWrapMode(QTextEdit.NoWrap)
        font = QFont("Monospace", 10)
        font.setFixedPitch(True)
        self.editor.setFont(font)

        # 構文ハイライト
        self.highlighter = POSyntaxHighlighter(self.editor.document())

        # プレビュー
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(font)

        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([400, 200])

        # ボタンレイアウト
        button_layout = QHBoxLayout()

        # 現在のエントリを取得ボタン
        self.get_current_button = QPushButton("現在のエントリを取得")
        self.get_current_button.clicked.connect(self._on_get_current_clicked)
        button_layout.addWidget(self.get_current_button)

        # すべてのエントリを取得ボタン
        self.get_all_button = QPushButton("すべてのエントリを取得")
        self.get_all_button.clicked.connect(self._on_get_all_clicked)
        button_layout.addWidget(self.get_all_button)

        # フィルタされたエントリを取得ボタン
        self.get_filtered_button = QPushButton("フィルタされたエントリを取得")
        self.get_filtered_button.clicked.connect(self._on_get_filtered_clicked)
        button_layout.addWidget(self.get_filtered_button)

        # プレビューボタン
        self.preview_button = QPushButton("プレビュー")
        self.preview_button.clicked.connect(self._on_preview_clicked)
        button_layout.addWidget(self.preview_button)

        # 適用ボタン
        self.apply_button = QPushButton("適用")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        button_layout.addWidget(self.apply_button)

        layout.addLayout(button_layout)

        # ダイアログボタン
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # エディタの内容が変更されたときのシグナル接続
        self.editor.textChanged.connect(self._on_text_changed)

    def _on_get_current_clicked(self):
        """現在のエントリを取得"""
        if not self._get_current_po:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        po_file = self._get_current_po()
        if not po_file:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        # 親ウィンドウからテーブルを取得
        if hasattr(self.parent(), "table"):
            table = self.parent().table
            # 現在選択されている行を取得
            current_row = table.currentRow()
            if current_row >= 0:
                # 選択された行のキーを取得
                item = table.item(current_row, 0)
                if item:
                    key = item.data(Qt.ItemDataRole.UserRole)
                    # キーからエントリを取得
                    current_entry = po_file.get_entry_by_key(key)
                    if current_entry:
                        # エントリをPO形式に変換してエディタに表示
                        self._set_entries([current_entry])
                        return

        QMessageBox.warning(self, "エラー", "現在選択されているエントリがありません")

    def _on_get_all_clicked(self):
        """すべてのエントリを取得"""
        if not self._get_current_po:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        po_file = self._get_current_po()
        if not po_file:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        # すべてのエントリを取得
        entries = po_file.get_filtered_entries()
        if not entries:
            QMessageBox.warning(self, "エラー", "エントリがありません")
            return

        # エントリをPO形式に変換してエディタに表示
        self._set_entries(entries)

    def _on_get_filtered_clicked(self):
        """フィルタされたエントリを取得"""
        if not self._get_current_po:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        po_file = self._get_current_po()
        if not po_file:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        # メインウィンドウからフィルタ条件を取得
        main_window = None
        parent = self.parent()
        while parent:
            if hasattr(parent, "search_widget") and hasattr(parent, "table_manager"):
                main_window = parent
                break
            parent = parent.parent()

        filter_text = None
        filter_keyword = None

        if main_window and hasattr(main_window, "search_widget"):
            # SearchWidgetからフィルタ条件を取得
            criteria = main_window.search_widget.get_search_criteria()
            filter_text = criteria.filter
            filter_keyword = criteria.filter_keyword

        # フィルタされたエントリを取得
        entries = po_file.get_filtered_entries(
            update_filter=True, 
            filter_keyword=filter_keyword
        )

        if not entries:
            QMessageBox.warning(self, "エラー", "フィルタされたエントリがありません")
            return

        # エントリをPO形式に変換してエディタに表示
        self._set_entries(entries)

    def _set_entries(self, entries: List[EntryModel]):
        """エントリをPO形式に変換してエディタに表示

        Args:
            entries: エントリのリスト
        """
        self._entry_map = {}  # マッピングをリセット
        po_text = ""

        for entry in entries:
            # エントリをPO形式に変換
            entry_text = self._entry_to_po_format(entry)
            po_text += entry_text + "\n\n"

            # キーとエントリのマッピングを保存
            self._entry_map[entry.key] = entry

        # エディタに表示
        self.editor.setPlainText(po_text)

        # プレビューも更新
        self._update_preview()

    def _entry_to_po_format(self, entry: EntryModel) -> str:
        """エントリをPO形式に変換

        Args:
            entry: 変換するエントリ

        Returns:
            str: PO形式の文字列
        """
        lines = []

        # コメント
        if entry.comment:
            lines.append(f"# {entry.comment}")

        # 翻訳者コメント
        if entry.tcomment:
            lines.append(f"#. {entry.tcomment}")

        # 参照
        if entry.occurrences:
            for src, line in entry.occurrences:
                lines.append(f"#: {src}:{line}")

        # フラグ
        if entry.flags:
            lines.append(f"#, {', '.join(entry.flags)}")

        # 以前のmsgctxt
        if entry.previous_msgctxt:
            lines.append(f'#| msgctxt "{entry.previous_msgctxt}"')

        # 以前のmsgid
        if entry.previous_msgid:
            lines.append(f'#| msgid "{entry.previous_msgid}"')

        # msgctxt
        if entry.msgctxt:
            lines.append(f'msgctxt "{entry.msgctxt}"')

        # msgid
        lines.append(f'msgid "{entry.msgid}"')

        # msgstr
        lines.append(f'msgstr "{entry.msgstr}"')

        return "\n".join(lines)

    def _on_preview_clicked(self):
        """プレビューボタンがクリックされたときの処理"""
        self._update_preview()

    def _update_preview(self):
        """プレビューを更新"""
        try:
            # エディタのテキストを解析
            entries = self._parse_po_format(self.editor.toPlainText())

            # プレビューテキスト
            preview_text = ""
            for i, (key, msgid, msgstr, msgctxt) in enumerate(entries):
                if i > 0:
                    preview_text += "\n\n"

                preview_text += f"エントリ {i + 1}:\n"
                if msgctxt:
                    preview_text += f"コンテキスト: {msgctxt}\n"
                preview_text += f"原文: {msgid}\n"
                preview_text += f"訳文: {msgstr}"

            self.preview.setPlainText(preview_text)

        except Exception as e:
            logger.exception("プレビュー更新中にエラーが発生しました")
            self.preview.setPlainText(f"エラー: {str(e)}")

    def _on_text_changed(self):
        """エディタのテキストが変更されたときの処理"""
        # 自動的にプレビューを更新
        self._update_preview()

    def _on_apply_clicked(self):
        """適用ボタンがクリックされたときの処理"""
        if not self._get_current_po:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        po_file = self._get_current_po()
        if not po_file:
            QMessageBox.warning(self, "エラー", "POファイルが読み込まれていません")
            return

        try:
            # エディタのテキストを解析
            entries = self._parse_po_format(self.editor.toPlainText())
            logger.debug(f"POFormatEditor._on_apply_clicked: {len(entries)}個のエントリを解析しました")

            # 更新されたエントリの数
            updated_count = 0
            not_found_count = 0

            # 各エントリを処理
            for key, msgid, msgstr, msgctxt in entries:
                # キーの生成
                if msgctxt:
                    entry_key = f"{msgctxt}\x04{msgid}"
                else:
                    entry_key = f"|{msgid}"  # 標準形式のキーを使用

                logger.debug(f"POFormatEditor._on_apply_clicked: エントリ処理 key={entry_key}, msgid={msgid}")

                # エントリを検索（正確なキーで検索）
                entry = po_file.get_entry_by_key(entry_key)
                
                # それでも見つからない場合は、フィルタリングで検索
                if not entry:
                    logger.debug(f"POFormatEditor._on_apply_clicked: キーで見つからないため、フィルタリングで検索 msgid={msgid}")
                    try:
                        # フィルタを使って効率的に検索（キャッシュを強制的に更新）
                        filtered_entries = po_file.get_filtered_entries(
                            update_filter=True,  # キャッシュを強制更新
                            filter_keyword=msgid   # msgidで検索
                        )
                        
                        for e in filtered_entries:
                            # msgidが完全一致かつmsgctxtも一致（またはともにNone）する場合
                            e_msgctxt = getattr(e, "msgctxt", None)
                            if e.msgid == msgid and ((e_msgctxt is None and msgctxt is None) or e_msgctxt == msgctxt):
                                entry = e
                                logger.debug(f"POFormatEditor._on_apply_clicked: エントリを絞り込み検索で発見: key={e.key}, msgid={msgid}")
                                break
                    except Exception as filter_error:
                        logger.exception(f"POFormatEditor._on_apply_clicked: フィルタリング検索中にエラー: {filter_error}")

                if entry:
                    # エントリが見つかった場合は更新
                    if entry.msgstr != msgstr:
                        # エントリのmsgstrを更新
                        old_msgstr = entry.msgstr
                        entry.msgstr = msgstr
                        logger.debug(f"POFormatEditor._on_apply_clicked: エントリ更新開始: key={entry.key}, msgid={entry.msgid}")
                        
                        # トランザクション内で更新を行う
                        try:
                            # 更新されたエントリを保存
                            update_success = po_file.update_entry(entry)
                            if update_success:
                                updated_count += 1
                                # 更新シグナルを発行
                                self.entry_updated.emit(entry.key, msgstr)
                                logger.debug(f"POFormatEditor._on_apply_clicked: エントリ更新成功: key={entry.key}")
                            else:
                                # 更新に失敗した場合は元の値に戻す
                                entry.msgstr = old_msgstr
                                logger.error(f"POFormatEditor._on_apply_clicked: エントリ更新失敗: key={entry.key}")
                                not_found_count += 1
                        except Exception as update_error:
                            # 例外発生時も元の値に戻す
                            entry.msgstr = old_msgstr
                            logger.exception(f"POFormatEditor._on_apply_clicked: エントリ更新中に例外発生: {update_error}")
                            not_found_count += 1
                    else:
                        logger.debug(f"POFormatEditor._on_apply_clicked: エントリの訳文に変更なし: key={entry.key}")
                else:
                    logger.warning(f"POFormatEditor._on_apply_clicked: エントリが見つかりませんでした: msgid={msgid}, msgctxt={msgctxt}")
                    not_found_count += 1

            # 結果を表示
            if not_found_count > 0:
                QMessageBox.warning(
                    self,
                    "警告",
                    f"{updated_count}個のエントリを更新しました。\n"
                    f"{not_found_count}個のエントリが見つかりませんでした。",
                )
            else:
                QMessageBox.information(
                    self, "成功", f"{updated_count}個のエントリを更新しました。"
                )

        except Exception as e:
            logger.exception("POFormatEditor._on_apply_clicked: エントリ適用中にエラーが発生しました")
            QMessageBox.critical(
                self, "エラー", f"エントリの適用に失敗しました: {str(e)}"
            )

    def _parse_po_format(self, text: str) -> List[Tuple[str, str, str, Optional[str]]]:
        """PO形式のテキストを解析

        Args:
            text: PO形式のテキスト

        Returns:
            List[Tuple[str, str, str, Optional[str]]]: (key, msgid, msgstr, msgctxt)のリスト
        """
        entries = []

        # エントリごとに分割
        entry_texts = re.split(r"\n\s*\n", text)

        for entry_text in entry_texts:
            if not entry_text.strip():
                continue

            # 現在のエントリのコンテキスト
            current_context = {"msgid": "", "msgstr": "", "msgctxt": None}

            # 行ごとに処理
            lines = entry_text.split("\n")
            current_key = None

            for i, line in enumerate(lines):
                line = line.strip()

                # コメント行はスキップ
                if line.startswith("#"):
                    continue

                # msgid、msgstr、msgctxtの行を処理
                if line.startswith("msgid "):
                    current_key = "msgid"
                    value = self._extract_quoted_string(line[6:])
                    current_context[current_key] = value
                elif line.startswith("msgstr "):
                    current_key = "msgstr"
                    value = self._extract_quoted_string(line[7:])
                    current_context[current_key] = value
                elif line.startswith("msgctxt "):
                    current_key = "msgctxt"
                    value = self._extract_quoted_string(line[8:])
                    current_context[current_key] = value
                # 継続行（引用符で始まる行）を処理
                elif line.startswith('"') and current_key:
                    value = self._extract_quoted_string(line)
                    current_context[current_key] += value

            # msgidとmsgstrが存在する場合のみエントリとして追加
            if current_context["msgid"] and "msgstr" in current_context:
                msgid = current_context["msgid"]
                msgstr = current_context["msgstr"]
                msgctxt = current_context["msgctxt"]

                # キーの生成（_on_apply_clickedと同じ形式を使用）
                if msgctxt:
                    key = f"{msgctxt}\x04{msgid}"
                else:
                    key = f"|{msgid}"

                entries.append((key, msgid, msgstr, msgctxt))

        return entries

    def _extract_quoted_string(self, text: str) -> str:
        """引用符で囲まれた文字列を抽出し、エスケープシーケンスを処理する

        Args:
            text: 引用符を含む文字列

        Returns:
            str: 引用符内の文字列（エスケープシーケンス処理済み）
        """
        # 最初と最後の引用符を取り除く
        match = re.match(r'"(.*?)"', text)
        if not match:
            return ""

        content = match.group(1)

        # POファイル形式のエスケープシーケンスを処理
        content = content.replace('\\"', '"')  # ダブルクォートのエスケープを解除
        content = content.replace("\\n", "\n")  # 改行のエスケープを解除
        content = content.replace("\\t", "\t")  # タブのエスケープを解除
        content = content.replace("\\\\", "\\")  # バックスラッシュのエスケープを解除

        return content
