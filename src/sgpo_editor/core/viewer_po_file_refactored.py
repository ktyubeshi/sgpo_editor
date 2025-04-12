"""POファイルビューア (後方互換エイリアス)

このモジュールは後方互換性のためのエイリアスモジュールです。
新しいコードでは直接 viewer_po_file.py の ViewerPOFile を使用してください。

ViewerPOFileRefactored は ViewerPOFile のエイリアスとして定義されており、
リファクタリング後のコードでも既存のインポート文が動作するようになっています。
"""

import logging
from sgpo_editor.core.viewer_po_file import ViewerPOFile

logger = logging.getLogger(__name__)

# 後方互換性のためにViewerPOFileRefactoredをViewerPOFileのエイリアスとして定義
ViewerPOFileRefactored = ViewerPOFile

logger.debug("viewer_po_file_refactored: ViewerPOFileRefactored は ViewerPOFile のエイリアスとして定義されています")
