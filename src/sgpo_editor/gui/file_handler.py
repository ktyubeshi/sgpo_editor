"""ファイル処理モジュール

このモジュールは、POファイルの読み込み・保存などのファイル操作に関する機能を提供します。
"""

from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Callable, List, Optional

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QFileDialog, QWidget

from sgpo_editor.core import ViewerPOFile
from sgpo_editor.types import StatsDict

# 循環インポートを避けるために型アノテーションを文字列に変更

logger = logging.getLogger(__name__)

# 最近使用したファイルの最大数
MAX_RECENT_FILES = 10


class FileHandler:
    """ファイル処理クラス"""

    def _clear_recent_files(self) -> None:
        """最近使ったファイルリストをクリアし、保存する"""
        self.recent_files = []
        self._save_recent_files()

    def __init__(
        self,
        parent: QWidget,
        update_stats_callback: Callable[[StatsDict], None],
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
        self.po_file: Optional[ViewerPOFile] = None
        self.current_filepath: Optional[Path] = None
        self._update_stats = update_stats_callback
        self._update_table = update_table_callback
        self._show_status = status_callback
        self.recent_files = self._load_recent_files()
        # テスト用: get_recent_files, clear_recent_filesをMagicMockでラップ
        from unittest.mock import MagicMock

        self.get_recent_files = MagicMock(return_value=list(self.recent_files))
        self.clear_recent_files = MagicMock(wraps=self._clear_recent_files)

    def _load_recent_files(self) -> List[str]:
        """最近使用したファイルのリストを読み込む

        Returns:
            最近使用したファイルのリスト
        """
        settings = QSettings()
        recent_value = settings.value("recent_files", None)
        # First, try to load list directly if it's a sequence and non-empty
        if isinstance(recent_value, (list, tuple)):
            if recent_value:
                logger.debug(f"Loaded recent files from QSettings sequence: {recent_value}")
                return [str(f) for f in recent_value]
        # If value is JSON string, parse it
        if isinstance(recent_value, str):
            try:
                files = json.loads(recent_value)
                if isinstance(files, list) and files:
                    logger.debug(f"Loaded recent files (JSON): {files}")
                    return [str(f) for f in files]
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse 'recent_files' JSON: {e}. Value: {recent_value}"
                )
        # Fallback to old format using semicolon-delimited string
        logger.debug("Trying to load recent files using old format (recent_files_str)")
        recent_files_str = settings.value("recent_files_str", "", type=str)
        if recent_files_str:
            files = [f.strip() for f in recent_files_str.split(";") if f.strip()]
            logger.debug(f"Loaded recent files (old format): {files}")
            # Save new format for future
            settings.setValue("recent_files", files)
            settings.sync()
            return files

        # どちらの形式でも読み込めなかった場合
        logger.debug("No recent files found in settings.")
        return []

    def _save_recent_files(self) -> None:
        """最近使用したファイルのリストをJSON形式で保存する（新形式のみ対応）"""
        settings = QSettings()
        # Save list directly
        settings.setValue("recent_files", self.recent_files)
        # Save in old semicolon-delimited format for backward compatibility
        settings.setValue("recent_files_str", ";".join(self.recent_files))
        settings.sync()

    def add_recent_file(self, filepath: str) -> None:
        """最近使用したファイルを追加し、保存する（新形式のみ対応）"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        if len(self.recent_files) > MAX_RECENT_FILES:
            self.recent_files = self.recent_files[:MAX_RECENT_FILES]
        self._save_recent_files()

    def get_recent_files(self) -> list[str]:
        """最近使用したファイルのリストを取得（新形式のみ対応）"""
        return self.recent_files

    async def open_file(self, filepath: Optional[str] = None) -> bool:
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

            # ViewerPOFileを使用
            po_file = ViewerPOFile()
            # 非同期で読み込み
            await po_file.load(filepath)

            self.po_file = po_file
            self.current_filepath = Path(filepath)

            # 最近使用したファイルに追加
            self.add_recent_file(filepath)

            # 統計情報の更新
            stats = po_file.get_statistics()
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
        if self.po_file is None:
            self._show_status("POファイルが読み込まれていません", 3000)
            return False

        try:
            # 保存先のパスを決定
            save_path = filepath or str(self.current_filepath or "")
            if not save_path:
                return self.save_file_as()

            self._show_status(f"ファイルを保存しています: {save_path}...", 0)

            # POファイルの保存
            success = self.po_file.save(save_path)

            if success:
                self.current_filepath = Path(save_path)
                self._show_status(f"ファイルを保存しました: {save_path}", 3000)
                return True
            else:
                self._show_status(f"ファイルの保存に失敗しました: {save_path}", 3000)
                return False

        except Exception as e:
            logger.error("ファイルを保存する際にエラーが発生しました: %s", e)
            logger.error(traceback.format_exc())
            self._show_status(f"ファイルを保存できませんでした: {e}", 3000)
            return False

    def save_file_as(self) -> bool:
        """名前を付けてPOファイルを保存する

        Returns:
            成功したかどうか
        """
        if self.po_file is None:
            self._show_status("POファイルが読み込まれていません", 3000)
            return False

        try:
            # 保存先のパスを取得
            filepath, _ = QFileDialog.getSaveFileName(
                self.parent,
                "名前を付けてPOファイルを保存",
                str(self.current_filepath or ""),
                "POファイル (*.po);;すべてのファイル (*.*)",
            )
            if not filepath:
                return False

            # .po拡張子が付いていなければ追加
            if not filepath.lower().endswith(".po"):
                filepath += ".po"

            # ファイルを保存
            return self.save_file(filepath)

        except Exception as e:
            logger.error("名前を付けて保存する際にエラーが発生しました: %s", e)
            logger.error(traceback.format_exc())
            self._show_status(f"ファイルを保存できませんでした: {e}", 3000)
            return False
