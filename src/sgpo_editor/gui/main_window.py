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

# ViewerPOFileのインポートを遅延させる
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.gui.widgets.search import SearchWidget
from sgpo_editor.gui.widgets.stats import StatsWidget
from sgpo_editor.gui.widgets.po_format_editor import POFormatEditor
from sgpo_editor.gui.widgets.preview_widget import PreviewDialog
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
        
        # ツールバー
        self.ui_manager.setup_toolbar(self.entry_editor._show_review_dialog)
        
        # メニューバー
        self.ui_manager.setup_menubar({
            "open_file": self._open_file,
            "save_file": self._save_file,
            "save_file_as": self._save_file_as,
            "close": self.close,
            "change_layout": self._change_entry_layout,
            "open_recent_file": self._open_recent_file,
            "open_po_format_editor": self._open_po_format_editor,
            "show_preview": self._show_preview_dialog,
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

    def _get_current_po(self) -> Optional["ViewerPOFile"]:
        """現在のPOファイルを取得

        Returns:
            現在のPOファイル
        """
        return self.file_handler.current_po

    def _open_file(self) -> None:
        """ファイルを開く"""
        self.file_handler.open_file()
        # 最近使用したファイルメニューを更新
        self.ui_manager.update_recent_files_menu(self._open_recent_file)

    def _open_recent_file(self, filepath: str) -> None:
        """最近使用したファイルを開く

        Args:
            filepath: ファイルパス
        """
        if filepath:
            self.file_handler.open_file(filepath)
            # 最近使用したファイルメニューを更新
            self.ui_manager.update_recent_files_menu(self._open_recent_file)

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
        # 現在のPOファイルを取得
        current_po = self._get_current_po()
        if not current_po:
            return
            
        # フィルタ条件を取得
        criteria = self.search_widget.get_search_criteria()
        filter_text = criteria.filter
        filter_keyword = criteria.filter_keyword
        
        try:
            # POファイルからフィルタ条件に合ったエントリを取得
            entries = current_po.get_filtered_entries(
                filter_text=filter_text,
                filter_keyword=filter_keyword
            )
            
            # テーブルを更新（フィルタ条件を渡す）
            self.table_manager.update_table(entries, criteria)
            
            # フィルタ結果の件数をステータスバーに表示
            self.statusBar().showMessage(f"フィルタ結果: {len(entries)}件")
        except Exception as e:
            self.statusBar().showMessage(f"テーブル更新エラー: {str(e)}")

    def _on_filter_changed(self) -> None:
        """フィルターが変更されたときの処理"""
        current_po = self._get_current_po()
        if not current_po:
            return
            
        try:
            # フィルタ条件を取得
            criteria = self.search_widget.get_search_criteria()
            
            # POファイルからフィルタ条件に合ったエントリを取得
            entries = current_po.get_filtered_entries(
                filter_text=criteria.filter,
                filter_keyword=criteria.filter_keyword
            )
            
            # テーブルを更新
            self.table_manager.update_table(entries, criteria)
            
            # フィルタ結果の件数をステータスバーに表示
            self.statusBar().showMessage(f"フィルタ結果: {len(entries)}件")
        except Exception as e:
            self.statusBar().showMessage(f"エラー: {str(e)}")

    def _on_search_changed(self) -> None:
        """フィルターキーワードが変更されたときの処理"""
        import logging
        current_po = self._get_current_po()
        if not current_po:
            logging.debug("現在のPOファイルが存在しません")
            return
            
        try:
            # フィルタ条件を取得
            criteria = self.search_widget.get_search_criteria()
            
            # 空のキーワードを処理
            if criteria.filter_keyword:
                criteria.filter_keyword = criteria.filter_keyword.strip()
            
            # デバッグ用ログ出力
            print(f"キーワードフィルタ変更: {criteria.filter_keyword}")
            print(f"フィルタ条件: filter={criteria.filter}, keyword={criteria.filter_keyword}, match_mode={criteria.match_mode}")
            logging.debug(f"MainWindow._on_search_changed: filter={criteria.filter}, keyword={criteria.filter_keyword}")
            
            # POファイルからフィルタ条件に合ったエントリを取得
            print("フィルタ条件に合ったエントリを取得中...")
            
            # キーワードが空の場合はフィルタしない
            if not criteria.filter_keyword:
                logging.debug("キーワードが空のため、全エントリを取得します")
            
            entries = current_po.get_filtered_entries(
                update_filter=True,  # 強制的にフィルタを更新
                filter_text=criteria.filter,
                filter_keyword=criteria.filter_keyword
            )
            print(f"取得完了: {len(entries)}件のエントリが見つかりました")
            
            # テーブルを更新
            print("テーブル更新開始...")
            updated_entries = self.table_manager.update_table(entries, criteria)
            print(f"テーブル更新完了: {len(updated_entries) if updated_entries else 0}件表示")
            
            # フィルタ結果の件数をステータスバーに表示
            self.statusBar().showMessage(f"フィルタ結果: {len(entries)}件")
        except Exception as e:
            print(f"キーワードフィルタ処理中にエラーが発生しました: {str(e)}")
            logging.error(f"キーワードフィルタエラー: {str(e)}")
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"エラー: {str(e)}")

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
        
    def _show_preview_dialog(self) -> None:
        """プレビューダイアログを表示する"""
        # 現在選択されているエントリがない場合は何もしない
        current_entry = self.event_handler.get_current_entry()
        if not current_entry:
            self.statusBar().showMessage("プレビューするエントリが選択されていません")
            return
            
        # プレビューダイアログを表示
        dialog = PreviewDialog(self)
        # イベントハンドラーを設定してエントリ選択変更イベントを接続
        dialog.set_event_handler(self.event_handler)
        # 現在のエントリを設定
        dialog.set_entry(current_entry)
        # ダイアログを表示
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        
    def _open_po_format_editor(self) -> None:
        """POフォーマットエディタを開く"""
        if not hasattr(self, "_po_format_editor"):
            self._po_format_editor = POFormatEditor(self, self._get_current_po)
            # エントリ更新シグナルを接続
            self._po_format_editor.entry_updated.connect(self._on_entry_updated)
        
        self._po_format_editor.show()


def main():
    """アプリケーションのエントリーポイント"""
    app = QApplication(sys.argv)
    app.setApplicationName("PO Editor")
    
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
