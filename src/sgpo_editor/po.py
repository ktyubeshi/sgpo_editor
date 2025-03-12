"""POファイル操作モジュール"""

import sys
from pathlib import Path
from typing import Optional

from po_viewer.gui.main_window import MainWindow
from PySide6.QtWidgets import QApplication
from rich.console import Console
from rich.table import Table

import sgpo

console = Console()


class PoFile:
    """POファイルを扱うクラス"""

    def __init__(self, file_path: str | Path):
        """
        POファイルを読み込む

        Args:
            file_path: POファイルのパス
        """
        self.file_path = Path(file_path)
        self.po = sgpo.pofile(str(self.file_path))
        self._modified = False

    @property
    def modified(self) -> bool:
        """変更されているかどうか"""
        return self._modified

    def save(self, file_path: str | Path | None = None) -> None:
        """POファイルを保存する

        Args:
            file_path: 保存先のパス。Noneの場合は元のファイルに上書き保存
        """
        save_path = Path(file_path) if file_path else self.file_path
        self.po.save(str(save_path))
        self._modified = False

        # 別名で保存した場合は、そのファイルを新しい作業ファイルとする
        if file_path:
            self.file_path = save_path

    def set_msgstr(self, entry, msgstr: str) -> None:
        """翻訳文を設定する

        Args:
            entry: 翻訳エントリ
            msgstr: 翻訳文
        """
        if entry.msgstr != msgstr:
            entry.msgstr = msgstr
            self._modified = True

    def display_summary(self):
        """POファイルの概要を表示"""
        table = Table(title=f"PO File: {self.file_path.name}")

        table.add_column("項目", style="cyan")
        table.add_column("値", style="green")

        table.add_row("総エントリ数", str(len(self.po)))
        table.add_row("翻訳済み", str(len(self.po.translated_entries())))
        table.add_row("未翻訳", str(len(self.po.untranslated_entries())))
        table.add_row("ファジー", str(len(self.po.fuzzy_entries())))

        console.print(table)

    def display_entries(self, filter_type: Optional[str] = None):
        """
        POファイルのエントリを表示

        Args:
            filter_type: 表示するエントリの種類（'translated', 'untranslated', 'fuzzy'）
        """
        entries = {
            "translated": self.po.translated_entries,
            "untranslated": self.po.untranslated_entries,
            "fuzzy": self.po.fuzzy_entries,
        }.get(filter_type, lambda: self.po)()

        table = Table(title=f"エントリ一覧 ({filter_type or 'all'})")
        table.add_column("msgid", style="cyan", no_wrap=True)
        table.add_column("msgstr", style="green", no_wrap=True)
        table.add_column("状態", style="yellow")

        for entry in entries:
            status = []
            if entry.fuzzy:
                status.append("fuzzy")
            if not entry.msgstr:
                status.append("未翻訳")
            if entry.msgstr:
                status.append("翻訳済")

            table.add_row(
                str(entry.msgid)[:50] + ("..." if len(str(entry.msgid)) > 50 else ""),
                str(entry.msgstr)[:50] + ("..." if len(str(entry.msgstr)) > 50 else ""),
                ", ".join(status),
            )

        console.print(table)


"""アプリケーションのエントリポイント"""


def main():
    """アプリケーションを実行"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
        if file_path.exists():
            window.open_file(str(file_path))

    sys.exit(app.exec())
