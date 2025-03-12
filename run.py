"""POビューワーの起動スクリプト"""
import logging
import sys
import os
from pathlib import Path

# srcディレクトリをPYTHONPATHに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# データディレクトリ作成
(Path(__file__).parent / "data").mkdir(exist_ok=True)

# ロギング設定
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "po_viewer.log"

logging.basicConfig(
    level=logging.DEBUG,  # CRITICALからDEBUGに変更してデバッグ情報を表示
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Qt設定
from PySide6.QtCore import QCoreApplication, QSettings
QCoreApplication.setOrganizationName("SGPO")
QCoreApplication.setApplicationName("POEditor")

from sgpo_editor.gui.main_window import main

if __name__ == "__main__":
    main()
