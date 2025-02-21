"""GUIアプリケーションのエントリーポイント"""
# 共通オプション
# nuitka-project: --standalone
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --follow-imports
# nuitka-project: --include-package-data=sgpo_editor
# nuitka-project: --noinclude-qt-translations
# nuitka-project: --product-name="SGPO Editor"
# nuitka-project: --product-version=0.1.0
# nuitka-project: --file-description="""A tool for viewing and checking PO
#    (gettext) files"""
# nuitka-project: --copyright="Copyright (c) 2024"

# プラットフォーム固有のオプション
# nuitka-project-if: {OS} == "Windows":
#    nuitka-project: --windows-icon-from-ico=resources/app.ico
#    nuitka-project: --output-dir=build/windows-{ARCH}
#    nuitka-project: --output-filename=sgpo_editor.exe
#    nuitka-project: --windows-company-name=SGPO
#    nuitka-project: --windows-product-version=0.1.0.0
#    nuitka-project: --windows-file-version=0.1.0.0

# nuitka-project-if: {OS} == "Darwin":
#    nuitka-project: --macos-create-app-bundle
#    nuitka-project: --macos-app-icon=resources/app.icns
#    nuitka-project: --macos-app-name="SGPO Editor"
#    nuitka-project: --output-dir=build/macos-{ARCH}
#    nuitka-project: --output-filename=sgpo_editor
#    nuitka-project: --macos-signed-app
#    nuitka-project: --macos-target-arch=x86_64,arm64

# nuitka-project-if: {OS} == "Linux":
#    nuitka-project: --linux-icon=resources/app.png
#    nuitka-project: --output-dir=build/linux-{ARCH}
#    nuitka-project: --output-filename=sgpo_editor

# デバッグビルド設定
# nuitka-project-if: os.getenv("DEBUG_COMPILATION", "no") == "yes":
#    nuitka-project: --enable-console
#    nuitka-project: --debug
#    nuitka-project: --unstripped
#    nuitka-project: --output-dir=build/debug-{OS}-{ARCH}

import sys
from PySide6.QtWidgets import QApplication
from .gui import MainWindow


def main():
    """アプリケーションを起動"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
