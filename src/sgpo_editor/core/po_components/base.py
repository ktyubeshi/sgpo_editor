"""POファイル基本コンポーネント

このモジュールは、POファイルを読み込み、メタデータを管理する基本的な機能を提供します。
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Union

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.po_factory import get_po_factory, POLibraryType
from sgpo_editor.core.po_interface import POEntry
from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.types import EntryDict, MetadataDict

logger = logging.getLogger(__name__)


class POFileBaseComponent:
    """POファイルの基本機能を提供するコンポーネント

    このクラスは、POファイルの読み込みとメタデータ管理の責務を持ちます。
    """

    def __init__(
        self,
        library_type: POLibraryType = POLibraryType.SGPO,
        db_accessor: Optional[DatabaseAccessor] = None,
        cache_manager: Optional[EntryCacheManager] = None,
    ):
        """初期化

        Args:
            library_type: 使用するPOライブラリの種類
            db_accessor: データベースアクセサのインスタンス（省略時は内部で生成）
            cache_manager: キャッシュマネージャのインスタンス（省略時は内部で生成）
        """
        # データベースとキャッシュ管理の初期化
        self.db = InMemoryEntryStore()
        self.db_accessor = db_accessor or DatabaseAccessor(self.db)
        self.cache_manager = cache_manager or EntryCacheManager()

        # POファイル関連の状態
        self.path = None
        self.modified = False
        self.metadata: MetadataDict = {}  # POファイルのメタデータを保存するための変数
        self.library_type = library_type

        # ファイル読み込み完了フラグ
        self._is_loaded = False

        logger.debug("POFileBaseComponent: 初期化完了")

    async def load(self, path: Union[str, Path]) -> None:
        """POファイルを非同期で読み込む

        このメソッドは、POファイルを非同期で読み込み、データベースに格納します。
        ファイル読み込みやデータベース操作などのCPU負荷の高い処理をasyncio.to_threadを
        使用して別スレッドで実行し、UIの応答性を向上させています。

        Args:
            path: 読み込むPOファイルのパス
        """
        # 作業中のデータを保存するための変数
        pofile = None
        entries_to_add = []
        start_time = time.time()
        
        try:
            logger.debug(f"POファイル読み込み開始: {path}")

            # キャッシュをクリア
            self.cache_manager.clear_all_cache()

            path = Path(path)
            self.path = path

            # POファイルファクトリを取得
            factory = get_po_factory(self.library_type)

            # POファイルを読み込む（CPU負荷の高い処理を非同期実行）
            try:
                logger.debug(f"POファイル読み込み処理開始: {path}")
                pofile = await asyncio.to_thread(factory.load_file, path)
                logger.debug(f"POファイル読み込み処理完了: {path}")
            except Exception as e:
                logger.error(f"POファイル読み込み処理失敗: {e}")
                raise RuntimeError(f"POファイルの読み込みに失敗しました: {e}") from e

            # メタデータを保存
            if pofile is not None:
                self.metadata = dict(pofile.metadata)
            else:
                logger.error("POファイルがNoneです。これは想定外のエラーです。")
                raise RuntimeError("POファイルの読み込みに失敗しました: ファイルがNoneです")

            # データベースをクリア
            try:
                logger.debug("データベースクリア開始")
                self.db_accessor.clear_database()
                logger.debug("データベースクリア完了")
            except Exception as e:
                logger.error(f"データベースクリア失敗: {e}")
                raise RuntimeError(f"データベースのクリアに失敗しました: {e}") from e

            # すべてのエントリをデータベースに追加するための準備
            try:
                logger.debug("エントリ変換処理開始")
                entries_to_add = []
                for i, entry in enumerate(pofile):
                    entry_dict = self._convert_entry_to_dict(entry, i)
                    entries_to_add.append(entry_dict)
                logger.debug(f"エントリ変換処理完了: {len(entries_to_add)}件のエントリを変換")
            except Exception as e:
                logger.error(f"エントリ変換処理失敗: {e}")
                raise RuntimeError(f"POエントリの変換に失敗しました: {e}") from e

            # エントリをデータベースに追加（CPU負荷の高い処理を非同期実行）
            try:
                logger.debug(f"データベース一括追加処理開始: {len(entries_to_add)}件")
                if entries_to_add:
                    await asyncio.to_thread(self.db_accessor.add_entries_bulk, entries_to_add)
                logger.debug("データベース一括追加処理完了")
            except Exception as e:
                logger.error(f"データベース一括追加処理失敗: {e}")
                raise RuntimeError(f"データベースへのエントリ追加に失敗しました: {e}") from e

            # 基本情報をキャッシュにロード（CPU負荷の高い処理を非同期実行）
            try:
                logger.debug("基本情報キャッシュロード処理開始")
                await asyncio.to_thread(self._load_all_basic_info)
                logger.debug("基本情報キャッシュロード処理完了")
            except Exception as e:
                logger.error(f"基本情報キャッシュロード処理失敗: {e}")
                logger.debug("基本情報キャッシュロードに失敗しましたが、処理を継続します")
                # キャッシュの失敗はクリティカルではないので、例外を再スローせず続行

            # 読み込み完了フラグを設定
            self._is_loaded = True
            self.modified = False

            # 読み込み時間を計測
            elapsed_time = time.time() - start_time
            logger.debug(f"POファイル読み込み完了: {path} ({elapsed_time:.2f}秒)")

        except Exception as e:
            # エラー時の状態復元とリソース解放
            elapsed_time = time.time() - start_time
            logger.error(f"POファイル読み込み失敗: {path} ({elapsed_time:.2f}秒)")
            logger.exception(e)
            
            # 一貫性を保つため、読み込み途中のデータをクリア
            self._is_loaded = False
            self.modified = False
            self.metadata = {}
            
            # メモリ解放
            entries_to_add.clear()
            pofile = None
            
            # データベースとキャッシュのリセットを試みる
            try:
                self.db_accessor.clear_database()
            except Exception as clear_error:
                logger.error(f"エラー回復時のデータベースクリアに失敗: {clear_error}")
            
            try:
                self.cache_manager.clear_all_cache()
            except Exception as cache_error:
                logger.error(f"エラー回復時のキャッシュクリアに失敗: {cache_error}")
            
            # 元の例外を再スロー
            raise

    def _load_all_basic_info(self) -> None:
        """すべてのエントリの基本情報を一括ロード

        データベースからすべてのエントリの基本情報を取得し、基本情報キャッシュに格納します。
        これにより、詳細情報が必要ない場合の高速なアクセスが可能になります。
        """
        # データベースからすべてのエントリの基本情報を取得
        entries = self.db_accessor.get_all_entries_basic_info()

        # 基本情報をキャッシュに格納
        for key, entry_dict in entries.items():
            # 辞書からEntryModelオブジェクトを作成
            entry_model = EntryModel.from_dict(entry_dict)
            self.cache_manager.set_entry(key, entry_model)

    def _convert_entry_to_dict(self, entry: POEntry, position: int) -> EntryDict:
        """POエントリをディクショナリに変換する

        Args:
            entry: POエントリオブジェクト
            position: エントリの位置（インデックス）

        Returns:
            EntryDict: 変換されたディクショナリ
        """
        # キーは位置（文字列型）
        key = str(position)

        # エントリの属性をディクショナリに変換
        entry_dict: EntryDict = {
            "key": key,
            "position": position,
            "msgid": entry.msgid,
            "msgstr": entry.msgstr,
            "msgctxt": entry.msgctxt if hasattr(entry, "msgctxt") else None,
            "flags": list(entry.flags) if hasattr(entry, "flags") else [],
            "obsolete": entry.obsolete if hasattr(entry, "obsolete") else False,
            "msgid_plural": entry.msgid_plural if hasattr(entry, "msgid_plural") else None,
            "msgstr_plural": dict(entry.msgstr_plural) if hasattr(entry, "msgstr_plural") else {},
            "previous_msgid": entry.previous_msgid if hasattr(entry, "previous_msgid") else None,
            "previous_msgid_plural": entry.previous_msgid_plural
            if hasattr(entry, "previous_msgid_plural")
            else None,
            "previous_msgctxt": entry.previous_msgctxt
            if hasattr(entry, "previous_msgctxt")
            else None,
            "linenum": entry.linenum if hasattr(entry, "linenum") else None,
            "comment": entry.comment if hasattr(entry, "comment") else None,
            "tcomment": entry.tcomment if hasattr(entry, "tcomment") else None,
            "occurrences": list(entry.occurrences) if hasattr(entry, "occurrences") else [],
        }

        return entry_dict

    def enable_cache(self, enabled: bool = True) -> None:
        """キャッシュ機能の有効/無効を設定する

        Args:
            enabled: キャッシュを有効にするかどうか
        """
        if self.cache_manager:
            self.cache_manager.enable_cache(enabled)
            if not enabled:
                # キャッシュを無効化する場合はキャッシュをクリア
                self.cache_manager.clear_all_cache()

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

    def get_filename(self) -> str:
        """POファイルの名前を取得する

        Returns:
            str: ファイル名（読み込まれていない場合は空文字列）
        """
        if not self.path:
            return ""
        return self.path.name 