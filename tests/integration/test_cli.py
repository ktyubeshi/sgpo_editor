import importlib
import sys
import types
from pathlib import Path


def test_po_editor_cli_basic(tmp_path, monkeypatch, capsys):
    module = types.ModuleType("sgpo_editor.core.sgpo_adapter")

    class DummySgpoFile:
        def __init__(self, path: Path):
            self.path = Path(path)

        def get_stats(self):
            return {
                "file_name": self.path.name,
                "total": 1,
                "translated": 1,
                "untranslated": 0,
                "fuzzy": 0,
                "progress": 100.0,
            }

    module.SgpoFile = DummySgpoFile
    monkeypatch.setitem(sys.modules, "sgpo_editor.core.sgpo_adapter", module)

    cli = importlib.import_module("sgpo_editor.cli")
    po_file = tmp_path / "example.po"
    po_file.write_text("msgid \"\"\nmsgstr \"\"\n")

    monkeypatch.setattr(sys, "argv", ["po_editor-cli", str(po_file)])
    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert f"ファイル: {po_file.name}" in captured.out
