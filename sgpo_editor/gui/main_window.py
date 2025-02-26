"""メインウィンドウ"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QTableWidget,
    QWidget,
    QApplication,
    QMessageBox,
)

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.gui.widgets.search import SearchWidget
from sgpo_editor.gui.widgets.stats import StatsWidget
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.file_handler import FileHandler
from sgpo_editor.gui.event_handler import EventHandler
from sgpo_editor.gui.ui_setup import UIManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """メインウィンドウ"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self.setWindowTitle("PO Editor")
        self.resize(800, 600)

        # コンポーネントの作成
        self.entry_editor = EntryEditor()
        self.stats_widget = StatsWidget()
        self.search_widget = SearchWidget(
            on_filter_changed=self._on_filter_changed,
            on_search_changed=self._on_search_changed,
            on_open_clicked=self._open_file,
        )
        self.table = QTableWidget()
        
        # 各マネージャの初期化
        self.table_manager = TableManager(self.table, self._get_current_po)
        self.ui_manager = UIManager(
            self, self.entry_editor, self.stats_widget, self.search_widget
        )
        self.file_handler = FileHandler(
            self,
            self._update_stats,
            self._update_table,
            self.statusBar().showMessage,
        )
        self.event_handler = EventHandler(
            self.table,
            self.entry_editor,
            self._get_current_po,
            self._update_table,
            self.statusBar().showMessage,
        )
        
        # UIの初期化
        self._setup_ui()
        
        # イベント接続
        self.event_handler.setup_connections()
        self.event_handler.entry_updated.connect(self._on_entry_updated)

    def _setup_ui(self) -> None:
        """UIの初期化"""
        # 中央ウィジェット（テーブル）
        self.ui_manager.setup_central_widget(self.table)
        
        # ドックウィジェット
        self.ui_manager.setup_dock_widgets()
        
        # メニューバー
        self.ui_manager.setup_menubar({
            "open_file": self._open_file,
            "save_file": self._save_file,
            "save_file_as": self._save_file_as,
            "close": self.close,
            "change_layout": self._change_entry_layout,
        })
        
        # ステータスバー
        self.ui_manager.setup_statusbar()
        
        # ウィンドウ状態の復元
        self.ui_manager.restore_dock_states()
        self.ui_manager.restore_window_state()

    def closeEvent(self, event: QEvent) -> None:
        """ウィンドウが閉じられるときの処理

        Args:
            event: イベント
        """
        # 設定の保存
        self.ui_manager.save_dock_states()
        self.ui_manager.save_window_state()
        event.accept()

    def _get_current_po(self) -> Optional[ViewerPOFile]:
        """現在のPOファイルを取得

        Returns:
            現在のPOファイル
        """
        return self.file_handler.current_po

    def _open_file(self) -> None:
        """ファイルを開く"""
        self.file_handler.open_file()

    def _save_file(self) -> None:
        """ファイルを保存する"""
        self.file_handler.save_file()

    def _save_file_as(self) -> None:
        """名前を付けて保存する"""
        self.file_handler.save_file_as()

    def _update_stats(self, stats: Dict[str, Any]) -> None:
        """統計情報を更新する

        Args:
            stats: 統計情報
        """
        self.stats_widget.update_stats(stats)

    def _update_table(self) -> None:
        """テーブルを更新する"""
        self.table_manager.update_table(self.file_handler.current_po)

    def _on_filter_changed(self) -> None:
        """フィルターが変更されたときの処理"""
        self._update_table()

    def _on_search_changed(self) -> None:
        """検索テキストが変更されたときの処理"""
        search_text = self.search_widget.get_search_text()
        if not search_text:
            return
            
        current_po = self._get_current_po()
        if not current_po:
            return
            
        # 検索テキストに一致するエントリを検索
        found = False
        entries = current_po.get_filtered_entries()
        for i, entry in enumerate(entries):
            if (search_text.lower() in (entry.msgid or "").lower() or
                search_text.lower() in (entry.msgstr or "").lower() or
                search_text.lower() in (entry.msgctxt or "").lower()):
                self.table.selectRow(i)
                found = True
                break
                
        if not found:
            self.statusBar().showMessage(f"検索テキスト '{search_text}' は見つかりませんでした", 3000)

    def _on_entry_updated(self, entry_number: int) -> None:
        """エントリが更新されたときの処理

        Args:
            entry_number: エントリ番号
        """
        # 統計情報の更新
        current_po = self._get_current_po()
        if current_po:
            stats = current_po.get_stats()
            self._update_stats(stats)

    def _change_entry_layout(self, layout_type: LayoutType) -> None:
        """エントリ編集のレイアウトを変更する

        Args:
            layout_type: レイアウトタイプ
        """
        self.event_handler.change_entry_layout(layout_type)


def main():
    """アプリケーションのエントリーポイント"""
    app = QApplication(sys.argv)
    app.setApplicationName("PO Editor")
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
