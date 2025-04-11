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

継承チェーン:
ViewerPOFileBase <- ViewerPOFileEntryRetriever <- ViewerPOFileFilter <- ViewerPOFileUpdater <- ViewerPOFileStats
"""

import logging
from typing import Dict, List, Optional, Union, Set, cast
from pathlib import Path

from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import EntryDict, EntryDictList, FilterSettings
from sgpo_editor.core.po_factory import POLibraryType
from sgpo_editor.core.viewer_po_file_stats import ViewerPOFileStats
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

    このクラスは、古いViewerPOFileクラスの完全な代替として機能し、
    すべての機能を提供しながらも、コードの保守性と拡張性を高めています。
    
    依存性注入パターンによりDatabaseAccessorとEntryCacheManagerを外部から注入できるため、
    - 単体テストが容易になる（モックやスタブの使用が可能）
    - 異なるデータベース実装やキャッシュ戦略への切り替えが容易
    - 実行時の設定に応じた振る舞いの変更が可能
    になっています。
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
            
        外部からDatabaseAccessorとEntryCacheManagerを注入可能な設計になっており、
        テスト時にはモックやスタブを使用して依存関係を置き換えることができます。
        """
        # 親クラスの初期化
        super().__init__(library_type, db_accessor, cache_manager)

        logger.debug("ViewerPOFileRefactored: 初期化完了")

    async def load(self, path: Union[str, Path]) -> None:
        """POファイルを非同期で読み込む

        Args:
            path: 読み込むPOファイルのパス
            
        このメソッドはsuper().load()を呼び出し、ViewerPOFileBase.loadメソッドの機能を使用します。
        非同期で動作し、UIのブロックを防ぎながらPOファイルを読み込みます。
        """
        # 親クラスのload()メソッドを非同期で呼び出す
        await super().load(path)
        logger.debug(f"ViewerPOFileRefactored.load: {path} の読み込みが完了しました")

    def get_all_entries(self) -> List[EntryModel]:
        """すべてのエントリを取得する

        データベースから全エントリを位置順に取得し、EntryModelリストとして返します。
        キャッシュは使用せず、常に最新のデータを返します。

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
        また、キャッシュマネージャのフィルタキャッシュも無効化します。
        """
        self.set_filter(
            search_text="",
            sort_column="position",
            sort_order="ASC",
            flag_conditions={},
            translation_status=None,
        )

        # フィルタリング結果を強制的に更新（キャッシュマネージャ経由）
        if self.cache_manager:
            self.cache_manager.set_force_filter_update(True)
            self.cache_manager.invalidate_filter_cache()
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

    def get_entry(self, key: str) -> Optional[EntryModel]:
        """エントリキーからエントリを取得する (従来メソッドとの互換性用)

        Args:
            key: エントリキー

        Returns:
            Optional[EntryModel]: 見つかったエントリ、または None
        """
        return self.get_entry_by_key(key)

    def get_entry_position(self, position: int) -> Optional[EntryModel]:
        """エントリ番号からエントリを取得する (従来メソッドとの互換性用)

        Args:
            position: エントリ番号

        Returns:
            Optional[EntryModel]: 見つかったエントリ、または None
        """
        return self.get_entry_at(position)

    def count_entries(self) -> int:
        """全エントリ数を取得する

        Returns:
            int: エントリの総数
        """
        return self.db_accessor.count_entries() if self.db_accessor else 0

    def get_available_flags(self) -> Set[str]:
        """利用可能なすべてのフラグのセットを取得する

        Returns:
            Set[str]: 利用可能なフラグのセット
        """
        if not self.db_accessor:
            return set()
        return self.db_accessor.get_all_flags()

    def get_filters(self) -> FilterSettings:
        """現在のフィルタ設定を取得する

        Returns:
            FilterSettings: 現在のフィルタ設定
        """
        return {
            "search_text": self.search_text,
            "sort_column": self.sort_column,
            "sort_order": self.sort_order,
            "flag_conditions": self.flag_conditions.copy() if self.flag_conditions else {},
            "translation_status": self.translation_status,
        }

    def invalidate_cache(self) -> None:
        """キャッシュを無効化する

        フィルタリング結果とキャッシュマネージャのキャッシュを無効化し、
        次回のget_filtered_entriesでフィルタ再計算を強制します。
        """
        logger.debug("ViewerPOFileRefactored.invalidate_cache: キャッシュ無効化")
        if self.cache_manager:
            self.cache_manager.set_force_filter_update(True)
            self.cache_manager.clear_cache()
        self.filtered_entries = []
        
    def prefetch_entries(self, keys: List[str]) -> None:
        """指定されたキーのエントリをプリフェッチする
        
        Args:
            keys: プリフェッチするエントリのキーのリスト
        """
        if not self.cache_manager or not self.db_accessor or not keys:
            return
            
        logger.debug(f"ViewerPOFileRefactored.prefetch_entries: {len(keys)}件のエントリをプリフェッチ")
        
        self.cache_manager.prefetch_visible_entries(
            keys,
            fetch_callback=self._fetch_entries_by_keys
        )
        
    def _fetch_entries_by_keys(self, keys: List[str]) -> List[EntryModel]:
        """指定されたキーのエントリをデータベースから取得する
        
        Args:
            keys: 取得するエントリのキーのリスト
            
        Returns:
            List[EntryModel]: 取得したエントリのリスト
        """
        if not self.db_accessor or not keys:
            return []
            
        try:
            entries_dict = self.db_accessor.get_entries_by_keys(keys)
            
            entries = [EntryModel.from_dict(cast(EntryDict, entry_dict)) for entry_dict in entries_dict]
            
            return entries
        except Exception as e:
            logger.error(f"エントリ取得中にエラーが発生: {e}")
            return []

    def get_unique_msgid_count(self) -> int:
        """一意のmsgid数を取得する

        Returns:
            int: 一意のmsgidの数
        """
        if not self.db_accessor:
            return 0
        return self.db_accessor.get_unique_msgid_count()

    def get_filename(self) -> str:
        """現在のファイル名を取得する

        Returns:
            str: ファイル名
        """
        if not self.path:
            return ""
        return Path(self.path).name
