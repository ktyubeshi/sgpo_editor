"""GUIアプリケーションのエントリーポイント"""

import sys

from PySide6.QtWidgets import QApplication

from sgpo_editor.gui import MainWindow
from sgpo_editor.i18n import setup_translator


def main():
    """アプリケーションを起動"""
    app = QApplication(sys.argv)
    app.setApplicationName("PO Editor")
    
    # 国際化設定
    setup_translator()
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
