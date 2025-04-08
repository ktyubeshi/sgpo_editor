"""POファイルビューア

このモジュールは、POファイルを読み込み、表示、編集するための機能を提供します。
"""

import logging
import time
import asyncio
from collections import namedtuple
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sgpo_editor.core.po_factory import get_po_factory, POLibraryType
from sgpo_editor.core.po_interface import POEntry
from sgpo_editor.models.database import InMemoryEntryStore
from sgpo_editor.models.entry import EntryModel
from sgpo_editor.core.constants import TranslationStatus

logger = logging.getLogger(__name__)

# 統計情報用のnamedtuple定義
Stats = namedtuple(
    "Stats", ["total", "translated", "fuzzy", "untranslated", "progress"]
)


class ViewerPOFile:
    """POファイルを読み込み、表示するためのクラス"""

    def __init__(self, library_type: Optional[POLibraryType] = POLibraryType.SGPO):
        """初期化

        Args:
            library_type: 使用するPOライブラリの種類
        """
        self.db = InMemoryEntryStore()
        self.path = None
        self.filtered_entries = []
        self.search_text = ""
        self.sort_column = None
        self.sort_order = None
        self.flag_conditions = {}
        self.translation_status = TranslationStatus.ALL
        self.modified = False
        self.metadata = {}  # POファイルのメタデータを保存するための変数を追加
        self.library_type = library_type

        # キャッシュ関連の変数を初期化
        # 完全なEntryModelオブジェクトのキャッシュ（key→EntryModelのマップ）
        self._complete_entry_cache = {}
        # 基本情報のみのキャッシュ（key→基本情報dictのマップ）
        self._entry_basic_info_cache = {}
        # フィルタ結果のキャッシュ（フィルタ条件に合致するエントリのリスト）
        self._filtered_entries_cache = []
        # フィルタキャッシュのキー（フィルタ条件を表す文字列）
        self._filtered_entries_cache_key = ""
        # キャッシュ有効フラグ（Falseの場合は常にデータベースから取得）
        self._cache_enabled = True
        # ファイル読み込み完了フラグ
        self._is_loaded = False

        # フィルタ更新フラグ（Trueの場合はフィルタ結果を強制的に再計算）
        self._force_filter_update = False

    async def load(self, path: Union[str, Path]) -> None:
        """POファイルを非同期で読み込む"""
        try:
            start_time = time.time()
            logger.debug(f"POファイル読み込み開始: {path}")

            # キャッシュをクリア
            self._clear_cache()

            path = Path(path)
            self.path = path

            # POファイルファクトリを取得
            factory = get_po_factory(self.library_type)

            # POファイルを読み込む（CPU負荷の高い処理を非同期実行）
            pofile = await asyncio.to_thread(factory.load_file, path)

            # メタデータを保存
            self.metadata = dict(pofile.metadata)

            # データベースをクリア
            self.db.clear()

            # すべてのエントリをデータベースに追加
            entries = []
            for i, entry in enumerate(pofile):
                entry_data = self._convert_entry_to_dict(entry, i)
                entries.append(entry_data)

            # バルクインサートを使用（最適化）（CPU負荷の高い処理を非同期実行）
            await asyncio.to_thread(self.db.add_entries_bulk, entries)

            # 基本情報のキャッシュを一括ロード（CPU負荷の高い処理を非同期実行）
            await asyncio.to_thread(self._load_all_basic_info)

            # 完全ロード終了フラグを設定
            self._is_loaded = True

            # 処理時間をログに出力
            elapsed = time.time() - start_time
            logger.debug(f"POファイル読み込み完了: {elapsed:.2f}秒")

        except Exception as e:
            logger.error(f"POファイル読み込みエラー: {e}")
            raise

    def _load_all_basic_info(self) -> None:
        """すべてのエントリの基本情報を一括ロード

        データベースからすべてのエントリの基本情報を取得し、基本情報キャッシュに格納します。
        これにより、詳細情報が必要ない場合の高速なアクセスが可能になります。
        """
        try:
            # get_all_entries_basic_infoが存在しないため、get_entriesを使用
            entries_basic_info = self.db.get_entries()
            for entry in entries_basic_info:
                if "key" in entry:
                    # 基本情報としてマーク
                    entry["is_basic_info"] = True
                    self._entry_basic_info_cache[entry["key"]] = entry
        except Exception as e:
            logger.error(f"基本情報キャッシュロードエラー: {e}")

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
        # キャッシュが無効化されている場合は直接DBから取得
        if not self._cache_enabled:
            entry_dict = self.db.get_entry_by_key(key)
            return EntryModel.from_dict(entry_dict) if entry_dict else None

        # 完全なエントリがすでにキャッシュにある場合
        if key in self._complete_entry_cache:
            # キャッシュがEntryModelオブジェクトかどうか確認
            cached_entry = self._complete_entry_cache[key]
            if isinstance(cached_entry, EntryModel):
                return cached_entry
            else:
                # 辞書の場合はEntryModelオブジェクトに変換してキャッシュを更新
                entry_obj = EntryModel.from_dict(cached_entry)
                self._complete_entry_cache[key] = entry_obj
                return entry_obj

        # 基本情報のみがキャッシュにある場合
        if key in self._entry_basic_info_cache:
            basic_info = self._entry_basic_info_cache[key]
            # 基本情報がEntryModelオブジェクトかどうか確認
            if isinstance(basic_info, EntryModel):
                # is_basic_infoフラグがある場合は詳細情報を取得
                if getattr(basic_info, "is_basic_info", False):
                    # DBから完全なエントリ情報を取得
                    full_entry_dict = self.db.get_entry_by_key(key)
                    if full_entry_dict:
                        # 完全なエントリをEntryModelオブジェクトに変換してキャッシュに保存
                        full_entry = EntryModel.from_dict(full_entry_dict)
                        self._complete_entry_cache[key] = full_entry
                        return full_entry
                    return basic_info  # 完全な情報がない場合は基本情報を返す
                return basic_info
            else:
                # 辞書の場合はEntryModelオブジェクトに変換
                is_basic_info = basic_info.get("is_basic_info", False)
                entry_obj = EntryModel.from_dict(basic_info)

                if is_basic_info:
                    # DBから完全なエントリ情報を取得
                    full_entry_dict = self.db.get_entry_by_key(key)
                    if full_entry_dict:
                        # 完全なエントリをEntryModelオブジェクトに変換してキャッシュに保存
                        full_entry = EntryModel.from_dict(full_entry_dict)
                        self._complete_entry_cache[key] = full_entry
                        return full_entry

                    # 基本情報をキャッシュに保存
                    self._entry_basic_info_cache[key] = entry_obj
                    return entry_obj

                # 基本情報をキャッシュに保存
                self._entry_basic_info_cache[key] = entry_obj
                return entry_obj

        # キャッシュにない場合はDBから取得
        entry_dict = self.db.get_entry_by_key(key)
        if entry_dict:
            # 辞書をEntryModelオブジェクトに変換
            entry_obj = EntryModel.from_dict(entry_dict)
            # 完全なエントリをキャッシュに保存
            self._complete_entry_cache[key] = entry_obj
            return entry_obj
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
        if not keys:
            return {}

        # キャッシュから取得できるエントリを確認
        result = {}
        missing_keys = []

        for key in keys:
            if key in self._complete_entry_cache:
                # 完全なエントリがキャッシュにある場合
                result[key] = self._complete_entry_cache[key]
            elif (
                key in self._entry_basic_info_cache
                and not self._entry_basic_info_cache[key].get("is_basic_info", False)
            ):
                # 基本情報のみがキャッシュにある場合
                result[key] = self._entry_basic_info_cache[key]
            else:
                # キャッシュにない場合は後でDBから取得するためリストに追加
                missing_keys.append(key)

        # キャッシュにないエントリをDBから一括取得
        if missing_keys:
            missing_entries = self.db.get_entries_by_keys(missing_keys)
            for key, entry in missing_entries.items():
                result[key] = EntryModel.from_dict(entry)
                # 完全な情報をキャッシュに保存
                self._complete_entry_cache[key] = result[key]

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
        # 基本情報がキャッシュにある場合
        if key in self._entry_basic_info_cache:
            return self._entry_basic_info_cache[key]

        # 完全なエントリがキャッシュにある場合
        if key in self._complete_entry_cache:
            entry = self._complete_entry_cache[key]
            # 基本情報のみを返す
            basic_info = EntryModel(
                key=entry.key,
                msgid=entry.msgid,
                msgstr=entry.msgstr,
                fuzzy="fuzzy" in entry.flags,
                obsolete=entry.obsolete,
                position=entry.position,
                flags=entry.flags,
            )
            self._entry_basic_info_cache[key] = basic_info
            return basic_info

        # キャッシュにない場合はDBから取得
        basic_info_dict = self.db.get_entry_basic_info(key)
        if basic_info_dict:
            self._entry_basic_info_cache[key] = EntryModel(**basic_info_dict)
        return self._entry_basic_info_cache.get(key)

    def _convert_entry_to_dict(self, entry: POEntry, position: int) -> Dict[str, Any]:
        """POエントリをディクショナリに変換する"""
        key = f"{position}"
        entry_dict = {
            "key": key,
            "msgid": entry.msgid,
            "msgstr": entry.msgstr,
            "flags": entry.flags,
            "obsolete": entry.obsolete,
            "position": position,
            "occurrences": entry.occurrences,
        }

        # 複数形
        if hasattr(entry, "msgid_plural") and entry.msgid_plural:
            entry_dict["msgid_plural"] = entry.msgid_plural
            entry_dict["msgstr_plural"] = entry.msgstr_plural

        # コンテキスト
        if entry.msgctxt:
            entry_dict["msgctxt"] = entry.msgctxt

        # 前バージョン
        if hasattr(entry, "previous_msgid") and entry.previous_msgid:
            entry_dict["previous_msgid"] = entry.previous_msgid
        if hasattr(entry, "previous_msgid_plural") and entry.previous_msgid_plural:
            entry_dict["previous_msgid_plural"] = entry.previous_msgid_plural
        if hasattr(entry, "previous_msgctxt") and entry.previous_msgctxt:
            entry_dict["previous_msgctxt"] = entry.previous_msgctxt

        # コメント
        if entry.comment:
            entry_dict["comment"] = entry.comment
        if entry.tcomment:
            entry_dict["tcomment"] = entry.tcomment

        return entry_dict

    def get_filtered_entries(
        self,
        update_filter: bool = False,
        filter_keyword: Optional[str] = None,
    ) -> List[EntryModel]:
        """フィルタ条件に合ったエントリーを取得する

        Args:
            update_filter: フィルター条件を強制的に更新するフラグ
            filter_keyword: 検索キーワード

        Returns:
            フィルター条件に一致するEntryModelのリスト
        """
        logger.debug(
            f"ViewerPOFile.get_filtered_entries: 開始 update_filter={update_filter}, filter_keyword={filter_keyword}, _force_filter_update={self._force_filter_update}"
        )
        # フィルタ条件の更新
        if update_filter or filter_keyword is not None:
            # filter_keywordが指定された場合はそれを使用、そうでない場合は現在のsearch_textを維持
            if filter_keyword is not None:
                self.search_text = filter_keyword
            # 強制更新フラグを設定
            self._force_filter_update = True
            logger.debug(f"ViewerPOFile.get_filtered_entries: フィルタ条件を更新: search_text={self.search_text}")

        # フィルタ条件をログ出力
        logger.debug(
            f"ViewerPOFile.get_filtered_entries: フィルタ条件: search_text={self.search_text}, translation_status={self.translation_status}"
        )

        # キャッシュキーの生成
        cache_key = self._generate_filter_cache_key()

        # 強制更新フラグがある場合またはキャッシュが無効な場合はキャッシュをクリア
        if self._force_filter_update:
            logger.debug(
                "ViewerPOFile.get_filtered_entries: 強制更新フラグがあるためキャッシュをクリア"
            )
            self._force_filter_update = False
            update_filter = True

            # フィルタキャッシュをリセット
            self._filtered_entries_cache = []
            self._filtered_entries_cache_key = ""

        # キャッシュチェック - 強制更新でなければキャッシュから返す
        if (
            not update_filter
            and self._filtered_entries_cache
            and self._filtered_entries_cache_key == cache_key
        ):
            logger.debug(
                "ViewerPOFile.get_filtered_entries: キャッシュからフィルタリング済みエントリを返します"
            )
            return self._filtered_entries_cache

        try:
            # 翻訳ステータスに基づいてフラグ条件を設定
            logger.debug("ViewerPOFile.get_filtered_entries: フラグ条件を設定")
            self._set_flag_conditions_from_status(self.translation_status)

            # データベースからエントリを取得
            logger.debug(
                "ViewerPOFile.get_filtered_entries: データベースからエントリを取得"
            )
            entries_dict = self.db.get_entries(
                search_text=self.search_text,
                flag_conditions=self.flag_conditions,
                translation_status=self.translation_status,
                sort_column=self.sort_column,
                sort_order=self.sort_order,
            )
            logger.debug(
                f"ViewerPOFile.get_filtered_entries: データベースから {len(entries_dict)} 件のエントリを取得"
            )

            # エントリオブジェクトのリストを作成
            result = []

            for entry_dict in entries_dict:
                key = entry_dict.get("key", "")
                # キーが存在し、キャッシュにある場合はキャッシュから取得
                if key and key in self._complete_entry_cache:
                    # 既存のEntryModelオブジェクトを更新（必要な場合）
                    entry_obj = self._complete_entry_cache[key]
                    # 重要なフィールドが変更されている場合のみ更新
                    if (
                        entry_obj.msgid != entry_dict.get("msgid", "")
                        or entry_obj.msgstr != entry_dict.get("msgstr", "")
                        or entry_obj.fuzzy != ("fuzzy" in entry_dict.get("flags", []))
                    ):
                        # 新しいオブジェクトを作成してキャッシュを更新
                        entry_obj = EntryModel.from_dict(entry_dict)
                        self._complete_entry_cache[key] = entry_obj
                else:
                    # 新しいEntryModelオブジェクトを作成してキャッシュに追加
                    entry_obj = EntryModel.from_dict(entry_dict)
                    if key:
                        self._complete_entry_cache[key] = entry_obj

                result.append(entry_obj)

            # 結果をキャッシュに保存
            self._filtered_entries_cache = result
            self._filtered_entries_cache_key = cache_key

            self.filtered_entries = result
            logger.debug(
                f"ViewerPOFile.get_filtered_entries: フィルタ済みエントリを更新しました: {len(self.filtered_entries)}件"
            )

            return self.filtered_entries

        except Exception as e:
            logger.error(f"ViewerPOFile.get_filtered_entries: エラー発生 {e}")
            logger.error(f"エントリの取得中にエラーが発生しました: {str(e)}")
            logger.exception(e)
            return []

    def _set_flag_conditions_from_status(self, translation_status: str) -> None:
        """翻訳ステータスからフラグ条件を設定する

        指定された翻訳ステータスに基づいて、適切なフラグ条件と翻訳ステータスを設定します。
        これにより、データベースクエリで適切なフィルタリングが行われます。

        Args:
            translation_status: 翻訳ステータス（TranslationStatus定数）
        """
        # フラグ条件を初期化
        self.flag_conditions = {}
        self.translation_status = translation_status

        # ステータスによって条件を設定
        if translation_status == TranslationStatus.ALL:
            # すべてのエントリを表示する場合は条件を設定しない
            pass
        elif translation_status == TranslationStatus.TRANSLATED:
            # 翻訳済みエントリの条件：msgstrがあり、fuzzyフラグがない
            self.flag_conditions = {
                "exclude_flags": ["fuzzy"],
            }
            self.translation_status = "translated"
        elif translation_status == TranslationStatus.UNTRANSLATED:
            # 未翻訳エントリの条件：msgstrが空か、fuzzyフラグがある
            # Databaseのtranslation_status="untranslated"条件と一致させる
            self.translation_status = "untranslated"
        elif translation_status == TranslationStatus.FUZZY:
            # ファジーエントリの条件：fuzzyフラグがある
            self.flag_conditions = {
                "include_flags": ["fuzzy"],
            }
        elif translation_status == TranslationStatus.OBSOLETE:
            # 廃止済みエントリの条件：obsoleteフラグがある
            self.flag_conditions = {
                "obsolete_only": True,
            }

    def set_filter(
        self,
        search_text: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[Dict[str, Any]] = None,
        translation_status: Optional[str] = None,
    ) -> None:
        """フィルタを設定する

        Args:
            search_text: 検索キーワード
            sort_column: ソート列
            sort_order: ソート順序
            flag_conditions: フラグ条件
            translation_status: 翻訳ステータス
        """
        update_needed = False

        if search_text is not None and search_text != self.search_text:
            self.search_text = search_text
            update_needed = True

        if sort_column is not None and sort_column != self.sort_column:
            self.sort_column = sort_column
            update_needed = True

        if sort_order is not None and sort_order != self.sort_order:
            self.sort_order = sort_order
            update_needed = True

        if flag_conditions is not None and flag_conditions != self.flag_conditions:
            self.flag_conditions = flag_conditions
            update_needed = True

        if (
            translation_status is not None
            and translation_status != self.translation_status
        ):
            self.translation_status = translation_status
            # translation_statusが変更された場合は、対応するflag_conditionsを設定
            self._set_flag_conditions_from_status(translation_status)
            update_needed = True

        if update_needed:
            # フィルタリング条件が変更された場合は、強制的に更新
            self._force_filter_update = True
            self.get_filtered_entries(update_filter=True)

    def update_entry(self, entry: Union[Dict[str, Any], EntryModel]) -> bool:
        """エントリを更新する"""
        logger.debug("ViewerPOFile.update_entry: 開始")
        try:
            # EntryModelオブジェクトを辞書に変換（必要な場合）
            if isinstance(entry, EntryModel):
                logger.debug(
                    f"ViewerPOFile.update_entry: EntryModelをPOEntryに変換 key={entry.key}"
                )
                # EntryModelをPOEntryに変換し、それを辞書に変換
                po_entry = entry.to_po_entry()
                entry_dict = {
                    "key": entry.key,
                    "msgid": po_entry.msgid,
                    "msgstr": po_entry.msgstr,
                    "flags": po_entry.flags,
                    "obsolete": po_entry.obsolete,
                    "position": entry.position,
                }

                # オプションフィールドを追加
                if hasattr(po_entry, "msgctxt") and po_entry.msgctxt:
                    entry_dict["msgctxt"] = po_entry.msgctxt
                if hasattr(po_entry, "comment") and po_entry.comment:
                    entry_dict["comment"] = po_entry.comment
                if hasattr(po_entry, "tcomment") and po_entry.tcomment:
                    entry_dict["tcomment"] = po_entry.tcomment
            else:
                entry_dict = entry

            # データベースを更新
            logger.debug(
                f"ViewerPOFile.update_entry: データベース更新開始 key={entry_dict.get('key')}"
            )

            # トランザクション内で更新を実行
            key = entry_dict.get("key", "")
            result = self.db.update_entry(entry_dict)
            logger.debug(
                f"ViewerPOFile.update_entry: データベース更新結果 result={result}"
            )

            if not result:
                logger.error(
                    f"ViewerPOFile.update_entry: データベース更新失敗 key={key}"
                )
                return False

            # キャッシュを更新
            if result and self._cache_enabled and key:
                logger.debug(f"ViewerPOFile.update_entry: キャッシュ更新 key={key}")
                # EntryModelオブジェクトをキャッシュに保存
                entry_obj = (
                    entry if isinstance(entry, EntryModel) else EntryModel(**entry_dict)
                )

                # 完全なエントリキャッシュを更新
                if key in self._complete_entry_cache:
                    self._complete_entry_cache[key] = entry_obj

                # 基本情報キャッシュも更新
                if key in self._entry_basic_info_cache:
                    basic_info = EntryModel(
                        key=entry_obj.key,
                        msgid=entry_obj.msgid,
                        msgstr=entry_obj.msgstr,
                        flags=entry_obj.flags,
                        obsolete=entry_obj.obsolete,
                        position=entry_obj.position,
                    )
                    self._entry_basic_info_cache[key] = basic_info

                # フィルタされたエントリリストのキャッシュを無効化するためのフラグを設定
                # これにより次回get_filtered_entriesが呼ばれたときにキャッシュが更新される
                self._force_filter_update = True
                logger.debug(
                    "ViewerPOFile.update_entry: キャッシュ強制更新フラグを設定しました"
                )

                # フィルタキャッシュをリセット
                logger.debug(
                    "ViewerPOFile.update_entry: フィルタキャッシュをクリアします"
                )
                self._filtered_entries_cache = []
                self._filtered_entries_cache_key = ""

            # 変更フラグを設定
            self.modified = True
            logger.debug(f"ViewerPOFile.update_entry: 完了 result={result}")

            return result

        except Exception as e:
            logger.error(f"ViewerPOFile.update_entry: エラー発生 {e}")
            logger.error(f"エントリ更新エラー: {e}")
            return False

    def update_entries(
        self, entries: Dict[str, Union[Dict[str, Any], EntryModel]]
    ) -> bool:
        """複数のエントリを一括更新する"""
        try:
            # EntryModelオブジェクトを辞書に変換（必要な場合）
            entries_dict = {}
            for key, entry in entries.items():
                if isinstance(entry, EntryModel):
                    # EntryModelをPOEntryに変換し、それを辞書に変換
                    po_entry = entry.to_po_entry()
                    entry_dict = {
                        "key": entry.key,
                        "msgid": po_entry.msgid,
                        "msgstr": po_entry.msgstr,
                        "flags": po_entry.flags,
                        "obsolete": po_entry.obsolete,
                        "position": entry.position,
                    }

                    # オプションフィールドを追加
                    if hasattr(po_entry, "msgctxt") and po_entry.msgctxt:
                        entry_dict["msgctxt"] = po_entry.msgctxt
                    if hasattr(po_entry, "comment") and po_entry.comment:
                        entry_dict["comment"] = po_entry.comment
                    if hasattr(po_entry, "tcomment") and po_entry.tcomment:
                        entry_dict["tcomment"] = po_entry.tcomment

                    entries_dict[key] = entry_dict
                else:
                    entries_dict[key] = entry

            # データベースを更新
            result = self.db.update_entries(entries_dict)

            # キャッシュを更新
            if result and self._cache_enabled:
                for key, entry in entries.items():
                    entry_obj = (
                        entry
                        if isinstance(entry, EntryModel)
                        else EntryModel.from_dict(entries_dict[key])
                    )

                    # 完全なエントリキャッシュを更新
                    self._complete_entry_cache[key] = entry_obj

                    # 基本情報キャッシュも更新
                    if key in self._entry_basic_info_cache:
                        basic_info = EntryModel(
                            key=entry_obj.key,
                            msgid=entry_obj.msgid,
                            msgstr=entry_obj.msgstr,
                            flags=entry_obj.flags,
                            obsolete=entry_obj.obsolete,
                            position=entry_obj.position,
                        )
                        self._entry_basic_info_cache[key] = basic_info

                # フィルタされたエントリリストのキャッシュを無効化するためのフラグを設定
                # 複数エントリが更新された場合は、フィルタリングの結果も変わる可能性があるため
                self._force_filter_update = True

            # 変更フラグを設定
            self.modified = True

            return result
        except Exception as e:
            logger.error(f"複数エントリ更新エラー: {e}")
            return False

    def import_entries(
        self, entries: Dict[str, Union[Dict[str, Any], EntryModel]]
    ) -> bool:
        """エントリをインポートする（既存エントリの上書き）"""
        try:
            # EntryModelオブジェクトを辞書に変換（必要な場合）
            entries_dict = {}
            for key, entry in entries.items():
                entries_dict[key] = (
                    entry.to_dict() if isinstance(entry, EntryModel) else entry
                )

            # データベースにインポート
            result = self.db.import_entries(entries_dict)

            # キャッシュに保存
            if result and self._cache_enabled:
                for key, entry in entries.items():
                    entry_obj = (
                        entry
                        if isinstance(entry, EntryModel)
                        else EntryModel.from_dict(entries_dict[key])
                    )

                    # 完全なエントリキャッシュを更新
                    self._complete_entry_cache[key] = entry_obj

                    # 基本情報も更新
                    if key in self._entry_basic_info_cache:
                        basic_info_dict = {
                            "key": entry_obj.key,
                            "msgid": entry_obj.msgid,
                            "msgstr": entry_obj.msgstr,
                            "fuzzy": entry_obj.fuzzy,
                            "obsolete": entry_obj.obsolete,
                            "position": entry_obj.position,
                            "flags": entry_obj.flags,
                            "is_basic_info": True,
                        }
                        self._entry_basic_info_cache[key] = EntryModel(
                            **basic_info_dict
                        )

            # 変更フラグを設定
            self.modified = True

            return result
        except Exception as e:
            logger.error(f"エントリインポートエラー: {e}")
            return False

    def get_stats(self) -> Stats:
        """統計情報を取得する"""
        # データベースからすべてのエントリを取得
        entries = self.get_filtered_entries()

        if not entries:
            return Stats(
                total=0,
                translated=0,
                fuzzy=0,
                untranslated=0,
                progress=0.0,
            )

        total = len(entries)
        translated = 0
        fuzzy = 0
        untranslated = 0

        for entry in entries:
            # fuzzyフラグがあるかチェック
            if entry.fuzzy:
                fuzzy += 1
            # 翻訳済みかチェック
            elif entry.msgstr and entry.msgstr.strip():
                translated += 1
            else:
                untranslated += 1

        # 進捗率を計算（パーセント表示）
        progress = (translated / total * 100) if total > 0 else 0.0

        return Stats(
            total=total,
            translated=translated,
            fuzzy=fuzzy,
            untranslated=untranslated,
            progress=progress,
        )

    def save(self, path: Optional[Union[str, Path]] = None) -> bool:
        """POファイルを保存する"""
        try:
            if path is None:
                path = self.path
            else:
                path = Path(path)

            # データベースからすべてのエントリを取得
            entries = self.db.get_entries(sort_column="position", sort_order="ASC")

            # POファイルファクトリを取得
            factory = get_po_factory(self.library_type)

            # 新しいPOファイルを作成
            pofile = factory.create_file()

            # メタデータを設定
            if self.metadata:
                pofile.metadata = dict(self.metadata)

            for entry_dict in entries:
                # データベースの辞書形式のデータからPOEntryを作成
                entry_kwargs = {
                    "msgid": entry_dict.get("msgid", ""),
                    "msgstr": entry_dict.get("msgstr", ""),
                    "occurrences": entry_dict.get("references", []),
                    "flags": entry_dict.get("flags", []),
                    "obsolete": entry_dict.get("obsolete", False),
                }

                # 複数形
                if "msgid_plural" in entry_dict and entry_dict["msgid_plural"]:
                    entry_kwargs["msgid_plural"] = entry_dict["msgid_plural"]
                    entry_kwargs["msgstr_plural"] = entry_dict.get("msgstr_plural", {})

                # コンテキスト
                if "msgctxt" in entry_dict and entry_dict["msgctxt"]:
                    entry_kwargs["msgctxt"] = entry_dict["msgctxt"]

                # 前バージョン
                if "previous_msgid" in entry_dict and entry_dict["previous_msgid"]:
                    entry_kwargs["previous_msgid"] = entry_dict["previous_msgid"]
                if (
                    "previous_msgid_plural" in entry_dict
                    and entry_dict["previous_msgid_plural"]
                ):
                    entry_kwargs["previous_msgid_plural"] = entry_dict[
                        "previous_msgid_plural"
                    ]
                if "previous_msgctxt" in entry_dict and entry_dict["previous_msgctxt"]:
                    entry_kwargs["previous_msgctxt"] = entry_dict["previous_msgctxt"]

                # コメント
                if "comment" in entry_dict and entry_dict["comment"]:
                    entry_kwargs["comment"] = entry_dict["comment"]
                if "tcomment" in entry_dict and entry_dict["tcomment"]:
                    entry_kwargs["tcomment"] = entry_dict["tcomment"]

                # Fuzzyフラグの設定
                if entry_dict.get("fuzzy", False) and "fuzzy" not in entry_kwargs.get(
                    "flags", []
                ):
                    if "flags" not in entry_kwargs:
                        entry_kwargs["flags"] = []
                    entry_kwargs["flags"].append("fuzzy")

                # エントリを作成して追加
                entry = factory.create_entry(**entry_kwargs)
                pofile.append(entry)

            # POファイルを保存
            pofile.save(str(path))
            logger.debug(f"POファイル保存完了: {path}")
            return True
        except Exception as e:
            logger.error(f"POファイル保存エラー: {e}")
            logger.exception(e)
            return False

    def _clear_cache(self) -> None:
        """キャッシュをクリアする

        すべてのキャッシュを無効化し、フィルタ結果もクリアします。
        ファイルの再読み込みや大きな変更があった場合に呼び出されます。
        """
        self._complete_entry_cache.clear()
        self._entry_basic_info_cache.clear()
        self.filtered_entries = []
        self._force_filter_update = True  # 次回のフィルタ処理で強制的に更新

    def enable_cache(self, enabled: bool = True) -> None:
        """キャッシュを有効/無効にする"""
        self._cache_enabled = enabled
        if not enabled:
            self._clear_cache()

    def prefetch_entries(self, keys: List[str]) -> None:
        """指定されたキーのエントリをプリフェッチする"""
        if not self._cache_enabled or not keys:
            return

        # キャッシュにないキーを特定
        missing_keys = [key for key in keys if key not in self._complete_entry_cache]
        if not missing_keys:
            return

        # 一括取得
        entries = self.db.get_entries_by_keys(missing_keys)

        # キャッシュに保存
        for key, entry in entries.items():
            self._complete_entry_cache[key] = EntryModel.from_dict(entry)

            # 基本情報も更新
            if key in self._entry_basic_info_cache:
                basic_info = {
                    "id": entry.get("id"),
                    "key": entry.get("key"),
                    "msgid": entry.get("msgid", ""),
                    "msgstr": entry.get("msgstr", ""),
                    "fuzzy": entry.get("fuzzy", False),
                    "obsolete": entry.get("obsolete", False),
                    "position": entry.get("position", 0),
                    "flags": entry.get("flags", []),
                    "is_basic_info": True,
                }
                self._entry_basic_info_cache[key] = EntryModel(**basic_info)

    def get_entry_at(self, position: int) -> Optional[EntryModel]:
        """位置（インデックス）からエントリを取得する

        Args:
            position: エントリの位置（インデックス）

        Returns:
            Optional[EntryModel]: 指定された位置のエントリ。見つからない場合はNone
        """
        logger.debug(f"ViewerPOFile.get_entry_at: 位置={position}のエントリを取得")
        try:
            # 位置をキーに変換（キーは文字列型の位置）
            key = str(position)
            # キーを使用してエントリを取得
            return self.get_entry_by_key(key)
        except Exception as e:
            logger.error(f"ViewerPOFile.get_entry_at: エラー発生 {e}", exc_info=True)
            return None

    # 互換性のためのエイリアス
    def get_entry(self, key: str) -> Optional[EntryModel]:
        """get_entry_by_keyのエイリアス（後方互換性のため）

        Args:
            key: エントリのキー

        Returns:
            Optional[EntryModel]: 指定されたキーのエントリ。見つからない場合はNone
        """
        logger.debug(
            f"ViewerPOFile.get_entry: キー={key}のエントリを取得（get_entry_by_keyを使用）"
        )
        return self.get_entry_by_key(key)

    def _generate_filter_cache_key(self) -> str:
        """現在のフィルタ条件からキャッシュキーを生成する

        Returns:
            str: キャッシュキー
        """
        # フィルタ条件を文字列として連結
        flag_conditions_str = (
            "|".join(f"{k}:{v}" for k, v in sorted(self.flag_conditions.items()))
            if self.flag_conditions
            else ""
        )

        # キャッシュキーを生成
        cache_key = (
            f"{self.translation_status}|{self.search_text}|"
            f"{flag_conditions_str}|"
            f"{self.sort_column}|{self.sort_order}"
        )

        return cache_key
