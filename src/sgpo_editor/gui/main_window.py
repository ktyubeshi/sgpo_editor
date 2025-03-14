"""メインウィンドウ"""

import logging
import sys
from typing import Any, Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidget, QWidget, QDockWidget, QMessageBox, QDialog

from sgpo_editor.gui.metadata_dialog import MetadataEditDialog
from sgpo_editor.gui.metadata_panel import MetadataPanel
from sgpo_editor.models.entry import EntryModel

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.event_handler import EventHandler
from sgpo_editor.gui.file_handler import FileHandler
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.ui_setup import UIManager

# ViewerPOFileのインポートを遅延させる
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.gui.widgets.po_format_editor import POFormatEditor
from sgpo_editor.gui.widgets.preview_widget import PreviewDialog
from sgpo_editor.gui.widgets.search import SearchWidget
from sgpo_editor.gui.widgets.stats import StatsWidget

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
        
        # メタデータパネルの初期化
        self.metadata_panel = MetadataPanel(self)

        # UIの初期化
        self._setup_ui()

        # イベント接続
        self.event_handler.setup_connections()
        self.event_handler.entry_updated.connect(self._on_entry_updated)
        
        # メタデータパネルのイベント接続
        self.metadata_panel.edit_requested.connect(self.edit_metadata)

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
            "toggle_column_visibility": self._toggle_column_visibility,
            "table_manager": self.table_manager,
        })
        
        # メタデータメニューの追加
        self.setup_metadata_menu()

        # ステータスバー
        self.ui_manager.setup_statusbar()

        # メタデータパネルのドックウィジェット設定
        self.setup_metadata_panel()
        
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

    def _update_stats(self, stats: Any) -> None:
        """統計情報を更新する

        Args:
            stats: 統計情報
        """
        from sgpo_editor.models import StatsModel

        # namedtupleを辞書に変換
        if hasattr(stats, "_asdict"):
            # namedtupleの場合は_asdictメソッドで辞書に変換
            stats_dict = stats._asdict()
            logger.debug(f"統計情報を辞書に変換します: {stats_dict}")
        elif isinstance(stats, dict):
            # すでに辞書型の場合はそのまま使用
            stats_dict = stats
        else:
            # その他の型の場合はエラーログを出力して空の辞書を使用
            logger.error(f"統計情報の型が不正です: {type(stats)}, {stats}")
            stats_dict = {}

        # StatsModelを作成してウィジェットを更新
        stats_model = StatsModel(**stats_dict)
        self.stats_widget.update_stats(stats_model)

    def _update_table(self) -> None:
        """テーブルを更新する"""
        # 現在のPOファイルを取得
        current_po = self._get_current_po()
        if not current_po:
            logger.debug(
                "POファイルが読み込まれていないため、テーブル更新をスキップします"
            )
            return

        try:
            # フィルタ条件を取得
            criteria = self.search_widget.get_search_criteria()
            filter_text = criteria.filter
            filter_keyword = criteria.filter_keyword

            logger.debug(
                f"テーブル更新: filter_text={filter_text}, filter_keyword={filter_keyword}"
            )

            # POファイルからフィルタ条件に合ったエントリを取得
            # update_filter=Trueを指定して、キャッシュを使わずに強制的に最新データを取得
            entries = current_po.get_filtered_entries(
                update_filter=True,  # 強制的に更新
                filter_text=filter_text,
                filter_keyword=filter_keyword,
            )

            logger.debug(f"取得したエントリ数: {len(entries)}件")

            # テーブルを更新（フィルタ条件を渡す）
            # 現在のソート条件を維持したまま更新
            sorted_entries = self.table_manager.update_table(entries, criteria)

            logger.debug(
                f"テーブル更新完了: {len(sorted_entries) if sorted_entries else 0}件表示"
            )

            # フィルタ結果の件数をステータスバーに表示
            self.statusBar().showMessage(f"フィルタ結果: {len(entries)}件")
            
            # テーブルの表示を強制的に更新
            self.table.viewport().update()
        except Exception as e:
            logger.error(f"テーブル更新エラー: {str(e)}", exc_info=True)
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
                filter_text=criteria.filter, filter_keyword=criteria.filter_keyword
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
            if criteria.filter_keyword is None:
                # Noneの場合はそのまま処理
                logging.debug("キーワードがNoneのため、全エントリを取得します")
            elif criteria.filter_keyword.strip() == "":
                # 空白文字のみの場合はNoneに設定
                criteria.filter_keyword = None
                logging.debug("キーワードが空文字のため、全エントリを取得します")
                # 検索テキストを明示的に空に設定
                self.search_widget.search_edit.setText("")

                # ★重要: キーワードがクリアされたとき、ViewerPOFileの内部状態をリセット
                current_po.search_text = None
                # キャッシュされたフィルタリング結果をクリア
                current_po.filtered_entries = []

            # デバッグ用ログ出力
            print(f"キーワードフィルタ変更: {criteria.filter_keyword}")
            print(
                f"フィルタ条件: filter={criteria.filter}, keyword={
                    criteria.filter_keyword
                }, match_mode={criteria.match_mode}"
            )
            logging.debug(
                f"MainWindow._on_search_changed: filter={criteria.filter}, keyword={
                    criteria.filter_keyword
                }"
            )

            # エントリを取得する前に、キーワードがNoneまたは空文字の場合はViewerPOFileの内部状態を明示的にリセット
            if criteria.filter_keyword is None:
                logging.debug(
                    "キーワードがNoneのため、ViewerPOFileの内部状態をリセットします"
                )
                current_po.search_text = None
                current_po.filtered_entries = []
            elif criteria.filter_keyword == "":
                logging.debug(
                    "キーワードが空文字のため、ViewerPOFileの内部状態をリセットします"
                )
                current_po.search_text = None
                current_po.filtered_entries = []

            # POファイルからフィルタ条件に合ったエントリを取得
            print("フィルタ条件に合ったエントリを取得中...")
            print(
                f"現在のViewerPOFile状態: search_text={
                    current_po.search_text
                }, filter_text={current_po.filter_text}"
            )

            entries = current_po.get_filtered_entries(
                update_filter=True,  # 強制的にフィルタを更新
                filter_text=criteria.filter,
                filter_keyword=criteria.filter_keyword,
            )
            print(f"取得完了: {len(entries)}件のエントリが見つかりました")
            print(
                f"更新後のViewerPOFile状態: search_text={
                    current_po.search_text
                }, filter_text={current_po.filter_text}"
            )

            # テーブルを更新
            print("テーブル更新開始...")
            updated_entries = self.table_manager.update_table(entries, criteria)
            print(
                f"テーブル更新完了: {
                    len(updated_entries) if updated_entries else 0
                }件表示"
            )

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
        logger.debug(f"エントリ更新通知を受信: エントリ番号={entry_number}")
        
        # 現在のPOファイルを取得
        current_po = self._get_current_po()
        if current_po:
            # 統計情報の更新
            stats = current_po.get_stats()
            self._update_stats(stats)
            
            # エントリ更新後にテーブルを確実に更新
            logger.debug("エントリ更新後にテーブルを更新します")
            self._update_table()
            
        # メタデータパネルの更新
        self.update_metadata_panel()

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
        
    def _toggle_column_visibility(self, column_index: int) -> None:
        """列の表示/非表示を切り替える
        
        Args:
            column_index: 列インデックス
        """
        try:
            # 変更前の状態を記録
            was_visible = self.table_manager.is_column_visible(column_index)
            logger.debug(f"列 {column_index} の切り替え前の状態: {'表示' if was_visible else '非表示'}")
            
            # 列の表示/非表示を切り替える
            self.table_manager.toggle_column_visibility(column_index)
            
            # 変更後の状態を取得
            now_visible = self.table_manager.is_column_visible(column_index)
            logger.debug(f"列 {column_index} の切り替え後の状態: {'表示' if now_visible else '非表示'}")
            
            # UIのチェック状態を確実に更新
            self.ui_manager.update_column_visibility_action(column_index, now_visible)
            
            # デバッグ情報とユーザー通知
            action_text = '表示' if now_visible else '非表示'
            self.statusBar().showMessage(f"列 {column_index} を{action_text}に設定しました")
            logger.info(f"列 {column_index} の表示状態を {was_visible} から {now_visible} に変更しました")
        except Exception as e:
            logger.error(f"列表示の切り替えエラー: {str(e)}", exc_info=True)
            self.statusBar().showMessage(f"列表示の切り替えエラー: {str(e)}")


    def setup_metadata_menu(self) -> None:
        """メタデータ関連のメニューを設定"""
        metadata_menu = self.menuBar().addMenu("メタデータ")
        
        edit_action = QAction("メタデータ編集", self)
        edit_action.triggered.connect(self.edit_metadata)
        metadata_menu.addAction(edit_action)
        
        view_action = QAction("メタデータパネル表示", self)
        view_action.setCheckable(True)
        view_action.triggered.connect(self.toggle_metadata_panel)
        metadata_menu.addAction(view_action)

    def setup_metadata_panel(self) -> None:
        """メタデータパネルの設定"""
        # メタデータパネルを右側のドックウィジェットとして追加
        self.metadata_dock = QDockWidget("メタデータ", self)
        self.metadata_dock.setWidget(self.metadata_panel)
        self.metadata_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.metadata_dock)
        
        # 初期状態では非表示
        self.metadata_dock.setVisible(False)

    def toggle_metadata_panel(self, checked: bool) -> None:
        """メタデータパネルの表示/非表示を切り替え
        
        Args:
            checked: チェック状態
        """
        self.metadata_dock.setVisible(checked)
        
        # 表示されたときに現在の選択エントリを表示
        if checked:
            self.update_metadata_panel()

    def edit_metadata(self, entry: Optional[EntryModel] = None) -> None:
        """メタデータ編集ダイアログを表示
        
        Args:
            entry: 編集対象のエントリ（指定がない場合は選択中のエントリ）
        """
        if entry is None:
            # 現在選択されているエントリを取得
            current_entry = self.event_handler.get_current_entry()
            if not current_entry:
                self.statusBar().showMessage("メタデータを編集するエントリが選択されていません")
                return
            
            entry = current_entry
        
        dialog = MetadataEditDialog(entry, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # メタデータパネルを更新
            self.update_metadata_panel()
            
            # メタデータが変更されたフラグを設定
            self.file_handler.set_modified(True)
            
            # ステータスバーに表示
            self.statusBar().showMessage("メタデータを更新しました")

    def update_metadata_panel(self) -> None:
        """メタデータパネルを更新"""
        # 現在選択されているエントリを取得
        current_entry = self.event_handler.get_current_entry()
        
        # メタデータパネルにエントリを設定
        self.metadata_panel.set_entry(current_entry)


def main():
    """アプリケーションのエントリーポイント"""
    app = QApplication(sys.argv)
    app.setApplicationName("PO Editor")

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
