"""POファイル統計・保存クラス

このモジュールは、POファイルの統計情報取得と保存機能を提供します。
ViewerPOFileUpdaterを継承し、統計情報と保存に関連する機能を実装します。
"""

import logging
from collections import namedtuple
from pathlib import Path
from typing import Optional, Union

from sgpo_editor.core.po_factory import get_po_factory
from sgpo_editor.core.viewer_po_file_updater import ViewerPOFileUpdater

logger = logging.getLogger(__name__)

# 統計情報用のnamedtuple定義
Stats = namedtuple(
    "Stats", ["total", "translated", "fuzzy", "untranslated", "progress"]
)


class ViewerPOFileStats(ViewerPOFileUpdater):
    """POファイルの統計情報取得と保存機能を提供するクラス

    このクラスは、ViewerPOFileUpdaterを継承し、統計情報と保存に関連する機能を実装します。
    """

    def get_stats(self) -> Stats:
        """統計情報を取得する

        Returns:
            Stats: 統計情報を含むnamedtupleオブジェクト
        """
        logger.debug("ViewerPOFileStats.get_stats: 統計情報取得開始")

        # フィルタリングされたエントリを取得
        entries = self.get_filtered_entries()

        # エントリがない場合は空の統計情報を返す
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
        """POファイルを保存する

        Args:
            path: 保存先のパス（省略時は読み込み元のパスを使用）

        Returns:
            bool: 保存が成功したかどうか
        """
        try:
            if path is None:
                path = self.path
            else:
                path = Path(path)

            # データベースからすべてのエントリを取得
            entries = self.db_accessor.get_filtered_entries(
                sort_column="position", sort_order="ASC"
            )

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

            # 変更フラグをリセット
            self.modified = False

            return True
        except Exception as e:
            logger.error(f"POファイル保存エラー: {e}")
            logger.exception(e)
            return False
