"""POファイルエントリ更新コンポーネント

このモジュールは、POファイルのエントリを更新するための機能を提供します。
"""

import logging
from typing import Dict, List, Optional, Set, Any, Union

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class UpdaterComponent:
    """POファイルのエントリ更新機能を提供するコンポーネント

    このクラスは、エントリの更新と保存を担当します。
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
        self.modified = False
        logger.debug("UpdaterComponent: 初期化完了")

    def update_entry(self, key: str, field: str, value: Any) -> bool:
        """エントリの特定のフィールドを更新する

        Args:
            key: 更新するエントリのキー
            field: 更新するフィールド名
            value: 設定する値

        Returns:
            bool: 更新が成功した場合はTrue、失敗した場合はFalse
        """
        logger.debug(f"UpdaterComponent.update_entry: key={key}, field={field}")

        if not self.db_accessor:
            logger.error("データベースアクセサが設定されていません")
            return False

        # フィールド名がEntryModelの有効なフィールドか確認
        valid_fields = [
            "msgid", "msgstr", "msgctxt", "flags", "obsolete",
            "msgid_plural", "msgstr_plural", "previous_msgid",
            "previous_msgid_plural", "previous_msgctxt", "comment",
            "tcomment", "occurrences"
        ]
        if field not in valid_fields:
            logger.error(f"無効なフィールド名: {field}")
            return False

        # データベースからエントリを取得
        entry_dict = self.db_accessor.get_entry_by_key(key)
        if not entry_dict:
            logger.error(f"キー {key} のエントリが見つかりません")
            return False

        # エントリを更新
        entry_dict[field] = value
        self.db_accessor.update_entry(entry_dict)

        # キャッシュから削除して次回アクセス時に再取得
        self.cache_manager.invalidate_entry(key)
        self.cache_manager.invalidate_filter_cache()
        
        # 変更フラグを設定
        self.modified = True

        return True

    def update_entry_field(self, entry: EntryModel, field: str, value: Any) -> bool:
        """エントリモデルの特定のフィールドを更新する

        Args:
            entry: 更新するエントリモデル
            field: 更新するフィールド名
            value: 設定する値

        Returns:
            bool: 更新が成功した場合はTrue、失敗した場合はFalse
        """
        return self.update_entry(entry.key, field, value)

    def update_entry_model(self, entry: EntryModel) -> bool:
        """エントリモデル全体を更新する

        Args:
            entry: 更新するエントリモデル

        Returns:
            bool: 更新が成功した場合はTrue、失敗した場合はFalse
        """
        logger.debug(f"UpdaterComponent.update_entry_model: key={entry.key}")

        # エントリをディクショナリに変換
        entry_dict = entry.model_dump()

        # データベースを更新
        success = self.db_accessor.update_entry(entry_dict)
        if not success:
            logger.error(f"キー {entry.key} のエントリの更新に失敗しました")
            return False

        # キャッシュから削除して次回アクセス時に再取得
        self.cache_manager.invalidate_entry(entry.key)
        self.cache_manager.invalidate_filter_cache()

        # 変更フラグを設定
        self.modified = True

        return True

    def set_flag(self, key: str, flag: str, value: bool = True) -> bool:
        """エントリのフラグを設定または解除する

        Args:
            key: 対象エントリのキー
            flag: 設定するフラグ名
            value: フラグ値（Trueで設定、Falseで解除）

        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        logger.debug(f"UpdaterComponent.set_flag: key={key}, flag={flag}, value={value}")

        # データベースからエントリを取得
        entry_dict = self.db_accessor.get_entry_by_key(key)
        if not entry_dict:
            logger.error(f"キー {key} のエントリが見つかりません")
            return False

        # 現在のフラグリストを取得
        flags = set(entry_dict.get("flags", []))

        # フラグを設定または解除
        if value:
            flags.add(flag)
        elif flag in flags:
            flags.remove(flag)

        # エントリを更新
        entry_dict["flags"] = list(flags)
        self.db_accessor.update_entry(entry_dict)

        # キャッシュから削除して次回アクセス時に再取得
        self.cache_manager.invalidate_entry(key)
        self.cache_manager.invalidate_filter_cache()

        # 変更フラグを設定
        self.modified = True

        return True

    def toggle_flag(self, key: str, flag: str) -> bool:
        """エントリのフラグを切り替える

        Args:
            key: 対象エントリのキー
            flag: 切り替えるフラグ名

        Returns:
            bool: 操作が成功した場合はTrue、失敗した場合はFalse
        """
        logger.debug(f"UpdaterComponent.toggle_flag: key={key}, flag={flag}")

        # データベースからエントリを取得
        entry_dict = self.db_accessor.get_entry_by_key(key)
        if not entry_dict:
            logger.error(f"キー {key} のエントリが見つかりません")
            return False

        # 現在のフラグリストを取得
        flags = set(entry_dict.get("flags", []))

        # フラグを切り替え
        if flag in flags:
            flags.remove(flag)
        else:
            flags.add(flag)

        # エントリを更新
        entry_dict["flags"] = list(flags)
        self.db_accessor.update_entry(entry_dict)

        # キャッシュから削除して次回アクセス時に再取得
        self.cache_manager.invalidate_entry(key)
        self.cache_manager.invalidate_filter_cache()

        # 変更フラグを設定
        self.modified = True

        return True

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

    def invalidate_cache(self) -> None:
        """キャッシュを無効化する

        キャッシュマネージャのキャッシュを無効化します。
        """
        if self.cache_manager:
            self.cache_manager.set_force_filter_update(True)
            self.cache_manager.clear_cache() 