"""メタデータ編集ダイアログ"""

import json
import logging
from typing import Any, Dict, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QMessageBox,
    QMenu,
)

from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class MetadataValueEditor(QDialog):
    """複雑なメタデータ値を編集するためのダイアログ"""
    
    def __init__(self, value: Any, value_type: str, parent: Optional[QDialog] = None) -> None:
        """初期化

        Args:
            value: 編集する値
            value_type: 値の型
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.value = value
        self.value_type = value_type
        self.setWindowTitle(f"{value_type}の編集")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 編集用テキストエリア
        self.text_edit = QLineEdit()
        
        if value_type == "リスト" or value_type == "辞書":
            # JSON形式で表示
            self.text_edit.setText(json.dumps(value, ensure_ascii=False))
        else:
            self.text_edit.setText(str(value))
            
        layout.addWidget(self.text_edit)
        
        # ボタン
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        cancel_button = QPushButton("キャンセル")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def get_value(self) -> Any:
        """編集された値を返す

        Returns:
            編集された値
        """
        value_str = self.text_edit.text()
        
        try:
            if self.value_type == "文字列":
                return value_str
            elif self.value_type == "数値":
                if value_str.isdigit():
                    return int(value_str)
                try:
                    return float(value_str)
                except ValueError:
                    return 0
            elif self.value_type == "真偽値":
                return value_str.lower() in ("true", "yes", "1")
            elif self.value_type == "リスト" or self.value_type == "辞書":
                return json.loads(value_str)
            return value_str
        except Exception as e:
            QMessageBox.warning(self, "変換エラー", f"値の変換に失敗しました: {str(e)}")
            return self.value  # 元の値を返す


class MetadataEditDialog(QDialog):
    """メタデータ編集ダイアログ"""
    
    def __init__(self, entry: EntryModel, parent: Optional[QDialog] = None) -> None:
        """初期化

        Args:
            entry: 編集対象のエントリ
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle("メタデータ編集")
        self.resize(500, 400)
        
        # レイアウト設定
        self.setup_ui()
        
        # 既存のメタデータを表示
        self.load_metadata()
    
    def setup_ui(self) -> None:
        """UIコンポーネントの設定"""
        layout = QVBoxLayout(self)
        
        # 説明ラベル
        info_label = QLabel("エントリのメタデータを編集します。右クリックで追加のオプションがあります。")
        layout.addWidget(info_label)
        
        # メタデータテーブル
        self.metadata_table = QTableWidget(0, 2)
        self.metadata_table.setHorizontalHeaderLabels(["キー", "値"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.metadata_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.metadata_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.metadata_table)
        
        # 追加フォーム
        form_layout = QHBoxLayout()
        
        key_label = QLabel("キー:")
        form_layout.addWidget(key_label)
        
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("キー名を入力")
        form_layout.addWidget(self.key_edit)
        
        value_label = QLabel("値:")
        form_layout.addWidget(value_label)
        
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("値を入力")
        form_layout.addWidget(self.value_edit)
        
        type_label = QLabel("型:")
        form_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["文字列", "数値", "真偽値", "リスト", "辞書"])
        form_layout.addWidget(self.type_combo)
        
        add_button = QPushButton("追加")
        add_button.setObjectName("add_button")
        add_button.clicked.connect(self.add_metadata)
        form_layout.addWidget(add_button)
        
        layout.addLayout(form_layout)
        
        # ボタン
        button_layout = QHBoxLayout()
        save_button = QPushButton("保存")
        save_button.setObjectName("save_button")
        save_button.clicked.connect(self.save_metadata)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("キャンセル")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_metadata(self) -> None:
        """既存のメタデータをテーブルに読み込む"""
        # EntryModelクラスのmetadataプロパティを使用
        metadata = getattr(self.entry, 'metadata', {})
        self.metadata_table.setRowCount(len(metadata))
        
        for row, (key, value) in enumerate(metadata.items()):
            key_item = QTableWidgetItem(key)
            self.metadata_table.setItem(row, 0, key_item)
            
            # 値の型に応じた表示
            value_str = self.format_value_for_display(value)
            value_item = QTableWidgetItem(value_str)
            
            # 値の型を保存
            value_item.setData(Qt.ItemDataRole.UserRole, self.get_value_type(value))
            
            self.metadata_table.setItem(row, 1, value_item)
    
    def format_value_for_display(self, value: Any) -> str:
        """値を表示用にフォーマット

        Args:
            value: フォーマットする値

        Returns:
            フォーマットされた文字列
        """
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    
    def get_value_type(self, value: Any) -> str:
        """値の型を判定

        Args:
            value: 判定する値

        Returns:
            値の型を表す文字列
        """
        if isinstance(value, bool):
            return "真偽値"
        elif isinstance(value, int) or isinstance(value, float):
            return "数値"
        elif isinstance(value, list):
            return "リスト"
        elif isinstance(value, dict):
            return "辞書"
        else:
            return "文字列"
    
    def add_metadata(self) -> None:
        """メタデータを追加する"""
        key = self.key_edit.text()
        value = self.value_edit.text()
        value_type = self.type_combo.currentText()
        
        if not key:
            QMessageBox.warning(self, "入力エラー", "キー名を入力してください")
            return
        
        # 値の型変換
        converted_value = self.convert_value(value, value_type)
        
        # テーブルに追加
        row = self.metadata_table.rowCount()
        self.metadata_table.insertRow(row)
        self.metadata_table.setItem(row, 0, QTableWidgetItem(key))
        
        value_item = QTableWidgetItem(self.format_value_for_display(converted_value))
        value_item.setData(Qt.ItemDataRole.UserRole, value_type)
        self.metadata_table.setItem(row, 1, value_item)
        
        # 入力フィールドをクリア
        self.key_edit.clear()
        self.value_edit.clear()
    
    def convert_value(self, value_str: str, value_type: str) -> Any:
        """文字列を指定された型に変換する

        Args:
            value_str: 変換する文字列
            value_type: 変換先の型

        Returns:
            変換された値
        """
        try:
            if value_type == "文字列":
                return value_str
            elif value_type == "数値":
                return int(value_str) if value_str.isdigit() else float(value_str)
            elif value_type == "真偽値":
                return value_str.lower() in ("true", "yes", "1")
            elif value_type == "リスト":
                return json.loads(value_str) if value_str else []
            elif value_type == "辞書":
                return json.loads(value_str) if value_str else {}
            return value_str
        except Exception as e:
            QMessageBox.warning(self, "変換エラー", f"値の変換に失敗しました: {str(e)}")
            return value_str
    
    def show_context_menu(self, position) -> None:
        """コンテキストメニューを表示

        Args:
            position: マウス位置
        """
        menu = QMenu()
        
        edit_action = QAction("編集", self)
        delete_action = QAction("削除", self)
        copy_action = QAction("コピー", self)
        
        selected_items = self.metadata_table.selectedItems()
        if selected_items:
            menu.addAction(edit_action)
            menu.addAction(delete_action)
            menu.addAction(copy_action)
        
        add_action = QAction("新規追加", self)
        menu.addAction(add_action)
        
        action = menu.exec(self.metadata_table.mapToGlobal(position))
        
        if action == edit_action:
            self.edit_selected_item()
        elif action == delete_action:
            self.delete_selected_items()
        elif action == copy_action:
            self.copy_selected_item()
        elif action == add_action:
            self.key_edit.setFocus()
    
    def edit_selected_item(self) -> None:
        """選択されたアイテムを編集"""
        selected_items = self.metadata_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        key_item = self.metadata_table.item(row, 0)
        value_item = self.metadata_table.item(row, 1)
        
        if key_item and value_item:
            # 値の型を取得
            value_type = value_item.data(Qt.ItemDataRole.UserRole) or "文字列"
            
            # 値を編集ダイアログで開く
            current_value = self.convert_value(value_item.text(), value_type)
            dialog = MetadataValueEditor(current_value, value_type, self)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_value = dialog.get_value()
                value_item.setText(self.format_value_for_display(new_value))
    
    def delete_selected_items(self) -> None:
        """選択されたアイテムを削除"""
        rows = set(item.row() for item in self.metadata_table.selectedItems())
        
        if not rows:
            return
        
        if QMessageBox.question(
            self,
            "削除の確認",
            f"選択された{len(rows)}行のメタデータを削除してもよろしいですか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) != QMessageBox.StandardButton.Yes:
            return
        
        # 逆順に削除（インデックスがずれないように）
        for row in sorted(rows, reverse=True):
            self.metadata_table.removeRow(row)
    
    def copy_selected_item(self) -> None:
        """選択されたアイテムをクリップボードにコピー"""
        selected_items = self.metadata_table.selectedItems()
        if not selected_items:
            return
        
        # 選択されたセルのテキストをコピー
        clipboard = QApplication.clipboard()
        clipboard.setText(selected_items[0].text())
    
    def save_metadata(self) -> None:
        """メタデータをエントリに保存する"""
        # 既存のメタデータをクリア
        self.entry.clear_metadata()
        
        # テーブルから新しいメタデータを設定
        rows = self.metadata_table.rowCount()
        for row in range(rows):
            key_item = self.metadata_table.item(row, 0)
            value_item = self.metadata_table.item(row, 1)
            
            if key_item and value_item:
                key = key_item.text()
                value_str = value_item.text()
                value_type = value_item.data(Qt.ItemDataRole.UserRole) or "文字列"
                
                # 値の型変換
                value = self.convert_value(value_str, value_type)
                
                self.entry.add_metadata(key, value)
        
        self.accept()
