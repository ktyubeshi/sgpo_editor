"""メタデータ表示パネル"""

import logging
from typing import Optional

from sgpo_editor.types import MetadataValueType

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QHBoxLayout,
    QHeaderView,
)

from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class MetadataPanel(QWidget):
    """メタデータ表示パネル"""

    # エントリ編集リクエストシグナル
    edit_requested = Signal(EntryModel)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化

        Args:
            parent: 親ウィジェット
        """
        super().__init__(parent)
        self.entry = None
        self.setup_ui()

    def setup_ui(self) -> None:
        """UIコンポーネントの設定"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # タイトル
        title_layout = QHBoxLayout()
        title_label = QLabel("メタデータ")
        title_label.setStyleSheet("font-weight: bold;")
        title_layout.addWidget(title_label)

        self.edit_button = QPushButton("編集")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.request_edit)
        title_layout.addWidget(self.edit_button)

        layout.addLayout(title_layout)

        # ツリーウィジェット
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["キー", "値"])
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tree)

    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """表示するエントリを設定

        Args:
            entry: 表示するエントリ
        """
        self.entry = entry
        self.edit_button.setEnabled(entry is not None)
        self.update_display()

    def update_display(self) -> None:
        """表示を更新"""
        self.tree.clear()

        if not self.entry:
            return

        # EntryModelクラスのmetadataプロパティを使用
        metadata = getattr(self.entry, "metadata", {})

        if not metadata:
            no_data_item = QTreeWidgetItem(["", "メタデータなし"])
            self.tree.addTopLevelItem(no_data_item)
            return

        for key, value in metadata.items():
            self.add_metadata_item(key, value)

        self.tree.expandAll()

    def add_metadata_item(
        self,
        key: str,
        value: MetadataValueType,
        parent: Optional[QTreeWidgetItem] = None,
    ) -> QTreeWidgetItem:
        """メタデータアイテムをツリーに追加

        Args:
            key: メタデータのキー
            value: メタデータの値
            parent: 親アイテム

        Returns:
            追加されたツリーアイテム
        """
        if parent is None:
            item = QTreeWidgetItem([key, self.format_value(value)])
            self.tree.addTopLevelItem(item)
        else:
            item = QTreeWidgetItem([key, self.format_value(value)])
            parent.addChild(item)

        # 複合型の場合は子アイテムを追加
        if isinstance(value, dict):
            for k, v in value.items():
                self.add_metadata_item(k, v, item)
        elif isinstance(value, list):
            for i, v in enumerate(value):
                self.add_metadata_item(f"[{i}]", v, item)

        return item

    def format_value(self, value: MetadataValueType) -> str:
        """値を表示用にフォーマット

        Args:
            value: フォーマットする値

        Returns:
            フォーマットされた文字列
        """
        if isinstance(value, (dict, list)):
            return ""  # 複合型は子アイテムで表示
        return str(value)

    def request_edit(self) -> None:
        """メタデータ編集リクエスト"""
        if self.entry:
            self.edit_requested.emit(self.entry)
