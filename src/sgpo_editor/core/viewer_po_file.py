"""POファイルビューア

このモジュールは、POファイルを読み込み、表示、編集するための機能を提供します。
"""

from pathlib import Path
import logging
import time
from typing import Any, Dict, List, Optional, Union
import polib
from sgpo_editor.models.database import Database

logger = logging.getLogger(__name__)


class ViewerPOFile:
    """POファイルを読み込み、表示するためのクラス"""

    def __init__(self):
        """初期化"""
        self.db = Database()
        self.path = None
        self.filtered_entries = []
        self.filter_text = ""
        self.search_text = ""
        self.sort_column = None
        self.sort_order = None
        self.flag_conditions = {}
        self.translation_status = None
        
        # エントリキャッシュを初期化
        self._entry_cache = {}
        self._basic_info_cache = {}
        self._cache_enabled = True
        self._is_loaded = False

    def load(self, path: Union[str, Path]) -> None:
        """POファイルを読み込む"""
        try:
            start_time = time.time()
            logger.debug(f"POファイル読み込み開始: {path}")
            
            # キャッシュをクリア
            self._clear_cache()

            path = Path(path)
            self.path = path

            # バイナリヘッダを読み込む
            with open(path, "rb") as f:
                header = f.read(10)

            pofile = None
            if header.startswith(b"\xDE\xBB\xBF"):  # UTF-8 BOM
                logger.debug("UTF-8 with BOM検出")
                with open(path, encoding="utf-8-sig") as f:
                    postr = f.read()
                pofile = polib.pofile(postr)
            else:
                logger.debug("通常のPOファイル読み込み")
                pofile = polib.pofile(str(path), encoding="utf-8")

            # データベースをクリア
            self.db.clear()

            # すべてのエントリをデータベースに追加
            entries = []
            for i, entry in enumerate(pofile):
                entry_data = self._convert_entry_to_dict(entry, i)
                entries.append(entry_data)

            # バルクインサートを使用（最適化）
            self.db.add_entries_bulk(entries)

            # 基本情報のキャッシュを一括ロード
            self._load_all_basic_info()
                
            # 完全ロード終了フラグを設定
            self._is_loaded = True
                
            # 処理時間をログに出力
            elapsed = time.time() - start_time
            logger.debug(f"POファイル読み込み完了: {elapsed:.2f}秒")
            
        except Exception as e:
            logger.error(f"POファイル読み込みエラー: {e}")
            raise
            
    def _load_all_basic_info(self) -> None:
        """すべてのエントリの基本情報を一括ロード"""
        try:
            entries_basic_info = self.db.get_all_entries_basic_info()
            for entry in entries_basic_info:
                if 'key' in entry:
                    self._basic_info_cache[entry['key']] = entry
        except Exception as e:
            logger.error(f"基本情報キャッシュロードエラー: {e}")

    def get_entry_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """キーでエントリを取得する（キャッシュ対応）"""
        # キャッシュが無効化されている場合は直接DBから取得
        if not self._cache_enabled:
            return self.db.get_entry_by_key(key)
            
        # 完全なエントリがすでにキャッシュにある場合
        if key in self._entry_cache:
            return self._entry_cache[key]
            
        # 基本情報のみがキャッシュにある場合
        if key in self._basic_info_cache:
            basic_info = self._basic_info_cache[key]
            # is_basic_infoフラグがある場合は詳細情報を取得
            if basic_info.get('is_basic_info', False):
                # DBから完全なエントリ情報を取得
                full_entry = self.db.get_entry_by_key(key)
                if full_entry:
                    # 完全なエントリをキャッシュに保存
                    self._entry_cache[key] = full_entry
                    return full_entry
                return basic_info  # 完全な情報がない場合は基本情報を返す
            return basic_info
            
        # キャッシュにない場合はDBから取得
        entry = self.db.get_entry_by_key(key)
        if entry:
            # 完全なエントリをキャッシュに保存
            self._entry_cache[key] = entry
        return entry

    def get_entries_by_keys(self, keys: List[str]) -> Dict[str, Dict[str, Any]]:
        """複数のキーに対応するエントリを一度に取得"""
        if not keys:
            return {}
            
        # キャッシュから取得できるエントリを確認
        result = {}
        missing_keys = []
        
        for key in keys:
            if key in self._entry_cache:
                # 完全なエントリがキャッシュにある場合
                result[key] = self._entry_cache[key]
            elif key in self._basic_info_cache and not self._basic_info_cache[key].get('is_basic_info', False):
                # 基本情報のみがキャッシュにある場合
                result[key] = self._basic_info_cache[key]
            else:
                # キャッシュにない場合は後でDBから取得するためリストに追加
                missing_keys.append(key)
                
        # キャッシュにないエントリをDBから一括取得
        if missing_keys:
            missing_entries = self.db.get_entries_by_keys(missing_keys)
            for key, entry in missing_entries.items():
                result[key] = entry
                # 完全な情報をキャッシュに保存
                self._entry_cache[key] = entry
                
        return result

    def get_entry_basic_info(self, key: str) -> Optional[Dict[str, Any]]:
        """エントリの基本情報のみを取得する（高速）"""
        # 基本情報がキャッシュにある場合
        if key in self._basic_info_cache:
            return self._basic_info_cache[key]
            
        # 完全なエントリがキャッシュにある場合
        if key in self._entry_cache:
            entry = self._entry_cache[key]
            # 基本情報のみを返す
            basic_info = {
                'id': entry.get('id'),
                'key': entry.get('key'),
                'msgid': entry.get('msgid', ''),
                'msgstr': entry.get('msgstr', ''),
                'fuzzy': entry.get('fuzzy', False),
                'obsolete': entry.get('obsolete', False),
                'position': entry.get('position', 0),
                'flags': entry.get('flags', []),
                'is_basic_info': True
            }
            self._basic_info_cache[key] = basic_info
            return basic_info
            
        # キャッシュにない場合はDBから取得
        basic_info = self.db.get_entry_basic_info(key)
        if basic_info:
            self._basic_info_cache[key] = basic_info
        return basic_info

    def _convert_entry_to_dict(self, entry: Any, position: int) -> Dict[str, Any]:
        """polibエントリをディクショナリに変換する"""
        key = f"{position}"
        entry_dict = {
            "key": key,
            "msgid": entry.msgid,
            "msgstr": entry.msgstr,
            "fuzzy": "fuzzy" in entry.flags,
            "obsolete": entry.obsolete,
            "position": position,
            "flags": entry.flags,
            "references": [f"{ref[0]}:{ref[1]}" if isinstance(ref, tuple) and len(ref) == 2 else str(ref) for ref in entry.occurrences],
        }

        # 複数形
        if hasattr(entry, "msgid_plural") and entry.msgid_plural:
            entry_dict["msgid_plural"] = entry.msgid_plural
            entry_dict["msgstr_plural"] = entry.msgstr_plural

        # コンテキスト
        if hasattr(entry, "msgctxt") and entry.msgctxt:
            entry_dict["msgctxt"] = entry.msgctxt

        # 前バージョン
        if hasattr(entry, "previous_msgid") and entry.previous_msgid:
            entry_dict["previous_msgid"] = entry.previous_msgid
        if hasattr(entry, "previous_msgid_plural") and entry.previous_msgid_plural:
            entry_dict["previous_msgid_plural"] = entry.previous_msgid_plural
        if hasattr(entry, "previous_msgctxt") and entry.previous_msgctxt:
            entry_dict["previous_msgctxt"] = entry.previous_msgctxt

        # コメント
        if hasattr(entry, "comment") and entry.comment:
            entry_dict["comment"] = entry.comment
        if hasattr(entry, "tcomment") and entry.tcomment:
            entry_dict["tcomment"] = entry.tcomment

        return entry_dict

    def get_filtered_entries(self, update_filter: bool = False) -> List[Dict[str, Any]]:
        """フィルタ条件に合ったエントリーを取得する"""
        if update_filter or not self.filtered_entries:
            self.filtered_entries = self.db.get_entries(
                filter_text=self.filter_text,
                search_text=self.search_text,
                sort_column=self.sort_column,
                sort_order=self.sort_order,
                flag_conditions=self.flag_conditions,
                translation_status=self.translation_status,
            )
        return self.filtered_entries

    def set_filter(
        self,
        filter_text: Optional[str] = None,
        search_text: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_order: Optional[str] = None,
        flag_conditions: Optional[Dict[str, Any]] = None,
        translation_status: Optional[str] = None,
    ) -> None:
        """フィルタを設定する"""
        update_needed = False

        if filter_text is not None and filter_text != self.filter_text:
            self.filter_text = filter_text
            update_needed = True

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
            update_needed = True

        if update_needed:
            self.get_filtered_entries(update_filter=True)

    def update_entry(self, entry: Dict[str, Any]) -> None:
        """エントリを更新する"""
        try:
            key = entry.get("key")
            if not key:
                logger.error("エントリの更新に失敗: キーがありません")
                return

            self.db.update_entry(key, entry)
            
            # キャッシュを更新
            self._entry_cache[key] = entry
            
            # 基本情報のキャッシュを更新
            if key in self._basic_info_cache:
                basic_info = {
                    'id': entry.get('id'),
                    'key': entry.get('key'),
                    'msgid': entry.get('msgid', ''),
                    'msgstr': entry.get('msgstr', ''),
                    'fuzzy': entry.get('fuzzy', False),
                    'obsolete': entry.get('obsolete', False),
                    'position': entry.get('position', 0),
                    'flags': entry.get('flags', []),
                    'is_basic_info': True
                }
                self._basic_info_cache[key] = basic_info
                
            # フィルタされたエントリーを更新
            for i, e in enumerate(self.filtered_entries):
                if e.get("key") == key:
                    self.filtered_entries[i] = entry
                    break

        except Exception as e:
            logger.error(f"エントリの更新に失敗: {e}")

    def save(self, path: Optional[Union[str, Path]] = None) -> None:
        """POファイルを保存する"""
        try:
            if path is None:
                path = self.path
            else:
                path = Path(path)

            # データベースからすべてのエントリを取得
            entries = self.db.get_entries(sort_column="position", sort_order="ASC")
            pofile = polib.POFile()

            for entry_dict in entries:
                entry = polib.POEntry(
                    msgid=entry_dict.get("msgid", ""),
                    msgstr=entry_dict.get("msgstr", ""),
                    occurrences=entry_dict.get("references", []),
                    flags=entry_dict.get("flags", []),
                    obsolete=entry_dict.get("obsolete", False),
                )

                # 複数形
                if "msgid_plural" in entry_dict and entry_dict["msgid_plural"]:
                    entry.msgid_plural = entry_dict["msgid_plural"]
                    entry.msgstr_plural = entry_dict.get("msgstr_plural", {})

                # コンテキスト
                if "msgctxt" in entry_dict and entry_dict["msgctxt"]:
                    entry.msgctxt = entry_dict["msgctxt"]

                # 前バージョン
                if "previous_msgid" in entry_dict and entry_dict["previous_msgid"]:
                    entry.previous_msgid = entry_dict["previous_msgid"]
                if (
                    "previous_msgid_plural" in entry_dict
                    and entry_dict["previous_msgid_plural"]
                ):
                    entry.previous_msgid_plural = entry_dict["previous_msgid_plural"]
                if "previous_msgctxt" in entry_dict and entry_dict["previous_msgctxt"]:
                    entry.previous_msgctxt = entry_dict["previous_msgctxt"]

                # コメント
                if "comment" in entry_dict and entry_dict["comment"]:
                    entry.comment = entry_dict["comment"]
                if "tcomment" in entry_dict and entry_dict["tcomment"]:
                    entry.tcomment = entry_dict["tcomment"]

                # Fuzzyフラグの設定
                if entry_dict.get("fuzzy", False) and "fuzzy" not in entry.flags:
                    entry.flags.append("fuzzy")

                pofile.append(entry)

            pofile.save(str(path))
            logger.info(f"POファイルを保存しました: {path}")

        except Exception as e:
            logger.error(f"POファイルの保存に失敗: {e}")
            raise

    def _clear_cache(self) -> None:
        """キャッシュをクリアする"""
        self._entry_cache.clear()
        self._basic_info_cache.clear()
        self._is_loaded = False
        
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
        missing_keys = [key for key in keys if key not in self._entry_cache]
        if not missing_keys:
            return
            
        # 一括取得
        entries = self.db.get_entries_by_keys(missing_keys)
        
        # キャッシュに保存
        for key, entry in entries.items():
            self._entry_cache[key] = entry
            
            # 基本情報も更新
            if key in self._basic_info_cache:
                basic_info = {
                    'id': entry.get('id'),
                    'key': entry.get('key'),
                    'msgid': entry.get('msgid', ''),
                    'msgstr': entry.get('msgstr', ''),
                    'fuzzy': entry.get('fuzzy', False),
                    'obsolete': entry.get('obsolete', False),
                    'position': entry.get('position', 0),
                    'flags': entry.get('flags', []),
                    'is_basic_info': True
                }
                self._basic_info_cache[key] = basic_info
