"""POファイルビューア

このモジュールは、POファイルを読み込み、表示、編集するための機能を提供します。
"""

from pathlib import Path
import logging
import time
from typing import Any, Dict, List, Optional, Union
from collections import namedtuple
import polib
from sgpo_editor.models.database import Database
from sgpo_editor.models.entry_model import Entry

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
        self.modified = False
        
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
            # get_all_entries_basic_infoが存在しないため、get_entriesを使用
            entries_basic_info = self.db.get_entries()
            for entry in entries_basic_info:
                if 'key' in entry:
                    # 基本情報としてマーク
                    entry['is_basic_info'] = True
                    self._basic_info_cache[entry['key']] = entry
        except Exception as e:
            logger.error(f"基本情報キャッシュロードエラー: {e}")

    def get_entry_by_key(self, key: str) -> Optional[Entry]:
        """キーでエントリを取得する（キャッシュ対応）"""
        # キャッシュが無効化されている場合は直接DBから取得
        if not self._cache_enabled:
            entry_dict = self.db.get_entry_by_key(key)
            return Entry.from_dict(entry_dict) if entry_dict else None
            
        # 完全なエントリがすでにキャッシュにある場合
        if key in self._entry_cache:
            # キャッシュがEntryオブジェクトかどうか確認
            cached_entry = self._entry_cache[key]
            if isinstance(cached_entry, Entry):
                return cached_entry
            else:
                # 辞書の場合はEntryオブジェクトに変換してキャッシュを更新
                entry_obj = Entry.from_dict(cached_entry)
                self._entry_cache[key] = entry_obj
                return entry_obj
            
        # 基本情報のみがキャッシュにある場合
        if key in self._basic_info_cache:
            basic_info = self._basic_info_cache[key]
            # 基本情報がEntryオブジェクトかどうか確認
            if isinstance(basic_info, Entry):
                # is_basic_infoフラグがある場合は詳細情報を取得
                if getattr(basic_info, 'is_basic_info', False):
                    # DBから完全なエントリ情報を取得
                    full_entry_dict = self.db.get_entry_by_key(key)
                    if full_entry_dict:
                        # 完全なエントリをEntryオブジェクトに変換してキャッシュに保存
                        full_entry = Entry.from_dict(full_entry_dict)
                        self._entry_cache[key] = full_entry
                        return full_entry
                    return basic_info  # 完全な情報がない場合は基本情報を返す
                return basic_info
            else:
                # 辞書の場合はEntryオブジェクトに変換
                is_basic_info = basic_info.get('is_basic_info', False)
                entry_obj = Entry.from_dict(basic_info)
                
                if is_basic_info:
                    # DBから完全なエントリ情報を取得
                    full_entry_dict = self.db.get_entry_by_key(key)
                    if full_entry_dict:
                        # 完全なエントリをEntryオブジェクトに変換してキャッシュに保存
                        full_entry = Entry.from_dict(full_entry_dict)
                        self._entry_cache[key] = full_entry
                        return full_entry
                    
                    # 基本情報をキャッシュに保存
                    self._basic_info_cache[key] = entry_obj
                    return entry_obj
                
                # 基本情報をキャッシュに保存
                self._basic_info_cache[key] = entry_obj
                return entry_obj
            
        # キャッシュにない場合はDBから取得
        entry_dict = self.db.get_entry_by_key(key)
        if entry_dict:
            # 辞書をEntryオブジェクトに変換
            entry_obj = Entry.from_dict(entry_dict)
            # 完全なエントリをキャッシュに保存
            self._entry_cache[key] = entry_obj
            return entry_obj
        return None

    def get_entries_by_keys(self, keys: List[str]) -> Dict[str, Entry]:
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
                result[key] = Entry.from_dict(entry)
                # 完全な情報をキャッシュに保存
                self._entry_cache[key] = result[key]
                
        return result

    def get_entry_basic_info(self, key: str) -> Optional[Entry]:
        """エントリの基本情報のみを取得する（高速）"""
        # 基本情報がキャッシュにある場合
        if key in self._basic_info_cache:
            return self._basic_info_cache[key]
            
        # 完全なエントリがキャッシュにある場合
        if key in self._entry_cache:
            entry = self._entry_cache[key]
            # 基本情報のみを返す
            basic_info = Entry.from_dict({
                'id': entry.id,
                'key': entry.key,
                'msgid': entry.msgid,
                'msgstr': entry.msgstr,
                'fuzzy': entry.fuzzy,
                'obsolete': entry.obsolete,
                'position': entry.position,
                'flags': entry.flags,
                'is_basic_info': True
            })
            self._basic_info_cache[key] = basic_info
            return basic_info
            
        # キャッシュにない場合はDBから取得
        basic_info = self.db.get_entry_basic_info(key)
        if basic_info:
            self._basic_info_cache[key] = Entry.from_dict(basic_info)
        return self._basic_info_cache.get(key)

    def _convert_entry_to_dict(self, entry: polib.POEntry, position: int) -> Dict[str, Any]:
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

    def get_filtered_entries(
        self, 
        update_filter: bool = False,
        filter_text: Optional[str] = None,
        filter_keyword: Optional[str] = None
    ) -> List[Entry]:
        """フィルタ条件に合ったエントリーを取得する"""
        if update_filter or not self.filtered_entries:
            # パラメータが指定された場合はそれを使用し、そうでない場合はインスタンス変数を使用
            actual_filter_text = filter_text if filter_text is not None else self.filter_text
            actual_search_text = filter_keyword if filter_keyword is not None else self.search_text
            
            # 辞書のリストを取得
            entries_dict = self.db.get_entries(
                filter_text=actual_filter_text,
                search_text=actual_search_text,
                sort_column=self.sort_column,
                sort_order=self.sort_order,
                flag_conditions=self.flag_conditions,
                translation_status=self.translation_status,
            )
            
            # エントリキャッシュを初期化（存在しない場合）
            if not hasattr(self, '_entry_obj_cache'):
                self._entry_obj_cache = {}
                
            # 辞書のリストをEntryオブジェクトのリストに変換（キャッシュを活用）
            result = []
            for entry_dict in entries_dict:
                key = entry_dict.get("key", "")
                # キーが存在し、キャッシュにある場合はキャッシュから取得
                if key and key in self._entry_obj_cache:
                    # 既存のEntryオブジェクトを更新（必要な場合）
                    entry_obj = self._entry_obj_cache[key]
                    # 重要なフィールドが変更されている場合のみ更新
                    if (entry_obj.msgid != entry_dict.get("msgid", "") or 
                        entry_obj.msgstr != entry_dict.get("msgstr", "") or
                        entry_obj.fuzzy != entry_dict.get("fuzzy", False)):
                        # 新しいオブジェクトを作成してキャッシュを更新
                        entry_obj = Entry.from_dict(entry_dict)
                        self._entry_obj_cache[key] = entry_obj
                else:
                    # 新しいEntryオブジェクトを作成してキャッシュに追加
                    entry_obj = Entry.from_dict(entry_dict)
                    if key:
                        self._entry_obj_cache[key] = entry_obj
                
                result.append(entry_obj)
            
            self.filtered_entries = result
            
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

    def update_entry(self, entry: Union[Dict[str, Any], Entry]) -> bool:
        """エントリを更新する"""
        try:
            # Entryオブジェクトを辞書に変換（必要な場合）
            entry_dict = entry.to_dict() if isinstance(entry, Entry) else entry
            
            # データベースを更新
            result = self.db.update_entry(entry_dict)
            
            # キャッシュを更新
            if result and self._cache_enabled and "key" in entry_dict:
                key = entry_dict["key"]
                # Entryオブジェクトをキャッシュに保存
                entry_obj = entry if isinstance(entry, Entry) else Entry.from_dict(entry_dict)
                
                if key in self._entry_cache:
                    self._entry_cache[key] = entry_obj
                    
                if key in self._basic_info_cache:
                    # 基本情報キャッシュも更新
                    basic_info_dict = {
                        'key': entry_obj.key,
                        'msgid': entry_obj.msgid,
                        'msgstr': entry_obj.msgstr,
                        'fuzzy': entry_obj.fuzzy,
                        'obsolete': entry_obj.obsolete,
                        'position': entry_obj.position,
                        'flags': entry_obj.flags,
                        'is_basic_info': True
                    }
                    self._basic_info_cache[key] = Entry.from_dict(basic_info_dict)
            
            # 変更フラグを設定
            self.modified = True
            
            return result
        except Exception as e:
            logger.error(f"エントリ更新エラー: {e}")
            return False

    def update_entries(self, entries: Dict[str, Union[Dict[str, Any], Entry]]) -> bool:
        """複数のエントリを一括更新する"""
        try:
            # Entryオブジェクトを辞書に変換（必要な場合）
            entries_dict = {}
            for key, entry in entries.items():
                entries_dict[key] = entry.to_dict() if isinstance(entry, Entry) else entry
            
            # データベースを更新
            result = self.db.update_entries(entries_dict)
            
            # キャッシュを更新
            if result and self._cache_enabled:
                for key, entry in entries.items():
                    entry_obj = entry if isinstance(entry, Entry) else Entry.from_dict(entries_dict[key])
                    
                    # 完全なエントリキャッシュを更新
                    self._entry_cache[key] = entry_obj
                    
                    # 基本情報キャッシュも更新
                    if key in self._basic_info_cache:
                        basic_info_dict = {
                            'key': entry_obj.key,
                            'msgid': entry_obj.msgid,
                            'msgstr': entry_obj.msgstr,
                            'fuzzy': entry_obj.fuzzy,
                            'obsolete': entry_obj.obsolete,
                            'position': entry_obj.position,
                            'flags': entry_obj.flags,
                            'is_basic_info': True
                        }
                        self._basic_info_cache[key] = Entry.from_dict(basic_info_dict)
            
            # 変更フラグを設定
            self.modified = True
            
            return result
        except Exception as e:
            logger.error(f"複数エントリ更新エラー: {e}")
            return False
            
    def import_entries(self, entries: Dict[str, Union[Dict[str, Any], Entry]]) -> bool:
        """エントリをインポートする（既存エントリの上書き）"""
        try:
            # Entryオブジェクトを辞書に変換（必要な場合）
            entries_dict = {}
            for key, entry in entries.items():
                entries_dict[key] = entry.to_dict() if isinstance(entry, Entry) else entry
            
            # データベースにインポート
            result = self.db.import_entries(entries_dict)
            
            # キャッシュに保存
            if result and self._cache_enabled:
                for key, entry in entries.items():
                    entry_obj = entry if isinstance(entry, Entry) else Entry.from_dict(entries_dict[key])
                    
                    # 完全なエントリキャッシュを更新
                    self._entry_cache[key] = entry_obj
                    
                    # 基本情報も更新
                    if key in self._basic_info_cache:
                        basic_info_dict = {
                            'key': entry_obj.key,
                            'msgid': entry_obj.msgid,
                            'msgstr': entry_obj.msgstr,
                            'fuzzy': entry_obj.fuzzy,
                            'obsolete': entry_obj.obsolete,
                            'position': entry_obj.position,
                            'flags': entry_obj.flags,
                            'is_basic_info': True
                        }
                        self._basic_info_cache[key] = Entry.from_dict(basic_info_dict)
            
            # 変更フラグを設定
            self.modified = True
            
            return result
        except Exception as e:
            logger.error(f"エントリインポートエラー: {e}")
            return False

    def get_stats(self) -> Any:
        """翻訳の統計情報を取得する"""
        # namedtupleを作成
        Stats = namedtuple("Stats", ["total", "translated", "fuzzy", "untranslated", "progress"])
        
        # すべてのエントリを取得
        entries = self.get_filtered_entries()
        
        # 統計情報を計算
        total = len(entries)
        translated = 0
        fuzzy = 0
        untranslated = 0
        
        for entry in entries:
            # fuzzyフラグがあるかチェック
            flags = entry.get("flags", [])
            if flags and "fuzzy" in flags:
                fuzzy += 1
            # 翻訳済みかチェック
            elif entry.get("msgstr") and entry["msgstr"].strip():
                translated += 1
            else:
                untranslated += 1
        
        # 進捗率を計算（パーセント表示）
        progress = (translated / total * 100) if total > 0 else 0.0
                
        return Stats(total=total, translated=translated, fuzzy=fuzzy, untranslated=untranslated, progress=progress)

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
            self._entry_cache[key] = Entry.from_dict(entry)
            
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
                self._basic_info_cache[key] = Entry.from_dict(basic_info)
