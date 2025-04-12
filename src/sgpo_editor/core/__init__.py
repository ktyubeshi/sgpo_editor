"""GUIアプリケーション用のコアモジュール"""

from sgpo_editor.core.viewer_po_file import ViewerPOFile

# 古い実装との後方互換性のためのエイリアス
ViewerPOFileRefactored = ViewerPOFile

__all__ = ["ViewerPOFile", "ViewerPOFileRefactored"]
