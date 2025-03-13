"""ファイル処理モジュール

このモジュールは、POファイルの読み込み・保存などのファイル操作に関する機能を提供します。
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from sgpo_editor.core.viewer_po_file import ViewerPOFile

# 循環インポートを避けるために型アノテーションを文字列に変更

logger = logging.getLogger(__name__)

# 最近使用したファイルの最大数
MAX_RECENT_FILES = 10


class FileHandler:
    """ファイル処理クラス"""

    def __init__(
        self,
        parent: QWidget,
        update_stats_callback: Callable[[Dict[str, Any]], None],
        update_table_callback: Callable[[], None],
        status_callback: Callable[[str, int], None],
    ) -> None:
        """初期化

        Args:
            parent: 親ウィジェット
            update_stats_callback: 統計情報更新時のコールバック
            update_table_callback: テーブル更新時のコールバック
            status_callback: ステータス表示用コールバック
        """
        self.parent = parent
        self.current_po: Optional["ViewerPOFile"] = None
        self.current_filepath: Optional[Path] = None
        self._update_stats = update_stats_callback
        self._update_table = update_table_callback
        self._show_status = status_callback
        self.recent_files = self._load_recent_files()

    def _load_recent_files(self) -> List[str]:
        """最近使用したファイルのリストを読み込む

        Returns:
            最近使用したファイルのリスト
        """
        settings = QSettings()
        # セミコロンで連結された文字列として保存されたデータを読み込む
        recent_files_str = settings.value("recent_files_str", "", type=str)

        if not recent_files_str:
            return []

        # セミコロンで分割してリストに変換
        recent_files = recent_files_str.split(";")
        # 空の要素を除去
        recent_files = [f for f in recent_files if f]
        return recent_files

    def _save_recent_files(self) -> None:
        """最近使用したファイルのリストを保存する"""
        settings = QSettings()
        # リストをセミコロンで連結した文字列に変換して保存
        if self.recent_files:
            recent_files_str = ";".join(self.recent_files)
            settings.setValue("recent_files_str", recent_files_str)
            # レガシーサポートのために以前のキーも更新
            settings.setValue("recent_files", self.recent_files)
            # 変更を確実に保存
            settings.sync()

    def add_recent_file(self, filepath: str) -> None:
        """最近使用したファイルを追加する

        Args:
            filepath: ファイルパス
        """
        # 既存のエントリを除去（同じファイルが既にリストにある場合）
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)

        # リストの先頭に追加
        self.recent_files.insert(0, filepath)

        # 最大数を超えた場合、古いものを削除
        if len(self.recent_files) > MAX_RECENT_FILES:
            self.recent_files = self.recent_files[:MAX_RECENT_FILES]

        # 設定に保存
        self._save_recent_files()

    def get_recent_files(self) -> List[str]:
        """最近使用したファイルのリストを取得する

        Returns:
            最近使用したファイルのリスト
        """
        return self.recent_files

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
                    "POファイル (*.po);;すべてのファイル (*.*)",
                )
                if not filepath:
                    return False

            self._show_status(f"ファイルを開いています: {filepath}...", 0)

            # POファイルを開く
            po_file = ViewerPOFile()
            po_file.load(filepath)

            self.current_po = po_file
            self.current_filepath = Path(filepath)

            # 最近使用したファイルに追加
            self.add_recent_file(filepath)

            # 統計情報の更新
            stats = po_file.get_stats()
            self._update_stats(stats)

            # テーブルの更新 - ファイル読み込み直後は重要
            logger.info("ファイル読み込み後のテーブル更新を開始します")
            self._update_table()
            # テーブルの更新が反映されるように処理を確実に実行させる
            QApplication.processEvents()

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
            QMessageBox.warning(self.parent, "警告", "保存するPOファイルがありません。")
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
                # 保存したファイルを最近使用したファイルに追加
                self.add_recent_file(save_path)

            self._show_status(f"ファイルを保存しました: {save_path}", 0)
            self.parent.setWindowTitle(f"PO Editor - {save_path}")
            return True

        except Exception as e:
            logger.error(f"ファイルを保存する際にエラーが発生しました: {e}")
            logger.error(traceback.format_exc())
            QMessageBox.critical(
                self.parent,
                "エラー",
                f"ファイルを保存する際にエラーが発生しました:\n{e}",
            )
            self._show_status(f"エラー: {e}", 0)
            return False

    def save_file_as(self) -> bool:
        """名前を付けて保存する

        Returns:
            成功したかどうか
        """
        if not self.current_po:
            QMessageBox.warning(self.parent, "警告", "保存するPOファイルがありません。")
            return False

        filepath, _ = QFileDialog.getSaveFileName(
            self.parent,
            "名前を付けて保存",
            str(self.current_filepath) if self.current_filepath else "",
            "PO Files (*.po);;All Files (*)",
        )

        if not filepath:
            return False

        return self.save_file(filepath)
