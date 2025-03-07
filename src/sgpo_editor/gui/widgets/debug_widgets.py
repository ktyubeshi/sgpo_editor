"""デバッグ用ウィジェット

エントリの詳細情報を表示するためのデバッグウィジェットを提供します。
"""
import json
from typing import Optional, Dict, Any, List, Union

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QSplitter
)
from PySide6.QtCore import Qt, Signal

from sgpo_editor.models.entry import EntryModel


class EntryDebugWidget(QWidget):
    """エントリのデバッグ情報を表示するウィジェット"""

    # 更新シグナル
    refresh_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self._entry: Optional[EntryModel] = None
        self._init_ui()

    def _init_ui(self) -> None:
        """UIの初期化"""
        layout = QVBoxLayout(self)
        
        # タイトルラベル
        title_label = QLabel("エントリデバッグ情報")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # デバッグテキスト表示エリア
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setFont(self._get_monospace_font())
        layout.addWidget(self.debug_text)
        
        # ボタンエリア
        button_layout = QHBoxLayout()
        
        # 更新ボタン
        refresh_button = QPushButton("更新")
        refresh_button.clicked.connect(self._on_refresh_clicked)
        button_layout.addWidget(refresh_button)
        
        # コピーボタン
        copy_button = QPushButton("コピー")
        copy_button.clicked.connect(self._on_copy_clicked)
        button_layout.addWidget(copy_button)
        
        # 展開/折りたたみボタン
        self.expand_button = QPushButton("すべて展開")
        self.expand_button.clicked.connect(self._on_expand_clicked)
        button_layout.addWidget(self.expand_button)
        
        layout.addLayout(button_layout)

    def _get_monospace_font(self):
        """等幅フォントを取得"""
        from PySide6.QtGui import QFont
        font = QFont("Consolas, Courier New, monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font
        
    def set_entry(self, entry: EntryModel) -> None:
        """エントリを設定し、表示を更新

        Args:
            entry: 表示するエントリ
        """
        self._entry = entry
        self._update_debug_display()
        
    def _update_debug_display(self) -> None:
        """デバッグ表示を更新"""
        if not self._entry:
            self.debug_text.setPlainText("エントリが設定されていません")
            return
        
        # エントリの辞書形式データを取得
        entry_dict = self._entry.to_dict()
        
        # 整形されたJSONで表示
        formatted_json = json.dumps(entry_dict, 
                                    ensure_ascii=False, 
                                    indent=2,
                                    default=str)
        
        self.debug_text.setPlainText(formatted_json)
    
    def _on_refresh_clicked(self) -> None:
        """更新ボタンがクリックされたときの処理"""
        self._update_debug_display()
        self.refresh_requested.emit()
        
    def _on_copy_clicked(self) -> None:
        """コピーボタンがクリックされたときの処理"""
        text = self.debug_text.toPlainText()
        clipboard = self.debug_text.clipboard()
        if clipboard:
            clipboard.setText(text)
            
    def _on_expand_clicked(self) -> None:
        """展開/折りたたみボタンがクリックされたときの処理"""
        current_text = self.expand_button.text()
        
        if current_text == "すべて展開":
            # JSONを解析して完全展開表示
            try:
                if self._entry:
                    entry_dict = self._entry.to_dict()
                    formatted_text = self._format_dict_as_text(entry_dict)
                    self.debug_text.setPlainText(formatted_text)
                    self.expand_button.setText("JSON表示")
            except Exception as e:
                self.debug_text.setPlainText(f"エラー: {str(e)}")
        else:
            # 通常のJSON表示に戻す
            self._update_debug_display()
            self.expand_button.setText("すべて展開")
            
    def _format_dict_as_text(self, data: Dict[str, Any], indent: int = 0) -> str:
        """辞書を階層的なテキスト形式にフォーマット
        
        Args:
            data: フォーマットする辞書
            indent: インデントレベル
            
        Returns:
            str: フォーマットされたテキスト
        """
        result = []
        indent_str = "  " * indent
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    result.append(f"{indent_str}{key}:")
                    result.append(self._format_dict_as_text(value, indent + 1))
                else:
                    result.append(f"{indent_str}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    result.append(f"{indent_str}[{i}]:")
                    result.append(self._format_dict_as_text(item, indent + 1))
                else:
                    result.append(f"{indent_str}[{i}]: {item}")
        else:
            result.append(f"{indent_str}{data}")
            
        return "\n".join(result)
