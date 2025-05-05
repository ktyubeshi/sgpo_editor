"""GUIモデルパッケージ

このパッケージは、共通のモデルを sgpo_editor.models から再エクスポートします。
"""

from sgpo_editor.models import EntryModel, StatsModel

__all__ = ["EntryModel", "StatsModel"]
