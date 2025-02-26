"""POファイルを読み書きするクラス"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, cast, TypeVar, Sequence, Protocol, Type, Iterator, Collection, overload, runtime_checkable, Generic

import polib
import sgpo_editor.sgpo as sgpo

from sgpo_editor.models.database import Database
from sgpo_editor.gui.models.entry import EntryModel
from sgpo_editor.types.po_entry import POEntry
from sgpo_editor.sgpo import SGPOFile
from sgpo_editor.gui.models.stats import StatsModel

logger = logging.getLogger(__name__)

T = TypeVar('T')
T_co = TypeVar('T_co', covariant=True)


class SequenceProtocol(Protocol[T_co]):
    """シーケンスのプロトコル定義"""

    def __iter__(self) -> Iterator[T_co]:
        """イテレータ"""
        ...

    def __len__(self) -> int:
        """長さ"""
        ...

    def __contains__(self, item: object) -> bool:
        """アイテムの存在確認"""
        ...

    def __getitem__(self, index: int) -> T_co:
        """インデックスによる値の取得"""
        ...


@runtime_checkable
class POFileProtocol(Protocol):
    """POファイルのプロトコル定義"""

    def __iter__(self) -> Iterator[POEntry]:
        """イテレータ"""
        ...

    def __len__(self) -> int:
        """長さ"""
        ...

    def __contains__(self, item: object) -> bool:
        """アイテムの存在確認"""
        ...

    @overload
    def __getitem__(self, key: int) -> POEntry:
        """インデックスによる値の取得"""
        ...

    @overload
    def __getitem__(self, key: str) -> POEntry:
        """キーによる値の取得"""
        ...

    def __getitem__(self, key: Union[str, int]) -> POEntry:
        """キーまたはインデックスによる値の取得"""
        ...

    def save(self, path: Optional[str] = None) -> None:
        """POファイルを保存する"""
        ...

    def clear(self) -> None:
        """全てのデータを削除"""
        ...

    def append(self, entry: POEntry) -> None:
        """エントリを追加"""
        ...


class DatabaseProtocol(Protocol):
    """データベースのプロトコル定義"""

    def clear(self) -> None:
        """全てのデータを削除"""
        ...

    def add_entries_bulk(self, entries: List[Dict[str, Any]]) -> None:
        """バルクインサートでエントリを追加"""
        ...

    def update_entry(self, key: str, entry: Dict[str, Any]) -> None:
        """エントリを更新"""
        ...

    def reorder_entries(self, entry_ids: List[int]) -> None:
        """エントリの表示順序を変更"""
        ...

    def get_entries(
        self,
        filter_text: Optional[str] = None,
        search_text: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[Dict[str, Any]] = None,
        translation_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """エントリの一覧を取得"""
        ...

    def get_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        """エントリを取得"""
        ...

    def get_entry_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """キーでエントリを取得"""
        ...


def ensure_not_none(value: Optional[T], message: str = "値がNoneです") -> T:
    """Noneでないことを保証する

    Args:
        value: チェックする値
        message: エラーメッセージ

    Returns:
        T: Noneでない値

    Raises:
        ValueError: 値がNoneの場合
    """
    if value is None:
        raise ValueError(message)
    return value


class ViewerPOFile:
    """POファイルを読み書きするクラス"""

    def __init__(self, path: Optional[Union[str, Path]] = None):
        """初期化

        Args:
            path: POファイルのパス（Noneの場合は空のPOファイルを作成）
        """
        self._po_file: Optional[POFileProtocol] = None
        self._db: DatabaseProtocol = Database()
        self._modified = False
        self._path: Optional[Path] = None
        self._entries: List[EntryModel] = []
        self._filtered_entries: List[EntryModel] = []
        self._filter_text: str = ""
        self._show_translated: bool = True
        self._show_untranslated: bool = True
        self._show_fuzzy: bool = True

        if path:
            self.load(path)

    @property
    def file_path(self) -> Optional[Path]:
        """ファイルパスを取得"""
        return self._path

    @property
    def modified(self) -> bool:
        """変更フラグを取得"""
        return self._modified

    def load(self, path: Union[str, Path]) -> None:
        """POファイルを読み込む

        Args:
            path: POファイルのパス
        """
        logger.info("POファイル読み込み開始: %s", path)
        start_time = time.time()
        error_count = 0

        try:
            # POファイルを読み込む
            self._po_file = cast(POFileProtocol, SGPOFile.from_file(str(path)))
            self._path = Path(path)
            self._db.clear()

            # エントリをデータベースに追加
            entries_to_insert: List[Dict[str, Any]] = []
            for i, entry in enumerate(self._po_file):
                try:
                    # エントリの作成
                    entry_model = EntryModel.from_po_entry(entry, position=i)
                    entries_to_insert.append(entry_model.model_dump())
                except Exception as e:
                    error_count += 1
                    logger.error(
                        "エントリの追加に失敗 [%d/%d]: %s",
                        i + 1,
                        len(self._po_file),
                        e,
                        exc_info=True
                    )

            # バルクインサート実行
            if entries_to_insert:
                self._db.add_entries_bulk(entries_to_insert)

            self._entries = self.get_entries()
            self._filtered_entries = self._entries.copy()

            elapsed_time = time.time() - start_time
            logger.info(
                "POファイル読み込み完了: %d件のエントリを読み込みました（成功: %d件、失敗: %d件、所要時間: %.2f秒）",
                len(self._po_file),
                len(self._po_file) - error_count,
                error_count,
                elapsed_time
            )
            self._modified = False

        except Exception as e:
            logger.error("POファイルの読み込みに失敗: %s", e, exc_info=True)
            raise

    def save(self, path: Optional[Union[str, Path]] = None) -> None:
        """POファイルを保存する

        Args:
            path: 保存先のパス（Noneの場合は現在のパスに保存）
        """
        save_path = path or self._path
        if not save_path:
            raise ValueError("保存先のパスが指定されていません")

        logger.info("POファイル保存開始: %s", save_path)
        start_time = time.time()

        try:
            # データベースからエントリを取得
            entries = self.get_entries()

            # POファイルを更新
            po_file = ensure_not_none(self._po_file, "POファイルが読み込まれていません")
            po_file.clear()
            for entry in entries:
                po_entry = cast(POEntry, polib.POEntry(
                    msgid=entry.msgid,
                    msgstr=entry.msgstr,
                    msgctxt=entry.msgctxt,
                    occurrences=[(ref.split(":")[0], ref.split(":")[1]) for ref in entry.references],
                    flags=entry.flags,
                    obsolete=entry.obsolete,
                    previous_msgid=entry.previous_msgid,
                    previous_msgid_plural=entry.previous_msgid_plural,
                    previous_msgctxt=entry.previous_msgctxt,
                    comment=entry.comment,
                    tcomment=entry.tcomment,
                ))
                po_file.append(po_entry)

            # POファイルを保存
            po_file.save(str(save_path))
            self._path = Path(save_path)
            self._modified = False

            elapsed_time = time.time() - start_time
            logger.info(
                "POファイル保存完了: %d件のエントリを保存しました（所要時間: %.2f秒）",
                len(entries),
                elapsed_time
            )

        except Exception as e:
            logger.error("POファイルの保存に失敗: %s", e, exc_info=True)
            raise

    def get_entries(
        self,
        filter_text: Optional[str] = None,
        filter_keyword: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flags: Optional[List[str]] = None,
        exclude_flags: Optional[List[str]] = None,
        only_fuzzy: bool = False,
        only_translated: bool = False,
        only_untranslated: bool = False,
    ) -> List[EntryModel]:
        """エントリの一覧を取得"""
        # フラグによるフィルタリング条件を構築
        flag_conditions: Dict[str, Any] = {}
        if flags:
            flag_conditions["include_flags"] = flags
        if exclude_flags:
            flag_conditions["exclude_flags"] = exclude_flags
        if only_fuzzy:
            flag_conditions["only_fuzzy"] = True

        # 翻訳状態によるフィルタリング
        translation_status = None
        if only_translated:
            translation_status = "translated"
        elif only_untranslated:
            translation_status = "untranslated"

        entries = self._db.get_entries(
            filter_text=filter_text,
            search_text=filter_keyword,  # データベースのインターフェースは変更しない
            sort_column=sort_column,
            sort_order=sort_order,
            flag_conditions=flag_conditions,
            translation_status=translation_status
        )

        # エントリをモデルに変換する前に、必要なフィールドが存在することを確認
        for entry in entries:
            if "flags" not in entry or entry["flags"] is None:
                entry["flags"] = []
            if "id" in entry and isinstance(entry["id"], int):
                entry["id"] = str(entry["id"])

        return [EntryModel.model_validate(entry) for entry in entries]

    def get_entry(self, entry_id: int) -> Optional[EntryModel]:
        """エントリを取得"""
        entry = self._db.get_entry(entry_id)
        return EntryModel.model_validate(entry) if entry else None

    def get_entry_by_key(self, key: str) -> Optional[EntryModel]:
        """キーでエントリを取得"""
        entry = self._db.get_entry_by_key(key)
        return EntryModel.model_validate(entry) if entry else None

    def update_entry(self, entry: EntryModel) -> None:
        """エントリを更新する

        Args:
            entry: 更新するエントリ
        """
        self._db.update_entry(entry.key, entry.model_dump())
        self._modified = True

        if self._po_file is None:
            return

        po_entry = self._po_file[entry.position]
        po_entry = cast(POEntry, po_entry)
        po_entry.msgstr = entry.msgstr
        po_entry.flags = entry.flags

        self._entries[entry.position] = entry
        if entry in self._filtered_entries:
            index = self._filtered_entries.index(entry)
            self._filtered_entries[index] = entry

    def reorder_entries(self, entry_ids: List[int]) -> None:
        """エントリの表示順序を変更"""
        self._db.reorder_entries(entry_ids)
        self._modified = True

    def get_stats(self) -> StatsModel:
        """統計情報を取得する

        Returns:
            StatsModel: 統計情報
        """
        entries = self.get_entries()
        total = len(entries)
        translated = len([e for e in entries if e.msgstr and not e.fuzzy])
        fuzzy = len([e for e in entries if e.fuzzy])
        untranslated = total - translated - fuzzy

        return StatsModel(
            total=total,
            translated=translated,
            fuzzy=fuzzy,
            untranslated=untranslated,
            file_name=str(self._path) if self._path else ""
        )

    def search_entries(self, filter_keyword: str) -> List[EntryModel]:
        """エントリをフィルタリングする

        Args:
            filter_keyword: フィルタキーワード

        Returns:
            List[EntryModel]: フィルタリング結果のエントリリスト
        """
        entries = self._db.get_entries(search_text=filter_keyword)
        return [EntryModel.model_validate(entry) for entry in entries]

    def save_po_file(self) -> None:
        """現在のパスにPOファイルを保存する"""
        if not self._path:
            raise ValueError("保存先のパスが指定されていません")
        self.save(self._path)

    def get_filtered_entries(
        self,
        filter_text: Optional[str] = None,
        show_translated: Optional[bool] = None,
        show_untranslated: Optional[bool] = None,
        show_fuzzy: Optional[bool] = None,
        filter_keyword: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> List[EntryModel]:
        """フィルタリングされたエントリの一覧を取得する

        Args:
            filter_text: フィルターテキスト
            show_translated: 翻訳済みを表示するかどうか
            show_untranslated: 未翻訳を表示するかどうか
            show_fuzzy: 要確認を表示するかどうか
            filter_keyword: フィルタキーワード
            sort_column: ソート列
            sort_order: ソート順序

        Returns:
            List[EntryModel]: フィルタリングされたエントリの一覧
        """
        # フィルター設定の更新
        if filter_text is not None:
            self._filter_text = filter_text
        if show_translated is not None:
            self._show_translated = show_translated
        if show_untranslated is not None:
            self._show_untranslated = show_untranslated
        if show_fuzzy is not None:
            self._show_fuzzy = show_fuzzy
            
        # 翻訳状態フィルターの設定
        only_translated = False
        only_untranslated = False
        only_fuzzy = False
        
        if self._filter_text == "翻訳済み":
            only_translated = True
            only_untranslated = False
            only_fuzzy = False
        elif self._filter_text == "未翻訳":
            only_translated = False
            only_untranslated = True
            only_fuzzy = False
        elif self._filter_text == "ファジー":
            only_translated = False
            only_untranslated = False
            only_fuzzy = True

        # データベースからエントリを取得
        entries = self.get_entries(
            filter_text=None,  # フィルターテキストは使用せず、翻訳状態で絞り込む
            filter_keyword=filter_keyword,  # フィルタキーワードはデータベースクエリではなく後処理で使用
            sort_column=sort_column,
            sort_order=sort_order,
            only_fuzzy=only_fuzzy,
            only_translated=only_translated,
            only_untranslated=only_untranslated,
        )
        
        # フィルタキーワードによる二次フィルタリング
        if filter_keyword and filter_keyword.strip():
            filter_keyword = filter_keyword.lower().strip()
            filtered_entries = []
            for entry in entries:
                # msgid, msgstr, msgctxtのいずれかにフィルタキーワードが含まれるエントリを抽出
                if ((entry.msgid and filter_keyword in entry.msgid.lower()) or
                    (entry.msgstr and filter_keyword in entry.msgstr.lower()) or
                    (entry.msgctxt and filter_keyword in entry.msgctxt.lower())):
                    filtered_entries.append(entry)
            entries = filtered_entries

        self._filtered_entries = entries
        return entries
