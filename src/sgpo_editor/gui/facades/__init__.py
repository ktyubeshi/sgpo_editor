"""ファサードパッケージ

このパッケージは、複雑なコンポーネント間の相互作用をカプセル化し、
よりシンプルなインターフェイスを提供するファサードクラスを提供します。
"""

from sgpo_editor.gui.facades.entry_editor_facade import EntryEditorFacade
from sgpo_editor.gui.facades.entry_list_facade import EntryListFacade

__all__ = ["EntryEditorFacade", "EntryListFacade"]
