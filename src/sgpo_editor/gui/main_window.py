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
from sgpo_editor.i18n import setup_translator

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.gui.event_handler import EventHandler
from sgpo_editor.gui.facades.entry_editor_facade import EntryEditorFacade
from sgpo_editor.gui.facades.entry_list_facade import EntryListFacade
from sgpo_editor.gui.file_handler import FileHandler
from sgpo_editor.gui.table_manager import TableManager
from sgpo_editor.gui.ui_setup import UIManager

# 必要なクラスをインポート
from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
from sgpo_editor.gui.widgets.po_format_editor import POFormatEditor
from sgpo_editor.gui.widgets.preview_widget import PreviewDialog
from sgpo_editor.gui.widgets.search import SearchWidget
from sgpo_editor.gui.widgets.stats import StatsWidget
from sgpo_editor.gui.translation_evaluate_dialog import TranslationEvaluateDialog
from sgpo_editor.gui.evaluation_dialog import EvaluationDialog

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
        self.table = QTableWidget()

        # SearchWidgetの初期化（コールバック関数を渡す）
        self.search_widget = SearchWidget(
            on_filter_changed=lambda: self._update_table(),
            on_search_changed=lambda: self._update_table()
        )

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

        # ファサードの初期化（新規追加）
        self.entry_editor_facade = EntryEditorFacade(
            self.entry_editor,
            self._get_current_po,
            self.statusBar().showMessage
        )
        self.entry_list_facade = EntryListFacade(
            self.table,
            self.table_manager,
            self.search_widget,
            self._get_current_po
        )

        # 既存のイベントハンドラ（レガシー互換用）
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

        # レガシーなイベント接続
        self.event_handler.entry_updated.connect(self._on_entry_updated)
        self.event_handler.entry_selected.connect(self._on_entry_selected)

        # ファサードを使った新しいイベント接続
        self.entry_editor_facade.entry_applied.connect(self._on_entry_updated)
        # エントリテキスト変更シグナルは現時点では必要ないのでコメントアウト
        # self.entry_editor_facade.entry_changed.connect(self._on_entry_text_changed)
        self.entry_list_facade.entry_selected.connect(self._on_entry_selected)
        self.entry_list_facade.filter_changed.connect(self._update_table)

        # メタデータパネルのイベント接続
        self.metadata_panel.edit_requested.connect(self.edit_metadata)

    def _setup_ui(self) -> None:
        """UIの初期化"""
        # 中央ウィジェット（テーブル）
        self.ui_manager.setup_central_widget(self.table)

        # ドックウィジェット
        self.ui_manager.setup_dock_widgets()

        # ツールバー
        self.ui_manager.setup_toolbar(self.entry_editor_facade.show_review_dialog)

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
            "show_translation_evaluate": self._show_translation_evaluate_dialog,
            "show_translation_evaluation_result": self._show_translation_evaluation_result_dialog,
        })

        # メタデータメニューの追加
        self.setup_metadata_menu()

        # メタデータパネルのドックウィジェット設定
        self.setup_metadata_panel()

        # ウィンドウメニューのセットアップ
        self.ui_manager.setup_window_menu()

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

    async def _open_file(self) -> None:
        """ファイルを開く（非同期）"""
        # file_handlerの非同期メソッドを呼び出す
        success = await self.file_handler.open_file()
        
        if not success:
            logger.debug("MainWindow._open_file: ファイルを開くのに失敗しました")
            return

        # EntryEditorにデータベースを設定（ファサード経由）
        current_po = self._get_current_po()
        if current_po:
            logger.debug(f"MainWindow._open_file: ファサード経由でデータベースを設定")
            self.entry_editor_facade.set_database(current_po.db)
            logger.debug(f"MainWindow._open_file: データベース設定完了")

        # 最近使用したファイルメニューを更新
        self.ui_manager.update_recent_files_menu(self._open_recent_file)

    async def _open_recent_file(self, filepath: str) -> None:
        """最近使用したファイルを開く（非同期）

        Args:
            filepath: ファイルパス
        """
        if filepath:
            # file_handlerの非同期メソッドを呼び出す
            success = await self.file_handler.open_file(filepath)
            
            if not success:
                logger.debug(f"MainWindow._open_recent_file: ファイル '{filepath}' を開くのに失敗しました")
                return

            # EntryEditorにデータベースを設定（ファサード経由）
            current_po = self._get_current_po()
            if current_po:
                logger.debug(f"MainWindow._open_recent_file: ファサード経由でデータベースを設定")
                self.entry_editor_facade.set_database(current_po.db)
                logger.debug(f"MainWindow._open_recent_file: データベース設定完了")

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
        """テーブルを更新する

        ファサードパターンを使用して、テーブル更新処理を委譲します。
        """
        current_po = self._get_current_po()
        if not current_po:
            logger.debug("POファイルが読み込まれていないため、テーブル更新をスキップします")
            return

        try:
            # EntryListFacadeにテーブル更新を委譲
            self.entry_list_facade.update_table()

            # 件数表示のためにPOファイルから情報を取得
            entries = current_po.get_filtered_entries()
            self.statusBar().showMessage(f"フィルタ結果: {len(entries)}件")
        except Exception as e:
            logger.error(f"テーブル更新エラー: {e}")
            self.statusBar().showMessage(f"テーブル更新エラー: {e}")

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

    def _on_entry_selected(self, entry_number: int) -> None:
        """エントリが選択されたときの処理

        Args:
            entry_number: エントリ番号
        """
        logger.debug(f"エントリ選択通知を受信: エントリ番号={entry_number}")

        try:
            # メタデータパネルのみ更新し、テーブルの更新は行わない
            logger.debug("MainWindow._on_entry_selected: メタデータパネルを更新")
            self.update_metadata_panel()

            # プレビューウィンドウが表示されている場合は更新
            logger.debug("MainWindow._on_entry_selected: プレビューダイアログの更新を試行")
            has_preview = hasattr(self, "_preview_dialog") and self._preview_dialog and self._preview_dialog.isVisible()
            logger.debug(
                f"MainWindow._on_entry_selected: プレビューダイアログの状態: 存在={hasattr(self, '_preview_dialog')}, 有効={bool(getattr(self, '_preview_dialog', None))}, 表示中={getattr(self, '_preview_dialog', None).isVisible() if hasattr(self, '_preview_dialog') and self._preview_dialog else False}")

            self._update_preview_dialog(entry_number)

            # 評価結果ウィンドウが表示されている場合は更新
            logger.debug("MainWindow._on_entry_selected: 評価結果ウィンドウの更新を試行")
            has_evaluation = hasattr(self, "_evaluation_result_window") and self._evaluation_result_window and self._evaluation_result_window.isVisible()
            logger.debug(
                f"MainWindow._on_entry_selected: 評価結果ウィンドウの状態: 存在={hasattr(self, '_evaluation_result_window')}, 有効={bool(getattr(self, '_evaluation_result_window', None))}, 表示中={getattr(self, '_evaluation_result_window', None).isVisible() if hasattr(self, '_evaluation_result_window') and self._evaluation_result_window else False}")

            self._update_evaluation_result_window(entry_number)

            logger.debug(f"MainWindow._on_entry_selected: 処理完了 (プレビュー={has_preview}, 評価結果={has_evaluation})")
        except Exception as e:
            logger.error(f"MainWindow._on_entry_selected: エラー発生 {e}", exc_info=True)
            # エラーが発生しても処理を継続するため、例外は再送出しない

    def _on_entry_updated(self, key: str, msgstr: str) -> None:
        """エントリが更新されたときの処理

        Args:
            key: エントリのキー
            msgstr: 更新された翻訳文
        """
        logger.debug(f"MainWindow._on_entry_updated: 開始 key={key}")

        # 現在のPOファイルを取得
        current_po = self._get_current_po()
        if not current_po:
            logger.debug("MainWindow._on_entry_updated: 現在のPOファイルが存在しないため、エントリ更新処理をスキップします")
            return

        try:
            # 更新前の選択キーを取得
            current_key = self.entry_list_facade.get_selected_entry_key()
            logger.debug(f"MainWindow._on_entry_updated: 更新前の選択キー: {current_key}")

            # 更新されたキー
            updated_key = key
            logger.debug(f"MainWindow._on_entry_updated: 更新されたエントリ key={updated_key}")

            # 統計情報の更新
            logger.debug(f"MainWindow._on_entry_updated: 統計情報の更新")
            stats = current_po.get_stats()
            self._update_stats(stats)

            # 強制的にフィルタ更新フラグを設定
            logger.debug(f"MainWindow._on_entry_updated: 強制的にフィルタ更新フラグを設定")
            current_po._force_filter_update = True

            # ファサードを使用してテーブルを更新
            logger.debug(f"MainWindow._on_entry_updated: テーブル更新開始")
            self.entry_list_facade.update_table()
            logger.debug(f"MainWindow._on_entry_updated: テーブル更新完了")

            # エントリの選択状態を維持
            if updated_key:
                # 更新されたエントリを選択
                logger.debug(f"MainWindow._on_entry_updated: 更新されたエントリを選択 key={updated_key}")
                selection_success = self.entry_list_facade.select_entry_by_key(updated_key)
                logger.debug(f"MainWindow._on_entry_updated: 選択結果 success={selection_success}")
                
                if not selection_success and current_key and current_key != updated_key:
                    # 更新されたキーでの選択に失敗したら元のキーで試す
                    logger.debug(f"MainWindow._on_entry_updated: 更新キーでの選択に失敗したため元のキーで再試行 key={current_key}")
                    self.entry_list_facade.select_entry_by_key(current_key)
            elif current_key:
                # 元の選択状態を復元
                logger.debug(f"MainWindow._on_entry_updated: 元の選択状態を復元 key={current_key}")
                self.entry_list_facade.select_entry_by_key(current_key)

            # メタデータパネルの更新
            logger.debug(f"MainWindow._on_entry_updated: メタデータパネルの更新")
            self.update_metadata_panel()
            logger.debug(f"MainWindow._on_entry_updated: 完了")

        except Exception as e:
            logger.error(f"MainWindow._on_entry_updated: エラー発生 {e}")
            logger.error(f"エントリ更新処理エラー: {e}")

    def _change_entry_layout(self, layout_type: LayoutType) -> None:
        """エントリ編集のレイアウトを変更する

        Args:
            layout_type: レイアウトタイプ
        """
        self.event_handler.change_entry_layout(layout_type)

    def _show_preview_dialog(self) -> None:
        """プレビューダイアログを表示する

        ファサードパターンを使用して、エントリ編集ファサードから現在のエントリを取得します。
        """
        # ファサードから現在のエントリを取得
        current_entry = self.entry_editor_facade.get_current_entry()
        if not current_entry:
            self.statusBar().showMessage("プレビューするエントリが選択されていません")
            return

        # プレビューダイアログを表示
        dialog = PreviewDialog(self)
        # ファサードを使用してイベントハンドラを設定
        dialog.set_event_handler(self.event_handler)  # 互換性のためにイベントハンドラを使用
        # 現在のエントリを設定
        dialog.set_entry(current_entry)
        # ダイアログを表示
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

        # ダイアログへの参照を保持
        self._preview_dialog = dialog

        # エントリ選択時にプレビューダイアログを更新するシグナルを接続
        if not hasattr(self, "_connected_preview_signal"):
            self.entry_list_facade.entry_selected.connect(self._update_preview_dialog)
            self._connected_preview_signal = True

    def _open_po_format_editor(self) -> None:
        """POフォーマットエディタを開く

        ファサードパターンに対応して、エントリ更新シグナルをファサード経由で接続します。
        """
        if not hasattr(self, "_po_format_editor"):
            self._po_format_editor = POFormatEditor(self, self._get_current_po)
            # エントリ更新シグナルをファサードのメソッドに接続
            self._po_format_editor.entry_updated.connect(self._on_entry_updated)

        self._po_format_editor.show()
        self._po_format_editor.raise_()
        self._po_format_editor.activateWindow()

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
        self.metadata_dock.setObjectName("metadata_dock")
        self.metadata_dock.setWidget(self.metadata_panel)
        self.metadata_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.metadata_dock)

        # 初期状態では非表示
        self.metadata_dock.setVisible(False)

        # UIManagerにドックウィジェットを登録
        self.ui_manager.register_dock_widget("metadata", self.metadata_dock)

    def toggle_metadata_panel(self, checked: bool) -> None:
        """メタデータパネルの表示/非表示を切り替え

        Args:
            checked: チェック状態
        """
        self.metadata_dock.setVisible(checked)

        # 表示されたときに現在の選択エントリを表示
        if checked:
            self.update_metadata_panel()

    def _select_entry_by_key(self, key: str) -> bool:
        """指定されたキーを持つエントリをテーブルで選択する

        Args:
            key: 検索するエントリのキー

        Returns:
            選択成功時はTrue、失敗時はFalse
        """
        if not key:
            logger.debug(f"キーが空のため選択できません: {key}")
            return False

        logger.debug(f"キーによるエントリ選択: {key}")
        try:
            # テーブル内の全ての行を確認
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)  # 最初の列に対するアイテムを取得
                if item is None:
                    continue

                item_key = item.data(Qt.ItemDataRole.UserRole)
                if item_key == key:
                    logger.debug(f"エントリを選択: 行={row}, キー={key}")
                    # 行選択
                    self.table.selectRow(row)
                    # ビューをスクロールして選択した行を表示
                    self.table.scrollTo(self.table.model().index(row, 0))
                    return True

            logger.debug(f"キー {key} を持つエントリがテーブルに見つかりませんでした")
            return False
        except Exception as e:
            logger.error(f"エントリ選択エラー: {e}")
            return False

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

    def _show_translation_evaluate_dialog(self) -> None:
        """翻訳品質評価ダイアログを表示"""
        # 現在のエントリが選択されていない場合は警告
        current_entry_key = self.entry_list_facade.get_selected_entry_key()
        if not current_entry_key:
            QMessageBox.warning(
                self, "警告", "エントリが選択されていません。先にエントリを選択してください。"
            )
            return

        # 現在のPOファイルを取得
        current_po = self._get_current_po()
        if not current_po:
            QMessageBox.warning(
                self, "警告", "POファイルが読み込まれていません。"
            )
            return

        try:
            # 選択されたエントリを取得
            current_entry = current_po.get_entry_by_key(current_entry_key)
            if not current_entry:
                QMessageBox.warning(
                    self, "警告", "選択されたエントリを取得できませんでした。"
                )
                return

            # 新しいLLM評価ダイアログを使用
            if current_po.path:
                # EvaluationDatabaseを作成
                from sgpo_editor.models.evaluation_db import EvaluationDatabase
                eval_db = EvaluationDatabase(str(current_po.path))
                
                # 新しいEvaluationDialogを使用
                dialog = EvaluationDialog(current_entry, eval_db, self)

                # 評価完了時のシグナルを接続
                dialog.evaluation_completed.connect(
                    lambda entry, result: self._on_evaluation_completed(entry, result)
                )

                # ダイアログを表示
                dialog.exec()
            else:
                # データベースが利用できない場合は従来のダイアログを使用
                dialog = TranslationEvaluateDialog(self)

                # 現在のエントリとエントリリストを設定
                dialog.set_current_entry(current_entry)

                # エントリリストを取得
                entries = current_po.get_filtered_entries()
                dialog.set_entries(entries)

                # ダイアログを表示
                dialog.exec()

        except Exception as e:
            logger.error(f"翻訳品質評価ダイアログ表示エラー: {e}", exc_info=True)
            QMessageBox.critical(
                self, "エラー", f"翻訳品質評価ダイアログの表示中にエラーが発生しました: {e}"
            )

    def _update_evaluation_result_window(self, entry_number: int) -> None:
        """エントリ選択時に評価結果ウィンドウを更新

        Args:
            entry_number: 選択されたエントリの番号
        """
        logger.debug(f"MainWindow._update_evaluation_result_window: 開始 entry_number={entry_number}")

        # 評価結果ウィンドウが表示されていない場合は何もしない
        if not hasattr(self, "_evaluation_result_window") or not self._evaluation_result_window or not self._evaluation_result_window.isVisible():
            logger.debug("MainWindow._update_evaluation_result_window: 評価結果ウィンドウが表示されていないため更新をスキップ")
            return

        try:
            # 選択されたエントリを取得
            current_po = self._get_current_po()
            if not current_po:
                logger.debug("MainWindow._update_evaluation_result_window: 現在のPOファイルが存在しない")
                return

            # エントリ番号からエントリを取得
            current_entry = current_po.get_entry_by_number(entry_number)
            if not current_entry:
                logger.debug(f"MainWindow._update_evaluation_result_window: エントリが取得できなかった entry_number={entry_number}")
                return

            # 評価結果ウィンドウを更新
            logger.debug(f"MainWindow._update_evaluation_result_window: 評価結果ウィンドウを更新 entry_number={entry_number}")
            self._evaluation_result_window.set_entry(current_entry)

        except Exception as e:
            logger.error(f"MainWindow._update_evaluation_result_window: エラー発生 {e}", exc_info=True)

    def _on_evaluation_completed(self, entry: EntryModel, result: Any) -> None:
        """評価完了時の処理

        Args:
            entry: 評価されたエントリ
            result: 評価結果
        """
        logger.debug(f"MainWindow._on_evaluation_completed: 評価完了 entry={entry.key}")

        try:
            # テーブルを更新
            self._update_table()

            # 評価結果ウィンドウが表示されている場合は更新
            if hasattr(self, "_evaluation_result_window") and self._evaluation_result_window and self._evaluation_result_window.isVisible():
                logger.debug("MainWindow._on_evaluation_completed: 評価結果ウィンドウを更新")
                self._evaluation_result_window.set_entry(entry)

            # ステータスバーに表示
            self.statusBar().showMessage(f"翻訳評価が完了しました。総合スコア: {result.overall_score}")

            # ファイルの変更フラグを設定
            self.file_handler.set_modified(True)

        except Exception as e:
            logger.error(f"MainWindow._on_evaluation_completed: エラー発生 {e}", exc_info=True)

    def _update_preview_dialog(self, entry_number: int) -> None:
        """エントリ選択時にプレビューダイアログを更新

        Args:
            entry_number: 選択されたエントリの番号
        """
        logger.debug(f"MainWindow._update_preview_dialog: 開始 entry_number={entry_number}")

        # プレビューダイアログが存在しない、または表示されていない場合は何もしない
        if not hasattr(self, "_preview_dialog") or not self._preview_dialog or not self._preview_dialog.isVisible():
            logger.debug("MainWindow._update_preview_dialog: プレビューダイアログが存在しないか表示されていない")
            return

        # 現在のPOファイルを取得
        current_po = self._get_current_po()
        if not current_po:
            logger.debug("MainWindow._update_preview_dialog: 現在のPOファイルが存在しない")
            return

        # 選択されたエントリを取得
        logger.debug(f"MainWindow._update_preview_dialog: フィルタリングされたエントリを取得")
        entries = current_po.get_filtered_entries()
        logger.debug(f"MainWindow._update_preview_dialog: 取得したエントリ数={len(entries)}")

        if 0 <= entry_number < len(entries):
            entry = entries[entry_number]
            logger.debug(f"MainWindow._update_preview_dialog: エントリ {entry_number} を取得 msgid='{entry.msgid[:30]}...'")
            # プレビューダイアログを更新
            self._preview_dialog.set_entry(entry)
            logger.debug("MainWindow._update_preview_dialog: プレビューダイアログを更新")
        else:
            logger.debug(f"MainWindow._update_preview_dialog: エントリ番号 {entry_number} が範囲外 (0-{len(entries)-1})")

        logger.debug("MainWindow._update_preview_dialog: 完了")

    def _show_translation_evaluation_result_dialog(self) -> None:
        """翻訳品質評価結果ダイアログを表示"""
        logger.debug("MainWindow._show_translation_evaluation_result_dialog: 開始")
        
        try:
            # 現在のPOファイルを取得
            current_po = self._get_current_po()
            if not current_po:
                QMessageBox.warning(
                    self, "警告", "POファイルが開かれていません。"
                )
                return
                
            # 現在選択されているエントリの番号を取得
            current_entry_number = self._get_selected_entry_number()
            if current_entry_number is None:
                QMessageBox.warning(
                    self, "警告", "エントリが選択されていません。"
                )
                return
                
            # 選択されたエントリを取得
            current_entry = current_po.get_entry_by_number(current_entry_number)
            if not current_entry:
                QMessageBox.warning(
                    self, "警告", "選択されたエントリを取得できませんでした。"
                )
                return
                
            # 評価結果ウィンドウが既に存在する場合は、それを使用
            if hasattr(self, "_evaluation_result_window") and self._evaluation_result_window:
                logger.debug("MainWindow._show_translation_evaluation_result_dialog: 既存の評価結果ウィンドウを使用")
                self._evaluation_result_window.set_entry(current_entry)
                self._evaluation_result_window.show()
                self._evaluation_result_window.activateWindow()
            else:
                # 新しい評価結果ウィンドウを作成
                logger.debug("MainWindow._show_translation_evaluation_result_dialog: 新しい評価結果ウィンドウを作成")
                from sgpo_editor.gui.translation_evaluate_dialog import TranslationEvaluationResultWindow
                self._evaluation_result_window = TranslationEvaluationResultWindow(current_entry, self)
                self._evaluation_result_window.show()
                
        except Exception as e:
            logger.error(f"MainWindow._show_translation_evaluation_result_dialog: エラー発生 {e}", exc_info=True)
            QMessageBox.critical(
                self, "エラー", f"評価結果ダイアログの表示中にエラーが発生しました: {e}"
            )

    def _get_selected_entry_number(self) -> Optional[int]:
        """現在選択されているエントリの番号を取得する
        
        Returns:
            Optional[int]: 選択されているエントリの番号。選択がない場合はNone
        """
        logger.debug("MainWindow._get_selected_entry_number: 開始")
        
        # 現在選択されているエントリのキーを取得
        entry_key = self.entry_list_facade.get_selected_entry_key()
        if not entry_key:
            logger.debug("MainWindow._get_selected_entry_number: エントリが選択されていません")
            return None
            
        # 現在のPOファイルを取得
        current_po = self._get_current_po()
        if not current_po:
            logger.debug("MainWindow._get_selected_entry_number: POファイルが開かれていません")
            return None
            
        # キーからエントリを取得
        entry = current_po.get_entry_by_key(entry_key)
        if not entry or not hasattr(entry, "position"):
            logger.debug("MainWindow._get_selected_entry_number: エントリが取得できないか、positionがありません")
            return None
            
        logger.debug(f"MainWindow._get_selected_entry_number: エントリ番号={entry.position}を返します")
        return entry.position

def main():
    """アプリケーションのエントリーポイント"""
    app = QApplication(sys.argv)
    app.setApplicationName("PO Editor")

    # 国際化設定
    setup_translator()

    main_window = MainWindow()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
