"""POファイルエントリ取得コンポーネント

このモジュールは、POファイルからエントリを取得するための機能を提供します。
"""

import logging
from typing import Dict, List, Optional

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class EntryRetrieverComponent:
    """エントリ取得機能を提供するコンポーネント

    このクラスは、DatabaseAccessorとEntryCacheManagerを使用して、
    エントリの取得と管理の責務を持ちます。
    """

    def __init__(
        self,
        db_accessor: DatabaseAccessor,
        cache_manager: EntryCacheManager,
    ):
        """初期化

        Args:
            db_accessor: データベースアクセサのインスタンス
            cache_manager: キャッシュマネージャのインスタンス
        """
        self.db_accessor = db_accessor
        self.cache_manager = cache_manager
        logger.debug("EntryRetrieverComponent: 初期化完了")

    def get_entry_by_key(self, key: str) -> Optional[EntryModel]:
        """キーでエントリを取得する（キャッシュ対応）

        指定されたキーに対応するエントリを取得します。キャッシュが有効な場合、
        まず完全なエントリキャッシュを確認し、次に基本情報キャッシュを確認し、
        最後にデータベースから取得します。

        Args:
            key: 取得するエントリのキー

        Returns:
            EntryModel: エントリモデルオブジェクト、存在しない場合はNone
        """
        logger.debug(
            f"EntryRetrieverComponent.get_entry_by_key: キー={key}のエントリを取得"
        )

        # キャッシュからエントリを取得
        entry = self.cache_manager.get_entry(key)
        if entry:
            logger.debug(
                f"EntryRetrieverComponent.get_entry_by_key: キャッシュヒット key={key}"
            )
            return entry

        # データベースからエントリを取得
        entry_dict = self.db_accessor.get_entry_by_key(key)
        if entry_dict:
            # EntryModelオブジェクトに変換
            entry = EntryModel.from_dict(entry_dict)
            # キャッシュに追加
            self.cache_manager.set_entry(key, entry)
            return entry

        logger.debug(
            f"EntryRetrieverComponent.get_entry_by_key: エントリが見つかりません key={key}"
        )
        return None

    def get_entries_by_keys(self, keys: List[str]) -> Dict[str, EntryModel]:
        """複数のキーに対応するエントリを一度に取得

        指定された複数のキーに対応するエントリを取得します。
        キャッシュから取得できるエントリはキャッシュから、それ以外はデータベースから一括取得します。

        Args:
            keys: 取得するエントリのキーのリスト

        Returns:
            Dict[str, EntryModel]: キーとエントリモデルの辞書
        """
        logger.debug(f"EntryRetrieverComponent.get_entries_by_keys: キー数={len(keys)}")
        result = {}

        # キャッシュにあるエントリを取得
        cached_entries = {}
        missing_keys = []
        for key in keys:
            entry = self.cache_manager.get_entry(key)
            if entry:
                cached_entries[key] = entry
            else:
                missing_keys.append(key)

        # キャッシュにないエントリをデータベースから一括取得
        if missing_keys:
            db_entries = self.db_accessor.get_entries_by_keys(missing_keys)
            for key, entry_dict in db_entries.items():
                # EntryModelオブジェクトに変換
                entry = EntryModel.from_dict(entry_dict)
                # キャッシュに追加
                self.cache_manager.set_entry(key, entry)
                result[key] = entry

        # キャッシュから取得したエントリを結果に追加
        result.update(cached_entries)

        return result

    def get_entry_basic_info(self, key: str) -> Optional[EntryModel]:
        """エントリの基本情報のみを取得する（高速）

        指定されたキーに対応するエントリの基本情報のみを取得します。
        完全なエントリ情報よりも少ないデータで高速に処理するために使用します。

        Args:
            key: 取得するエントリのキー

        Returns:
            EntryModel: 基本情報のみを含むエントリモデル、存在しない場合はNone
        """
        logger.debug(
            f"EntryRetrieverComponent.get_entry_basic_info: キー={key}の基本情報を取得"
        )

        # 基本情報キャッシュからエントリを取得
        if self.cache_manager.exists_entry(key):
            basic_info = self.cache_manager.get_entry(key)
            logger.debug(
                f"EntryRetrieverComponent.get_entry_basic_info: キャッシュヒット key={key}"
            )
            return basic_info

        # データベースからエントリの基本情報を取得
        basic_info_dict = self.db_accessor.get_entry_basic_info(key)
        if basic_info_dict:
            # EntryModelオブジェクトに変換
            basic_info = EntryModel.from_dict(basic_info_dict)
            # キャッシュに追加
            self.cache_manager.add_basic_info_to_cache(key, basic_info)
            return basic_info

        logger.debug(
            f"EntryRetrieverComponent.get_entry_basic_info: 基本情報が見つかりません key={key}"
        )
        return None

    def prefetch_entries(self, keys: List[str]) -> None:
        """指定されたキーのエントリをプリフェッチする

        Args:
            keys: プリフェッチするエントリのキーのリスト
        """
        if not keys:
            return

        # キャッシュにないキーを特定
        missing_keys = [key for key in keys if not self.cache_manager.exists_entry(key)]
        if not missing_keys:
            return

        # 一括取得
        entries = self.db_accessor.get_entries_by_keys(missing_keys)

        # キャッシュに保存
        for key, entry in entries.items():
            entry_model = EntryModel.from_dict(entry)
            self.cache_manager.add_entry_to_cache(key, entry_model)

    def get_entry_at(self, position: int) -> Optional[EntryModel]:
        """位置（インデックス）からエントリを取得する

        Args:
            position: エントリの位置（インデックス）

        Returns:
            Optional[EntryModel]: 指定された位置のエントリ。見つからない場合はNone
        """
        logger.debug(
            f"EntryRetrieverComponent.get_entry_at: 位置={position}のエントリを取得"
        )

        # 位置をキーに変換（文字列として）
        key = str(position)
        return self.get_entry_by_key(key)

    def get_all_entries(self) -> List[EntryModel]:
        """すべてのエントリを取得する

        キャッシュは使用せず、常に最新のデータを返します。

        Returns:
            List[EntryModel]: すべてのエントリのリスト
        """
        # データベースからすべてのエントリを取得
        entries_dict = self.db_accessor.get_filtered_entries(
            filter_text="すべて",
            filter_keyword=None,
            match_mode="部分一致",
            case_sensitive=False,
            filter_status=None,
            filter_obsolete=True,
            search_text=None,
        )

        # 既にEntryModelのリストが返されるので変換は不要
        return entries_dict

    def count_entries(self) -> int:
        """全エントリ数を取得する

        Returns:
            int: エントリの総数
        """
        return self.db_accessor.count_entries() if self.db_accessor else 0

    def get_unique_msgid_count(self) -> int:
        """ユニークなmsgid（原文）の数を取得する

        重複を除いた翻訳対象の原文の数を返します。

        Returns:
            int: ユニークなmsgidの数
        """
        return self.db_accessor.get_unique_msgid_count() if self.db_accessor else 0
