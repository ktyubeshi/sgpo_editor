"""ファイル処理モジュール

このモジュールは、POファイルの読み込み・保存などのファイル操作に関する機能を提供します。
"""

import logging
import traceback
from pathlib import Path
from typing import Optional, Callable, Dict, Any

from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox

from sgpo_editor.core.viewer_po_file import ViewerPOFile

logger = logging.getLogger(__name__)


class FileHandler:
    """ファイル処理クラス"""

    def __init__(self, parent: QWidget, update_stats_callback: Callable[[Dict[str, Any]], None],
                update_table_callback: Callable[[], None], status_callback: Callable[[str, int], None]) -> None:
        """初期化

        Args:
            parent: 親ウィジェット
            update_stats_callback: 統計情報更新時のコールバック
            update_table_callback: テーブル更新時のコールバック
            status_callback: ステータス表示用コールバック
        """
        self.parent = parent
        self.current_po: Optional[ViewerPOFile] = None
        self.current_filepath: Optional[Path] = None
        self._update_stats = update_stats_callback
        self._update_table = update_table_callback
        self._show_status = status_callback

    def open_file(self, filepath: Optional[str] = None) -> bool:
        """POファイルを開く

        Args:
            filepath: ファイルパス（省略時はダイアログを表示）

        Returns:
            成功したかどうか
        """
        try:
            # ファイルパスの取得
            if not filepath:
                filepath, _ = QFileDialog.getOpenFileName(
                    self.parent,
                    "POファイルを開く",
                    "",
                    "POファイル (*.po);;すべてのファイル (*.*)"
                )
                if not filepath:
                    return False
                    
            self._show_status(f"ファイルを開いています: {filepath}...", 0)
            
            # POファイルを開く
            po_file = ViewerPOFile(filepath)
            
            self.current_po = po_file
            self.current_filepath = Path(filepath)
            
            # 統計情報の更新
            stats = po_file.get_stats()
            self._update_stats(stats)
            
            # テーブルの更新
            self._update_table()
            
            # ウィンドウタイトルの更新
            if hasattr(self.parent, "setWindowTitle"):
                self.parent.setWindowTitle(f"PO Viewer - {Path(filepath).name}")
                
            self._show_status(f"ファイルを開きました: {filepath}", 3000)
            return True
            
        except Exception as e:
            logger.error("ファイルを開く際にエラーが発生しました: %s", e)
            logger.error(traceback.format_exc())
            self._show_status(f"ファイルを開けませんでした: {e}", 3000)
            return False

    def save_file(self, filepath: Optional[str] = None) -> bool:
        """POファイルを保存する

        Args:
            filepath: ファイルパス（省略時は現在のファイルに上書き）

        Returns:
            成功したかどうか
        """
        if not self.current_po:
            QMessageBox.warning(
                self.parent,
                "警告",
                "保存するPOファイルがありません。"
            )
            return False
            
        try:
            if not filepath and not self.current_filepath:
                return self.save_file_as()
                
            save_path = filepath or str(self.current_filepath)
            self._show_status(f"ファイルを保存しています: {save_path}...", 0)
            
            # POファイルを保存
            self.current_po.save(save_path)
            
            if filepath:
                self.current_filepath = Path(filepath)
                
            self._show_status(f"ファイルを保存しました: {save_path}", 0)
            self.parent.setWindowTitle(f"PO Editor - {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"ファイルを保存する際にエラーが発生しました: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(
                self.parent,
                "エラー",
                f"ファイルを保存する際にエラーが発生しました:\n{e}"
            )
            self._show_status(f"エラー: {e}", 0)
            return False

    def save_file_as(self) -> bool:
        """名前を付けて保存する

        Returns:
            成功したかどうか
        """
        if not self.current_po:
            QMessageBox.warning(
                self.parent,
                "警告",
                "保存するPOファイルがありません。"
            )
            return False
            
        filepath, _ = QFileDialog.getSaveFileName(
            self.parent, "名前を付けて保存", 
            str(self.current_filepath) if self.current_filepath else "",
            "PO Files (*.po);;All Files (*)"
        )
        
        if not filepath:
            return False
            
        return self.save_file(filepath)
