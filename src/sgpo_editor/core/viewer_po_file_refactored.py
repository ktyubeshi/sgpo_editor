"""リファクタリングされたPOファイルビューア

このモジュールは、POファイルを読み込み、表示、編集するための機能を提供します。
ViewerPOFileクラスをリファクタリングし、キャッシュ管理とデータベースアクセスの責務を分離しています。

責務ごとに分割された各クラスをインポートし、それらを継承した統合クラスを提供します。
このクラスは古いViewerPOFileクラスの完全な代替となり、以下の責務を明確に分離しています:
1. ViewerPOFileBase: 基本的な初期化とPOファイル読み込み機能
2. ViewerPOFileEntryRetriever: エントリ取得関連の機能
3. ViewerPOFileFilter: フィルタリング関連の機能
4. ViewerPOFileUpdater: エントリ更新関連の機能
5. ViewerPOFileStats: 統計情報と保存機能
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.core.po_factory import POLibraryType
from sgpo_editor.core.viewer_po_file_stats import ViewerPOFileStats, Stats
from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.types import FilteredEntriesList

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
    
    このクラスは、古いViewerPOFileクラスの完全な代替として機能し、
    すべての機能を提供しながらも、コードの保守性と拡張性を高めています。
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
    
    def get_all_entries(self) -> List[EntryModel]:
        """すべてのエントリを取得する

        Returns:
            List[EntryModel]: すべてのエントリのリスト
        """
        # データベースからすべてのエントリを取得
        entries_dict = self.db_accessor.get_filtered_entries(
            sort_column="position", sort_order="ASC"
        )
        
        # リストからEntryModelオブジェクトのリストに変換
        entries = [EntryModel.from_dict(entry_dict) for entry_dict in entries_dict]
        
        return entries
    
    def reset_filter(self) -> None:
        """フィルタをリセットする
        
        すべてのフィルタ条件をクリアし、デフォルト状態に戻します。
        """
        self.set_filter(
            search_text="",
            sort_column="position",
            sort_order="ASC",
            flag_conditions={},
            translation_status=None
        )
        
        # フィルタリング結果を強制的に更新
        self._force_filter_update = True
        self.filtered_entries = []
    
    def is_loaded(self) -> bool:
        """ファイルが読み込まれているかを返す
        
        Returns:
            bool: ファイルが読み込まれている場合はTrue
        """
        return self._is_loaded
    
    def is_modified(self) -> bool:
        """ファイルが変更されているかを返す
        
        Returns:
            bool: ファイルが変更されている場合はTrue
        """
        return self.modified
    
    def set_modified(self, modified: bool = True) -> None:
        """変更フラグを設定する
        
        Args:
            modified: 設定する変更フラグの値
        """
        self.modified = modified
