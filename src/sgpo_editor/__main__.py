"""GUIアプリケーションのエントリーポイント"""
import sys
from PySide6.QtWidgets import QApplication
from sgpo_editor.gui import MainWindow

def main():
    """アプリケーションを起動"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
