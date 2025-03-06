from __future__ import annotations

import os
import re
from enum import Enum
from os import PathLike
from typing import Any, Dict, List, Optional, Union

import polib
from pydantic import BaseModel, ConfigDict

from . import duplicate_checker
from .duplicate_checker import DuplicateEntry


class DiffStatus(str, Enum):
    """差分の状態を表すEnum"""

    NEW = "new"
    REMOVED = "removed"
    MODIFIED = "modified"


class KeyTuple(BaseModel):
    """POファイルのエントリを一意に識別するためのキー"""
    model_config = ConfigDict(frozen=True)  # イミュータブルにする（NamedTupleと同様）

    msgctxt: str
    msgid: str


class DiffEntry(BaseModel):
    """POファイルのエントリの差分情報"""
    key: KeyTuple
    status: DiffStatus
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class DiffResult(BaseModel):
    """POファイル間の差分結果"""
    new_entries: list[DiffEntry] = []
    removed_entries: list[DiffEntry] = []
    modified_entries: list[DiffEntry] = []

    def __bool__(self) -> bool:
        return bool(self.new_entries or self.removed_entries or self.modified_entries)


def pofile(filename: str) -> SGPOFile:
    return SGPOFile.from_file(filename)


def pofile_from_text(text: str) -> SGPOFile:
    return SGPOFile.from_text(text)


class SGPOFile(polib.POFile):
    """SmartGit用のPOファイル操作クラス"""
    META_DATA_BASE_DICT: Dict[str, str] = {
        "Project-Id-Version": "SmartGit",
        "Report-Msgid-Bugs-To": "https://github.com/syntevo/smartgit-translations",
        "POT-Creation-Date": "",
        "PO-Revision-Date": "",
        "Last-Translator": "",
        "Language-Team": "",
        "Language": "",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": "nplurals=1; plural=0;",
    }

    def __init__(self) -> None:
        super().__init__(self)
        self.wrapwidth = 9999
        self.charset = "utf-8"
        self.check_for_duplicates = True

    @classmethod
    def from_file(cls, filename: str) -> SGPOFile:
        """ファイルからSGPOFileインスタンスを作成します。

        Args:
            filename: POファイルのパス（.po、.pot、または数字_数字形式）

        Returns:
            SGPOFileインスタンス

        Raises:
            ValueError: ファイルパスが無効な場合（None、未対応の形式）
            FileNotFoundError: ファイルが存在しない場合

        Note:
            - ファイル名は_validate_filenameメソッドで検証されます
            - 作成されたインスタンスは以下の設定を持ちます：
              - wrapwidth: 9999（行折り返しを防止）
              - charset: utf-8
              - check_for_duplicates: True
        """
        cls._validate_filename(filename)
        return cls._create_instance(filename)

    @classmethod
    def from_text(cls, text: str) -> SGPOFile:
        """テキストからSGPOFileインスタンスを作成します。

        Args:
            text: POファイルの内容（UTF-8でエンコードされたテキスト）

        Returns:
            SGPOFileインスタンス

        Note:
            - テキストは直接polibに渡されて解析されます
            - 作成されたインスタンスは以下の設定を持ちます：
              - wrapwidth: 9999（行折り返しを防止）
              - charset: utf-8
              - check_for_duplicates: True
        """
        return cls._create_instance(text)

    @classmethod
    def _create_instance(cls, source: Union[str, PathLike[str]]) -> SGPOFile:
        """SGPOFileインスタンスを作成する内部メソッドです。

        Args:
            source: POファイルのパスまたはPOファイルの内容

        Returns:
            SGPOFileインスタンス

        Note:
            - polibを使用してPOファイルを解析し、SGPOFileインスタンスを作成
            - インスタンスの設定：
              - wrapwidth: 9999（行折り返しを防止）
              - charset: utf-8
              - check_for_duplicates: True
            - 作成されたインスタンスにはpolibのインスタンス変数とエントリが継承されます
        """
        instance = cls.__new__(cls)
        po = polib.pofile(str(source), wrapwidth=9999, charset="utf-8", check_for_duplicates=True)

        instance.__dict__ = po.__dict__
        for entry in po:
            instance.append(entry)

        return instance

    def import_unknown(self, unknown: SGPOFile) -> None:
        """未知のエントリをインポートします。

        Args:
            unknown: インポート元のPOファイル

        Note:
            - 既存のエントリは上書きされません
            - インポート結果は標準出力に表示されます
        """
        success_count = 0
        print("\nImport unknown entry...")
        for unknown_entry in unknown:
            # unknown_entry.flags = ['New']  # For debugging.
            my_entry = self.find_by_key(unknown_entry.msgctxt, unknown_entry.msgid)

            if my_entry is not None:
                if my_entry.msgid == unknown_entry.msgid:
                    print("\nAlready exists.(Skipped)")
                    print(f'\t\tmsgctxt "{unknown_entry.msgctxt}"')
                    print(f'\t\tmsgid "{unknown_entry.msgid}"')
                else:
                    print("\nAlready exists. but,msgid has been changed.(Skipped)")
                    print(f'\t\t#| msgid "{my_entry.msgid}"')
                    print(f'\t\tmsgctxt "{unknown_entry.msgctxt}"')
                    print(f'\t\tmsgid "{unknown_entry.msgid}"')
            else:
                try:
                    self.append(unknown_entry)
                    print("\nNew entry added.")
                    print(f'\t\tmsgctxt "{unknown_entry.msgctxt}')
                    print(f'\t\tmsgid "{unknown_entry.msgid}')
                    success_count += 1
                except ValueError as e:
                    print(e)
                except OSError as e:
                    print(e)

        print(f"{success_count} entries added.")

    def import_mismatch(self, mismatch: SGPOFile) -> None:
        """不一致のエントリをインポートします。

        Args:
            mismatch: インポート元のPOファイル

        Note:
            - 既存のエントリは上書きされます
            - インポート結果は標準出力に表示されます
        """
        new_entry_count = 0
        modified_entry_count = 0

        print("\nImport unknown entry...")
        for mismatch_entry in mismatch:
            # mismatch_entry.flags = ['Modified']  # For debugging.
            my_entry = self.find_by_key(mismatch_entry.msgctxt, mismatch_entry.msgid)

            if my_entry is not None:
                if my_entry.msgid == mismatch_entry.msgid:
                    print("\nAlready exists.(Skipped)")
                    print(f'\t\t#| msgid "{my_entry.previous_msgid}"')
                    print(f'\t\tmsgctxt "{my_entry.msgctxt}"')
                    print(f'\t\tmsgid "{my_entry.msgid}"')
                else:
                    print("\nmsgid has been changed.")
                    print(f'\t\t#| msgid "{my_entry.msgid}"')
                    print(f'\t\tmsgctxt "{mismatch_entry.msgctxt}"')
                    print(f'\t\tmsgid "{mismatch_entry.msgid}"')
                    my_entry.previous_msgid = my_entry.msgid
                    my_entry.msgid = mismatch_entry.msgid
                    modified_entry_count += 1
            else:
                try:
                    self.append(mismatch_entry)
                    print("\nNew entry added.")
                    print(f'\t\tmsgctxt "{mismatch_entry.msgctxt}"')
                    print(f'\t\tmsgid "{mismatch_entry.msgid}"')
                    new_entry_count += 1
                except ValueError as e:
                    print(e)
                except OSError as e:
                    print(e)

        print(f"{new_entry_count} entries added.")
        print(f"{modified_entry_count} entries modified.")

    def import_pot(self, pot: SGPOFile) -> None:
        """POTファイルからエントリをインポートします。

        Args:
            pot: インポート元のPOTファイル

        Note:
            - 新規エントリが追加されます
            - 削除されたエントリは obsolete フラグが設定されます
            - 変更されたエントリは fuzzy フラグが設定されます
            - インポート結果は標準出力に表示されます
        """
        new_entry_count = 0
        modified_entry_count = 0
        po_key_set: set[KeyTuple] = set(self.get_key_list())
        pot_key_set: set[KeyTuple] = set(pot.get_key_list())

        diff_pot_only_key: set[KeyTuple] = pot_key_set - po_key_set
        diff_po_only_key: set[KeyTuple] = po_key_set - pot_key_set

        # Add new my_entry
        print(f"\npot file only: {len(diff_pot_only_key)}")
        for key in diff_pot_only_key:
            print(f'msgctxt:\t"{key.msgctxt}"\n  msgid:\t"{key.msgid}"\n')

            pot_entry = pot.find_by_key(key.msgctxt, key.msgid)
            if pot_entry:
                self.append(pot_entry)
                new_entry_count += 1

        # Remove obsolete entry
        print(f"\npo file only: {len(diff_po_only_key)}")
        for key in diff_po_only_key:
            print(f'msgctxt:\t"{key.msgctxt}"\n  msgid:\t"{key.msgid}"\n')

            entry = self.find_by_key(key.msgctxt, key.msgid)
            if entry:
                entry.obsolete = True

        # Modified entry
        for my_entry in self:
            if not my_entry.msgctxt.endswith(":"):
                pot_entry = pot.find_by_key(my_entry.msgctxt, "")  # Noneの代わりに空文字を使用

                if pot_entry and (my_entry.msgid != pot_entry.msgid):
                    print(f"msgctxt:\t{my_entry.msgctxt}\n  msgid:\t{my_entry.msgid}\n")
                    my_entry.previous_msgid = my_entry.msgid
                    my_entry.msgid = pot_entry.msgid
                    my_entry.flags = ["fuzzy"]
                    modified_entry_count += 1

        print(f"\n     new entry:\t{new_entry_count}")
        print(f"\nmodified entry:\t{modified_entry_count}")

    def delete_extracted_comments(self) -> None:
        """抽出されたコメントを削除します。

        Note:
            - unknownファイルやmismatchファイルから抽出されたコメントを削除
            - SmartGitの場合、アクティビティログの出力が該当
            - コメントは空文字に置換（polibの仕様に合わせて）
            - 削除されたコメントは復元できません
        """
        for entry in self:
            if entry.comment:
                entry.comment = ""  # polibではNoneではなく空文字を使用

    def find_by_key(self, msgctxt: str, msgid: str) -> Optional[polib.POEntry]:
        """キーに一致するエントリを検索します。

        Args:
            msgctxt: メッセージコンテキスト
            msgid: メッセージID

        Returns:
            一致するエントリ。見つからない場合はNone

        Note:
            - msgctxtが':'で終わる場合、msgctxtとmsgidの組み合わせがキーとなります
            - それ以外の場合、msgctxtのみがキーとなります
        """
        for entry in self:
            # If the msgctxt ends with ':', the combination of msgid and
            # msgctxt becomes the key that identifies the entry.
            # Otherwise, only msgctxt is the key to identify the entry.
            entry_msgctxt = entry.msgctxt or ""
            if entry_msgctxt.endswith(":"):
                if entry_msgctxt == msgctxt and entry.msgid == msgid:
                    return entry
            else:
                if entry_msgctxt == msgctxt:
                    return entry
        return None

    def sort(
        self,
        *,
        key: Optional[Any] = None,
        reverse: bool = False,
    ) -> None:
        """エントリをソートします。

        Args:
            key: ソートキーを生成する関数。指定しない場合はデフォルトのソートキーを使用
            reverse: 逆順にソートする場合はTrue

        Note:
            デフォルトのソートキーは以下の規則に従います：
            - '*'で始まるエントリは先頭に配置
            - その他のエントリは_multi_keys_filterを通して生成されたキーでソート
        """
        if key is None:
            super().sort(
                key=lambda entry: self._po_entry_to_sort_key(entry),
                reverse=reverse,
            )
        else:
            super().sort(key=key, reverse=reverse)

    def format(self):
        """POファイルをフォーマットします。

        以下の処理を行います：
        1. メタデータを定義済みの形式に整理
        2. エントリをソート
        """
        self.metadata = self._filter_po_metadata(self.metadata)
        self.sort()

    def save(
        self,
        fpath: Optional[str] = None,
        repr_method: str = "__unicode__",
        newline: Optional[str] = "\n",
    ) -> None:
        """POファイルを保存します。

        Args:
            fpath: 保存先のパス。指定しない場合は元のパスに保存
            repr_method: エントリの文字列表現を生成するメソッド名
            newline: 改行コード。デフォルトはLF（\n）

        Note:
            polibのデフォルトの改行コードをLFに変更しています。
        """
        # Change the default value of newline to \n (LF).
        super().save(
            fpath=fpath,
            repr_method=repr_method,
            newline=newline,
        )

    def get_key_list(self) -> list[KeyTuple]:
        """全エントリのキーのリストを返します。

        Returns:
            KeyTupleのリスト
        """
        return [self._po_entry_to_key_tuple(entry) for entry in self]

    def check_duplicates(self) -> List[DuplicateEntry]:
        """重複エントリをチェックします。

        Returns:
            重複エントリのリスト

        Note:
            - SmartGitの圧縮表記（括弧内の複数値）を考慮して重複をチェック
            - 重複は以下の条件で判定：
              1. msgctxtが完全一致
              2. 圧縮表記を展開した際のmsgctxtが一致
            - 重複が見つかった場合、DuplicateEntryオブジェクトを返す
        """
        return duplicate_checker.check_msgctxt_duplicates(self)

    def diff(self, other: SGPOFile) -> DiffResult:
        """2つのPOファイル間の差分を比較します。

        Args:
            other: 比較対象のPOファイル

        Returns:
            DiffResult: 差分の結果
                - new_entries: 新規追加されたエントリ（otherにあってselfにないもの）
                - removed_entries: 削除されたエントリ（selfにあってotherにないもの）
                - modified_entries: 変更されたエントリ（msgstrが異なるもの）

        Note:
            - エントリの一致判定は(msgctxt, msgid)の組み合わせで行います
            - msgstrの値のみが異なる場合は変更として扱います
            - 比較は大文字小文字を区別します
        """
        result = DiffResult()
        self_entries = {(entry.msgctxt, entry.msgid): entry for entry in self}
        other_entries = {(entry.msgctxt, entry.msgid): entry for entry in other}

        # 新規エントリの検出
        for key, entry in other_entries.items():
            if key not in self_entries:
                result.new_entries.append(
                    DiffEntry(
                        key=KeyTuple(msgctxt=key[0], msgid=key[1]),
                        status=DiffStatus.NEW,
                        new_value=entry.msgstr if entry else None,
                    )
                )

        # 削除されたエントリの検出
        for key, entry in self_entries.items():
            if key not in other_entries:
                result.removed_entries.append(
                    DiffEntry(
                        key=KeyTuple(msgctxt=key[0], msgid=key[1]),
                        status=DiffStatus.REMOVED,
                        old_value=entry.msgstr if entry else None,
                    )
                )

        # 変更されたエントリの検出
        for key in self_entries.keys() & other_entries.keys():
            self_entry = self_entries[key]
            other_entry = other_entries[key]

            if self_entry and other_entry and self_entry.msgstr != other_entry.msgstr:
                result.modified_entries.append(
                    DiffEntry(
                        key=KeyTuple(msgctxt=key[0], msgid=key[1]),
                        status=DiffStatus.MODIFIED,
                        old_value=self_entry.msgstr,
                        new_value=other_entry.msgstr,
                    )
                )

        return result

    # ======= Private methods =======
    @staticmethod
    def _filter_po_metadata(meta_dict: Dict[str, str]) -> Dict[str, str]:
        """メタデータを定義済みの形式に整理します。

        Args:
            meta_dict: 元のメタデータ辞書

        Returns:
            整理されたメタデータ辞書

        Note:
            - META_DATA_BASE_DICTで定義されたキーのみが保持されます
            - 値が空文字のキーは元のメタデータの値を使用します
        """
        new_meta_dict: Dict[str, str] = {}
        for meta_key, meta_value in SGPOFile.META_DATA_BASE_DICT.items():
            if meta_value == "":
                new_meta_dict[meta_key] = meta_dict.get(meta_key, "")
            else:
                new_meta_dict[meta_key] = meta_value
        return new_meta_dict

    def _po_entry_to_sort_key(self, po_entry: polib.POEntry) -> str:
        """エントリのソートキーを生成します。

        Args:
            po_entry: POエントリ

        Returns:
            ソートキー

        Note:
            - '*'で始まるエントリは先頭に配置されるよう、ASCII 1を先頭に付加
            - その他のエントリは_multi_keys_filterを通してキーを生成
        """
        if po_entry.msgctxt.startswith("*"):
            # Add a character with an ASCII code of 1 at the beginning to make the sort order come first.
            return chr(1) + self._po_entry_to_legacy_key(po_entry)
        else:
            return self._multi_keys_filter(self._po_entry_to_legacy_key(po_entry))

    @staticmethod
    def _po_entry_to_legacy_key(po_entry: polib.POEntry) -> str:
        """レガシー形式のキーを生成します。

        Args:
            po_entry: POエントリ

        Returns:
            レガシー形式のキー

        Note:
            - msgctxtが':'で終わる場合：msgctxt（':'除く）+ '"' + msgid + '"'
            - それ以外の場合：msgctxtをそのまま使用
        """
        if po_entry.msgctxt.endswith(":"):
            return po_entry.msgctxt.rstrip(":") + '"' + po_entry.msgid + '"'
        else:
            return po_entry.msgctxt

    @staticmethod
    def _po_entry_to_key_tuple(po_entry: polib.POEntry) -> KeyTuple:
        """エントリからKeyTupleを生成します。

        Args:
            po_entry: POエントリ

        Returns:
            KeyTuple

        Note:
            - msgctxtが':'で終わる場合：msgctxtとmsgidを使用
            - それ以外の場合：msgctxtと空文字を使用
        """
        msgctxt = po_entry.msgctxt or ""
        if msgctxt.endswith(":"):
            return KeyTuple(msgctxt=msgctxt, msgid=po_entry.msgid)
        else:
            return KeyTuple(msgctxt=msgctxt, msgid="")

    @staticmethod
    def _multi_keys_filter(text: str) -> str:
        """マルチキーエントリのソート用にテキストを変換します。

        Args:
            text: 変換対象のテキスト

        Returns:
            変換後のテキスト

        Note:
            - エスケープされていない括弧内の文字列の前に'ZZZ'を追加
            - これにより、マルチキーエントリがロケールファイル内の適切な位置にグループ化されます
        """
        # Matches everything inside parentheses that are NOT escaped
        pattern = r"(?<!\\\\)\(([^)]+)\)(?!\\\\)"

        # Use re.sub to add 'ZZZ' and remove parentheses from any matched pattern
        modified_text = re.sub(pattern, "ZZZ\\1", text)

        return modified_text

    @staticmethod
    def _validate_filename(filename: str) -> bool:
        """ファイル名が有効かどうかを検証します。

        Args:
            filename: 検証対象のファイル名

        Returns:
            True（有効な場合）

        Raises:
            ValueError: ファイルパスがNoneまたは未対応の形式の場合
            FileNotFoundError: ファイルが存在しない場合

        Note:
            以下のいずれかの形式が有効：
            - .po拡張子
            - .pot拡張子
            - 数字_数字形式
        """
        if not filename:
            raise ValueError("File path cannot be None")

        if not os.path.exists(filename):
            raise FileNotFoundError(f"File not found: {filename}")

        pattern = r".*\d+_\d+$"
        if not (filename.endswith(".po") or filename.endswith("pot") or re.match(pattern, filename)):
            raise ValueError("File type not supported")

        return True
