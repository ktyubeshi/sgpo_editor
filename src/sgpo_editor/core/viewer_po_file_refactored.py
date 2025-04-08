"""リファクタリングされたPOファイルビューア

このモジュールは、POファイルを読み込み、表示、編集するための機能を提供します。
ViewerPOFileクラスをリファクタリングし、キャッシュ管理とデータベースアクセスの責務を分離しています。

責務ごとに分割された各クラスをインポートし、それらを継承した統合クラスを提供します。
"""

import logging
import asyncio
from typing import Optional, Union
from pathlib import Path

from sgpo_editor.core.po_factory import POLibraryType
from sgpo_editor.core.viewer_po_file_stats import ViewerPOFileStats, Stats
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor

logger = logging.getLogger(__name__)


class ViewerPOFileRefactored(ViewerPOFileStats):
    """POファイルを読み込み、表示するためのリファクタリングされたクラス

    このクラスは、キャッシュ管理とデータベースアクセスの責務を分離し、
    EntryCacheManagerとDatabaseAccessorを利用して実装されています。
    
    責務ごとに分割された以下のクラスを継承しています：
    - ViewerPOFileBase: 基本的な初期化とPOファイル読み込み機能
    - ViewerPOFileEntryRetriever: エントリ取得関連の機能
    - ViewerPOFileFilter: フィルタリング関連の機能
    - ViewerPOFileUpdater: エントリ更新関連の機能
    - ViewerPOFileStats: 統計情報と保存機能
    """

    def __init__(
        self,
        library_type: Optional[POLibraryType] = POLibraryType.SGPO,
        db_accessor: Optional[DatabaseAccessor] = None,
        cache_manager: Optional[EntryCacheManager] = None,
    ):
        """初期化

        Args:
            library_type: 使用するPOライブラリの種類
            db_accessor: データベースアクセサのインスタンス（省略時は内部で生成）
            cache_manager: キャッシュマネージャのインスタンス（省略時は内部で生成）
        """
        # 親クラスの初期化
        super().__init__(library_type, db_accessor, cache_manager)
        
        logger.debug("ViewerPOFileRefactored: 初期化完了")

    async def load(self, path: Union[str, Path]) -> None:
        """POファイルを非同期で読み込む

        Args:
            path: 読み込むPOファイルのパス
        """
        # 親クラスのload()メソッドを非同期で呼び出す
        await super().load(path)
        logger.debug(f"ViewerPOFileRefactored.load: {path} の読み込みが完了しました")
