"""設定モジュール

このモジュールは、アプリケーションの設定を管理します。
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# デフォルト設定
DEFAULT_CONFIG = {
    # 使用するPOライブラリ（"polib" または "sgpo"）
    "po_library": "sgpo",
    # UIの設定
    "ui": {
        # テーブルの列幅
        "column_widths": {
            "entry_number": 100,
            "msgctxt": 150,
            "msgid": 182,
            "msgstr": 275,
            "status": 107,
            "score": 100,
        },
        # テーブルの列表示/非表示
        "column_visibility": {
            "entry_number": True,
            "msgctxt": True,
            "msgid": True,
            "msgstr": True,
            "status": True,
            "score": True,
        },
        # フォントサイズ
        "font_size": 12,
        # エディタの設定
        "editor": {
            "wrap_text": True,
            "show_line_numbers": True,
            "highlight_syntax": True,
        },
    },
    # 最近使用したファイル
    "recent_files": [],
    # 自動保存の設定
    "auto_save": {
        "enabled": False,
        "interval_minutes": 5,
    },
}


class Config:
    """設定クラス"""

    def __init__(self):
        """初期化"""
        self._config = DEFAULT_CONFIG.copy()
        self._config_path = self._get_config_path()
        self._load_config()

    def _get_config_path(self) -> Path:
        """設定ファイルのパスを取得"""
        # ユーザーのホームディレクトリ
        home_dir = Path.home()

        # プラットフォームに応じた設定ディレクトリ
        if os.name == "nt":  # Windows
            config_dir = home_dir / "AppData" / "Roaming" / "sgpo_editor"
        else:  # macOS, Linux
            config_dir = home_dir / ".config" / "sgpo_editor"

        # 設定ディレクトリが存在しない場合は作成
        config_dir.mkdir(parents=True, exist_ok=True)

        return config_dir / "config.json"

    def _load_config(self) -> None:
        """設定ファイルを読み込む"""
        if not self._config_path.exists():
            logger.info(
                f"設定ファイルが見つかりません。デフォルト設定を使用します: {self._config_path}"
            )
            self._save_config()
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)

            # 読み込んだ設定をデフォルト設定にマージ
            self._merge_config(self._config, loaded_config)
            logger.info(f"設定ファイルを読み込みました: {self._config_path}")
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗しました: {e}")

    def _save_config(self) -> None:
        """設定ファイルを保存する"""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)

            logger.info(f"設定ファイルを保存しました: {self._config_path}")
        except Exception as e:
            logger.error(f"設定ファイルの保存に失敗しました: {e}")

    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """設定を再帰的にマージする

        Args:
            target: マージ先の辞書
            source: マージ元の辞書
        """
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                # 両方が辞書の場合は再帰的にマージ
                self._merge_config(target[key], value)
            else:
                # それ以外の場合は上書き
                target[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得する

        Args:
            key: 設定キー（ドット区切りで階層指定可能）
            default: デフォルト値

        Returns:
            設定値
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """設定値を設定する

        Args:
            key: 設定キー（ドット区切りで階層指定可能）
            value: 設定値
        """
        keys = key.split(".")
        target = self._config

        # 最後のキー以外を処理
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        # 最後のキーを設定
        target[keys[-1]] = value

        # 設定を保存
        self._save_config()

    def add_recent_file(self, file_path: str) -> None:
        """最近使用したファイルを追加する

        Args:
            file_path: ファイルパス
        """
        recent_files = self.get("recent_files", [])

        # 既に存在する場合は削除して先頭に追加
        if file_path in recent_files:
            recent_files.remove(file_path)

        # 先頭に追加
        recent_files.insert(0, file_path)

        # 最大10件まで保持
        recent_files = recent_files[:10]

        # 設定を更新
        self.set("recent_files", recent_files)


# シングルトンインスタンス
_config_instance = None


def get_config() -> Config:
    """設定インスタンスを取得する

    Returns:
        Config: 設定インスタンス
    """
    global _config_instance

    if _config_instance is None:
        _config_instance = Config()

    return _config_instance
