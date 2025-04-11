"""ViewerPOFile モジュール

このモジュールは、ViewerPOFileRefactored を ViewerPOFile として再エクスポートします。
"""

from sgpo_editor.core.viewer_po_file_refactored import ViewerPOFileRefactored

ViewerPOFile = ViewerPOFileRefactored

__all__ = ["ViewerPOFile"]
