"""POファイルビューアの基本クラス

このモジュールは、POファイルを読み込むための基本機能を提供します。
ViewerPOFileクラスをリファクタリングし、キャッシュ管理とデータベースアクセスの責務を分離しています。
"""

import logging
import time
import asyncio
from pathlib import Path
from typing import Optional, Union

from sgpo_editor.types import EntryDict, FlagConditions, MetadataDict

from sgpo_editor.core.cache_manager import EntryCacheManager
from sgpo_editor.core.constants import TranslationStatus
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.core.po_factory import get_po_factory, POLibraryType
from sgpo_editor.core.po_interface import POEntry
from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class ViewerPOFileBase:
    """POファイルを読み込み、表示するための基本クラス

    このクラスは、キャッシュ管理とデータベースアクセスの責務を分離し、
    EntryCacheManagerとDatabaseAccessorを利用して実装されています。

    主な機能:
    1. POファイルの非同期読み込み: asyncioを使用してUIの応答性を向上
    2. エントリの取得と管理: キャッシュとデータベースを連携してエントリを効率的に管理
    3. フィルタリングとソート: 検索条件や翻訳ステータスに基づくエントリの絞り込み

    キャッシュとデータベースの連携方法:
    - ファイル読み込み時: キャッシュをクリアし、データベースに新しいエントリを格納
    - エントリ取得時: まずキャッシュを確認し、キャッシュミス時にデータベースから取得
    - エントリ更新時: データベースとキャッシュの両方を更新し、フィルタキャッシュを無効化
    - フィルタリング時: キャッシュを確認し、キャッシュミスまたは強制更新時に再計算
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
        # データベースとキャッシュ管理の初期化
        self.db = InMemoryEntryStore()
        self.db_accessor = db_accessor or DatabaseAccessor(self.db)
        self.cache_manager = cache_manager or EntryCacheManager()

        # POファイル関連の状態
        self.path = None
        self.modified = False
        self.metadata: MetadataDict = {}  # POファイルのメタデータを保存するための変数
        self.library_type = library_type

        # フィルタリング関連の状態
        self.filtered_entries = []
        self.filter_text = TranslationStatus.ALL
        self.search_text = ""
        self.sort_column = None
        self.sort_order = None
        self.flag_conditions: FlagConditions = {}
        self.translation_status = None

        # ファイル読み込み完了フラグ
        self._is_loaded = False

        # フィルタ更新フラグ（Trueの場合はフィルタ結果を強制的に再計算）
        self._force_filter_update = False

        logger.debug("ViewerPOFileBase: 初期化完了")

    async def load(self, path: Union[str, Path]) -> None:
        """POファイルを非同期で読み込む

        このメソッドは、POファイルを非同期で読み込み、データベースに格納します。
        ファイル読み込みやデータベース操作などのCPU負荷の高い処理をasyncio.to_threadを
        使用して別スレッドで実行し、UIの応答性を向上させています。

        キャッシュとの連携:
        - 読み込み開始時に、EntryCacheManagerのclear_all_cacheメソッドですべてのキャッシュをクリア
        - 読み込み完了後、_load_all_basic_infoメソッドで基本情報キャッシュを初期化

        Args:
            path: 読み込むPOファイルのパス
        """
        try:
            start_time = time.time()
            logger.debug(f"POファイル読み込み開始: {path}")

            # キャッシュをクリア
            self.cache_manager.clear_all_cache()

            path = Path(path)
            self.path = path

            # POファイルファクトリを取得
            factory = get_po_factory(self.library_type)

            # POファイルを読み込む（CPU負荷の高い処理を非同期実行）
            pofile = await asyncio.to_thread(factory.load_file, path)

            # メタデータを保存
            self.metadata = dict(pofile.metadata)

            # データベースをクリア
            self.db_accessor.clear_database()

            # すべてのエントリをデータベースに追加（CPU負荷の高い処理を非同期実行）
            entries_to_add = []
            for i, entry in enumerate(pofile):
                entry_dict = self._convert_entry_to_dict(entry, i)
                entries_to_add.append(entry_dict)

            await asyncio.to_thread(self.db_accessor.add_entries_bulk, entries_to_add)

            # 基本情報をキャッシュにロード（CPU負荷の高い処理を非同期実行）
            await asyncio.to_thread(self._load_all_basic_info)

            # 読み込み完了フラグを設定
            self._is_loaded = True
            self.modified = False

            # 読み込み時間を計測
            elapsed_time = time.time() - start_time
            logger.debug(f"POファイル読み込み完了: {path} ({elapsed_time:.2f}秒)")

        except Exception as e:
            logger.error(f"POファイル読み込みエラー: {e}")
            logger.exception(e)
            raise

    def _load_all_basic_info(self) -> None:
        """すべてのエントリの基本情報を一括ロード

        データベースからすべてのエントリの基本情報を取得し、基本情報キャッシュに格納します。
        これにより、詳細情報が必要ない場合の高速なアクセスが可能になります。

        キャッシュとの連携:
        - DatabaseAccessorのget_all_entries_basic_infoメソッドで基本情報を取得
        - 取得した基本情報をEntryModelオブジェクトに変換
        - EntryCacheManagerのcache_basic_info_entryメソッドでキャッシュに格納

        このメソッドはファイル読み込み時に呼び出され、リスト表示などの高速化に対応します。
        """
        # データベースからすべてのエントリの基本情報を取得
        entries = self.db_accessor.get_all_entries_basic_info()

        # 基本情報をキャッシュに格納
        for key, entry_dict in entries.items():
            # 辞書からEntryModelオブジェクトを作成
            entry_model = EntryModel.from_dict(entry_dict)
            self.cache_manager.cache_basic_info_entry(key, entry_model)

    def _convert_entry_to_dict(self, entry: POEntry, position: int) -> EntryDict:
        """POエントリをディクショナリに変換する

        Args:
            entry: POエントリオブジェクト
            position: エントリの位置（インデックス）

        Returns:
            Dict[str, Any]: 変換されたディクショナリ
        """
        # キーは位置（文字列型）
        key = str(position)

        # 基本情報
        entry_dict = {
            "key": key,
            "position": position,
            "msgid": entry.msgid,
            "msgstr": entry.msgstr,
            "fuzzy": "fuzzy" in entry.flags,
            "obsolete": entry.obsolete,
        }

        # 複数形
        if hasattr(entry, "msgid_plural") and entry.msgid_plural:
            entry_dict["msgid_plural"] = entry.msgid_plural
        if hasattr(entry, "msgstr_plural") and entry.msgstr_plural:
            entry_dict["msgstr_plural"] = entry.msgstr_plural

        # コンテキスト
        if hasattr(entry, "msgctxt") and entry.msgctxt:
            entry_dict["msgctxt"] = entry.msgctxt

        # 参照情報
        if hasattr(entry, "occurrences") and entry.occurrences:
            entry_dict["references"] = entry.occurrences

        # フラグ
        if hasattr(entry, "flags") and entry.flags:
            entry_dict["flags"] = entry.flags

        # コメント
        if hasattr(entry, "comment") and entry.comment:
            entry_dict["comment"] = entry.comment
        if hasattr(entry, "tcomment") and entry.tcomment:
            entry_dict["tcomment"] = entry.tcomment

        return entry_dict

    def enable_cache(self, enabled: bool = True) -> None:
        """キャッシュを有効/無効にする

        キャッシュの有効/無効を切り替えます。無効にすると、すべてのキャッシュがクリアされ、
        以降の操作はすべてデータベースから直接取得されます。これはデバッグ時や
        メモリ使用量を抑えたい場合に便利です。

        Args:
            enabled: キャッシュを有効にする場合はTrue、無効にする場合はFalse
        """
        self.cache_manager.enable_cache(enabled)
        if not enabled:
            self.cache_manager.clear_all_cache()
