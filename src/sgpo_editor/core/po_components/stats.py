"""POファイル統計コンポーネント

このモジュールは、POファイルの統計情報の計算と保存機能を提供します。
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union, Tuple

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.po_factory import get_po_factory, POLibraryType
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import StatisticsInfo

logger = logging.getLogger(__name__)


class StatsComponent:
    """POファイルの統計と保存機能を提供するコンポーネント

    このクラスは、POファイルの統計情報を計算し、ファイルを保存する責務を持ちます。
    """

    def __init__(
        self,
        db_accessor: DatabaseAccessor,
        cache_manager: EntryCacheManager,
        library_type: POLibraryType = POLibraryType.SGPO,
    ):
        """初期化

        Args:
            db_accessor: データベースアクセサのインスタンス
            cache_manager: キャッシュマネージャのインスタンス
            library_type: 使用するPOライブラリの種類
        """
        self.db_accessor = db_accessor
        self.cache_manager = cache_manager
        self.library_type = library_type
        self.path = None
        self.metadata = {}
        logger.debug("StatsComponent: 初期化完了")

    def set_path(self, path: Optional[Union[str, Path]]) -> None:
        """POファイルのパスを設定する

        Args:
            path: POファイルのパス
        """
        self.path = Path(path) if path else None

    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """POファイルのメタデータを設定する

        Args:
            metadata: POファイルのメタデータ
        """
        self.metadata = metadata.copy() if metadata else {}

    def get_statistics(self) -> StatisticsInfo:
        """翻訳統計情報を取得する

        Returns:
            StatisticsInfo: 統計情報を含む辞書
        """
        if not self.db_accessor:
            return {
                "total": 0,
                "translated": 0,
                "untranslated": 0,
                "fuzzy": 0,
                "obsolete": 0,
                "percent_translated": 0.0,
            }

        # 総エントリ数
        total = self.db_accessor.count_entries()
        # 翻訳済みエントリ数 (msgstrが空でないもの)
        translated = self.db_accessor.count_entries_with_condition(
            {"field": "msgstr", "value": "", "operator": "!="}
        )
        # 未翻訳エントリ数 (msgstrが空のもの)
        untranslated = self.db_accessor.count_entries_with_condition(
            {"field": "msgstr", "value": "", "operator": "="}
        )
        # fuzzyフラグ付きエントリ数
        fuzzy = self.db_accessor.count_entries_with_flag("fuzzy")
        # obsoleteフラグ付きエントリ数
        obsolete = self.db_accessor.count_entries_with_condition(
            {"field": "obsolete", "value": True, "operator": "="}
        )

        # 翻訳率の計算 (0除算対策)
        percent_translated = (translated / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "translated": translated,
            "untranslated": untranslated,
            "fuzzy": fuzzy,
            "obsolete": obsolete,
            "percent_translated": percent_translated,
        }

    def count_entries_with_flag(self, flag: str) -> int:
        """特定のフラグを持つエントリの数を取得する

        Args:
            flag: カウントするフラグ名

        Returns:
            int: 指定されたフラグを持つエントリの数
        """
        if not self.db_accessor:
            return 0
        return self.db_accessor.count_entries_with_flag(flag)

    def get_flag_statistics(self) -> Dict[str, int]:
        """すべてのフラグの統計情報を取得する

        Returns:
            Dict[str, int]: フラグ名とそのフラグを持つエントリ数の辞書
        """
        if not self.db_accessor:
            return {}

        result = {}
        all_flags = self.db_accessor.get_all_flags()
        
        for flag in all_flags:
            count = self.db_accessor.count_entries_with_flag(flag)
            result[flag] = count
            
        return result

    async def save(self, path: Optional[Union[str, Path]] = None) -> bool:
        """POファイルを保存する

        Args:
            path: 保存先のパス (Noneの場合は現在のパスを使用)

        Returns:
            bool: 保存が成功した場合はTrue、失敗した場合はFalse
        """
        save_path = Path(path) if path else self.path
        if not save_path:
            logger.error("保存先のパスが指定されていません")
            return False

        start_time = time.time()
        logger.debug(f"StatsComponent.save: POファイル保存開始 path={save_path}")

        try:
            # エントリの取得（データベースから全エントリを取得）
            entries_dict = self.db_accessor.get_all_entries()
            
            # POファイルファクトリを取得
            factory = get_po_factory(self.library_type)
            
            # POファイルを作成
            pofile = factory.create_new_file()
            
            # メタデータを設定
            if self.metadata:
                for key, value in self.metadata.items():
                    pofile.metadata[key] = value
            
            # エントリをPOファイルに追加
            for entry_dict in entries_dict:
                po_entry = factory.create_entry_from_dict(entry_dict)
                pofile.append(po_entry)
            
            # 非同期でファイルを保存
            await factory.save_file_async(pofile, save_path)
            
            elapsed_time = time.time() - start_time
            logger.debug(f"StatsComponent.save: POファイル保存完了 ({elapsed_time:.2f}秒)")
            return True
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"StatsComponent.save: POファイル保存エラー ({elapsed_time:.2f}秒): {str(e)}")
            logger.exception(e)
            return False

    def get_entry_counts_by_type(self) -> Dict[str, int]:
        """タイプ別のエントリ数を取得する

        Returns:
            Dict[str, int]: タイプとエントリ数の辞書
        """
        if not self.db_accessor:
            return {
                "singular": 0,
                "plural": 0,
                "with_context": 0,
            }

        # 単数形エントリ（msgid_pluralがないもの）
        singular = self.db_accessor.count_entries_with_condition(
            {"field": "msgid_plural", "value": None, "operator": "="}
        )
        
        # 複数形エントリ（msgid_pluralがあるもの）
        plural = self.db_accessor.count_entries_with_condition(
            {"field": "msgid_plural", "value": None, "operator": "!="}
        )
        
        # コンテキスト付きエントリ（msgctxtがあるもの）
        with_context = self.db_accessor.count_entries_with_condition(
            {"field": "msgctxt", "value": None, "operator": "!="}
        )

        return {
            "singular": singular,
            "plural": plural,
            "with_context": with_context,
        } 