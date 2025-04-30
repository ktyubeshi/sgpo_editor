"""GUIアプリケーション用のコアモジュール"""

from sgpo_editor.core.viewer_po_file import ViewerPOFile
# 後方互換性エイリアスを維持
ViewerPOFileRefactored = ViewerPOFile
__all__ = ["ViewerPOFile", "ViewerPOFileRefactored"]
