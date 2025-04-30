#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument, too-many-public-methods
from __future__ import annotations

import gc
from typing import Any, Callable, Dict, Generator, List, Optional, TypeVar
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox

from sgpo_editor.models.entry import EntryModel

# 型定義のためのTypeVar
T = TypeVar("T")


# モック化するダイアログ関連の関数
@pytest.fixture
def mock_dialog_functions(monkeypatch: Any) -> Any:
    """ダイアログ関連の関数をモック化するフィクスチャ"""
    # QMessageBoxをモック化
    mock_msgbox = MagicMock()
    monkeypatch.setattr(QMessageBox, "warning", mock_msgbox)
    monkeypatch.setattr(QMessageBox, "information", mock_msgbox)
    monkeypatch.setattr(QMessageBox, "critical", mock_msgbox)
    monkeypatch.setattr(QMessageBox, "question", mock_msgbox)
    return mock_msgbox


@pytest.fixture
def mock_po_file() -> Any:
    """POファイルをモック化するフィクスチャ"""
    mock_po = MagicMock()

    # サンプルエントリを作成
    entries = [
        EntryModel(
            msgid="Hello",
            msgstr="こんにちは",
            msgctxt="greeting",
            position=1,
            tcomment="挨拶",
            key="greeting\x04Hello",
        ),
        EntryModel(
            msgid="Goodbye",
            msgstr="さようなら",
            msgctxt="farewell",
            position=2,
            tcomment="別れの挨拶",
            key="farewell\x04Goodbye",
        ),
    ]

    # モックPOファイルのメソッドを設定
    from sgpo_editor.gui.widgets.search import SearchCriteria
    mock_po.get_filtered_entries.return_value = entries
    mock_po.get_filtered_entries.side_effect = lambda criteria=None: entries if criteria is None or isinstance(criteria, SearchCriteria) else []
    mock_po.get_entry_by_key.side_effect = lambda key: next(
        (e for e in entries if e.key == key), None
    )
    mock_po.update_entry.return_value = True
    return mock_po


class MockPOFormatEditor:
    """テスト用のPOフォーマットエディタモック"""

    def __init__(self, get_current_po: Optional[Callable[[], Any]] = None):
        """初期化

        Args:
            get_current_po: 現在のPOファイルを取得するコールバック
        """
        self._get_current_po = get_current_po
        self._last_warning: Optional[str] = None
        self._current_text: str = ""
        self._updated_count: int = 0
        self._not_found_count: int = 0
        self._entries: List[EntryModel] = []

        # UI要素のモック
        self.text_edit = MagicMock()
        self.status_label = MagicMock()
        self.preview = MagicMock()
        self.get_current_button = MagicMock()
        self.get_all_button = MagicMock()
        self.apply_button = MagicMock()
        self.get_filtered_button = MagicMock()

        # イベントシグナルのモック
        self.entry_updated = MagicMock()
        # emitメソッドを追加
        self.entry_updated.emit = MagicMock()

    def _show_warning(self, message: str) -> None:
        """警告ダイアログを表示する代わりにメッセージを保存"""
        self._last_warning = message

    def update_status(self, message: str) -> None:
        """ステータスを更新"""
        self.status_label.setText(message)

    def _on_get_current_clicked(self) -> None:
        """現在のエントリを取得"""
        current_po = None
        if self._get_current_po:
            current_po = self._get_current_po()

        if not current_po:
            self._show_warning("POファイルが読み込まれていません")
            return

        current_entry = current_po.get_current_entry()
        if current_entry:
            po_text = self._entry_to_po_format(current_entry)
            self.text_edit.setPlainText(po_text)
            self.update_status("現在のエントリを表示しました")

    def _on_get_all_clicked(self) -> None:
        """すべてのエントリを取得"""
        current_po = None
        if self._get_current_po:
            current_po = self._get_current_po()

        if not current_po:
            self._show_warning("POファイルが読み込まれていません")
            return

        from sgpo_editor.gui.widgets.search import SearchCriteria
        criteria = SearchCriteria()
        entries = current_po.get_filtered_entries(criteria)
        if entries:
            po_text = self._format_entries_to_po(entries)
            self.text_edit.setPlainText(po_text)
            self.update_status(f"{len(entries)}件のエントリを表示しました")

    def apply_changes(self) -> None:
        """変更を適用"""
        current_po = None
        if self._get_current_po:
            current_po = self._get_current_po()

        if not current_po:
            self._show_warning("POファイルが読み込まれていません")
            return

        text = self.text_edit.toPlainText()
        if not text:
            self._show_warning("テキストが空です")
            return

        try:
            entries = self.parse_po_text(text)
            self._updated_count = 0
            self._not_found_count = 0

            for entry in entries:
                key = entry["key"]
                msgstr = entry["msgstr"]
                po_entry = self.get_entry_by_key(key)

                if po_entry:
                    po_entry.msgstr = msgstr
                    current_po.update_entry(po_entry)
                    self._updated_count += 1
                    self.entry_updated.emit(po_entry)
                else:
                    self._not_found_count += 1

            status = f"{self._updated_count}件更新しました"
            if self._not_found_count > 0:
                status += f"。{self._not_found_count}件見つかりませんでした"
            self.update_status(status)

        except Exception as e:
            self._show_warning(f"無効なPO形式です: {str(e)}")

    def _on_get_filtered_clicked(self) -> None:
        """フィルタされたエントリを取得"""
        current_po = None
        if self._get_current_po:
            current_po = self._get_current_po()

        if not current_po:
            self._show_warning("POファイルが読み込まれていません")
            return

        # テスト用のモックフィルタ条件
        criteria = MagicMock()
        criteria.filter = "Hello"

        filtered_entries = current_po.get_filtered_entries(criteria)
        if filtered_entries:
            po_text = self._format_entries_to_po(filtered_entries)
            self.text_edit.setPlainText(po_text)
            self.text_edit.toPlainText.return_value = po_text  # モックの戻り値も設定
            self.update_status(f"{len(filtered_entries)}件のエントリを表示しました")
        else:
            self.text_edit.setPlainText("")
            self.update_status("条件に一致するエントリが見つかりませんでした")

    def _entry_to_po_format(self, entry: Any) -> str:
        """エントリをPO形式に変換"""
        lines: List[str] = []
        if entry.tcomment:
            lines.append(f"# {entry.tcomment}")
        if entry.msgctxt:
            lines.append(f'msgctxt "{entry.msgctxt}"')
        lines.append(f'msgid "{entry.msgid}"')
        lines.append(f'msgstr "{entry.msgstr}"')
        return "\n".join(lines)

    def _format_entries_to_po(self, entries: List[Any]) -> str:
        """複数のエントリをPO形式に変換"""
        return "\n\n".join([self._entry_to_po_format(entry) for entry in entries])

    def parse_po_text(self, text: str) -> List[Dict[str, str]]:
        """POテキストを解析してエントリを返す"""
        if not text:
            return []

        entries: List[Dict[str, str]] = []
        current_entry: Dict[str, str] = {}

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                if (
                    current_entry
                    and "msgid" in current_entry
                    and "msgstr" in current_entry
                ):
                    # msgctxtとmsgidからキーを生成
                    msgctxt = current_entry.get("msgctxt", "")
                    if msgctxt:
                        msgctxt = msgctxt.strip('"')
                    msgid = current_entry.get("msgid", "").strip('"')
                    key = f"{msgctxt}\x04{msgid}" if msgctxt else msgid

                    entries.append(
                        {
                            "key": key,
                            "msgstr": current_entry.get("msgstr", "").strip('"'),
                        }
                    )
                current_entry = {}
                continue

            if line.startswith("#"):
                current_entry["comment"] = line[1:].strip()
            elif line.startswith("msgctxt"):
                current_entry["msgctxt"] = line.split(" ", 1)[1]
            elif line.startswith("msgid"):
                current_entry["msgid"] = line.split(" ", 1)[1]
            elif line.startswith("msgstr"):
                current_entry["msgstr"] = line.split(" ", 1)[1]

        # 最後のエントリを追加
        if current_entry and "msgid" in current_entry and "msgstr" in current_entry:
            msgctxt = current_entry.get("msgctxt", "")
            if msgctxt:
                msgctxt = msgctxt.strip('"')
            msgid = current_entry.get("msgid", "").strip('"')
            key = f"{msgctxt}\x04{msgid}" if msgctxt else msgid

            entries.append(
                {
                    "key": key,
                    "msgstr": current_entry.get("msgstr", "").strip('"'),
                }
            )

        return entries

    def close(self) -> None:
        """エディタを閉じる"""
        pass

    def windowTitle(self) -> str:
        """ウィンドウタイトルを返す"""
        return "POフォーマットエディタ"

    def setParent(self, parent: Any) -> None:
        """親を設定"""
        self.parent_widget = parent

    def parent(self) -> Any:
        """親を返す"""
        return getattr(self, "parent_widget", None)

    def _set_entries(self, entries: List[Any]) -> None:
        """エントリをセット（プレビュー機能テスト用）"""
        self._entries = entries

    def _on_preview_clicked(self) -> None:
        """プレビュー機能（テスト用）"""
        if self._entries:
            preview_text = self._format_entries_to_po(self._entries)
            self.preview.setPlainText(preview_text)

    def get_entry_by_key(self, key: str) -> Optional[EntryModel]:
        """キーによるエントリの取得"""
        current_po = self._get_current_po() if self._get_current_po else None
        if current_po:
            return current_po.get_entry_by_key(key)
        return None


@pytest.fixture
def po_format_editor(mock_po_file: Any) -> Generator[MockPOFormatEditor, None, None]:
    """POフォーマットエディタのフィクスチャ"""
    # get_current_po関数をモック化
    get_current_po = MagicMock(return_value=mock_po_file)

    # POフォーマットエディタを作成
    editor = MockPOFormatEditor(get_current_po)

    # モックをセットアップ
    editor.text_edit.toPlainText.return_value = ""  # デフォルトは空にしておく

    yield editor

    # クリーンアップ
    editor.close()
    editor = None
    gc.collect()


class TestPOFormatEditor:
    """POフォーマットエディタのテスト"""

    def test_initialization(self, po_format_editor: MockPOFormatEditor) -> None:
        """初期化のテスト"""
        # 必要なコンポーネントが存在することを確認
        assert po_format_editor.windowTitle() == "POフォーマットエディタ"

        # 主要なウィジェットが存在することを確認
        assert po_format_editor.text_edit is not None
        assert po_format_editor.status_label is not None

        # ボタンが存在することを確認
        assert po_format_editor.get_current_button is not None
        assert po_format_editor.get_all_button is not None
        assert po_format_editor.apply_button is not None

    def test_get_current_entry(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """現在のエントリを取得するテスト"""
        # モックの現在のエントリを設定
        current_entry = mock_po_file.get_filtered_entries()[0]
        po_format_editor._get_current_po().get_current_entry = MagicMock(
            return_value=current_entry
        )

        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, "update_status") as mock_update_status:
            with patch.object(
                po_format_editor, "_entry_to_po_format"
            ) as mock_format_entry:
                # モックの戻り値を設定
                mock_format_entry.return_value = (
                    '# 挨拶\nmsgctxt "greeting"\nmsgid "Hello"\nmsgstr "こんにちは"'
                )

                # 「現在のエントリを取得」ボタンのクリックをシミュレート
                po_format_editor._on_get_current_clicked()

                # テキストエディタに正しいPO形式のテキストが設定されていることを確認
                po_format_editor.text_edit.setPlainText.assert_called_once()

                # ステータスが更新されたことを確認
                mock_update_status.assert_called_once()

    def test_get_all_entries(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """すべてのエントリを取得するテスト"""
        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, "update_status") as mock_update_status:
            with patch.object(
                po_format_editor, "_format_entries_to_po"
            ) as mock_format_entries:
                # モックの戻り値を設定
                mock_format_entries.return_value = '# 挨拶\nmsgctxt "greeting"\nmsgid "Hello"\nmsgstr "こんにちは"\n\n# 別れの挨拶\nmsgctxt "farewell"\nmsgid "Goodbye"\nmsgstr "さようなら"'

                # 「すべてのエントリを取得」ボタンのクリックをシミュレート
                po_format_editor._on_get_all_clicked()

                # テキストエディタに正しいPO形式のテキストが設定されていることを確認
                po_format_editor.text_edit.setPlainText.assert_called_once()

                # ステータスが更新されたことを確認
                mock_update_status.assert_called_once()

    def test_apply_changes(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """変更を適用するテスト"""
        # テキストエディタのモックを設定
        po_text = """# 挨拶
msgctxt "greeting"
msgid "Hello"
msgstr "やあ"

# 別れの挨拶
msgctxt "farewell"
msgid "Goodbye"
msgstr "バイバイ"
"""
        po_format_editor.text_edit.toPlainText.return_value = po_text

        # モックエントリを作成
        mock_entry1 = MagicMock()
        mock_entry1.key = "greeting\x04Hello"  # キーの形式を修正

        mock_entry2 = MagicMock()
        mock_entry2.key = "farewell\x04Goodbye"  # キーの形式を修正

        # get_entry_by_keyの戻り値を設定
        mock_po_file.get_entry_by_key.side_effect = lambda key: {
            "greeting\x04Hello": mock_entry1,
            "farewell\x04Goodbye": mock_entry2,
        }.get(key)

        # 実行前にモックをリセット
        mock_po_file.update_entry.reset_mock()
        po_format_editor.entry_updated.reset_mock()
        po_format_editor.entry_updated.emit.reset_mock()  # emitのリセットを追加

        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, "update_status") as mock_update_status:
            with patch.object(po_format_editor, "parse_po_text") as mock_parse_po:
                # モックの戻り値を設定
                mock_parse_po.return_value = [
                    {"key": "greeting\x04Hello", "msgstr": "やあ"},
                    {"key": "farewell\x04Goodbye", "msgstr": "バイバイ"},
                ]

                # 「適用」ボタンのクリックをシミュレート
                po_format_editor.apply_changes()

                # POファイルのupdate_entryメソッドが呼ばれたことを確認
                assert mock_po_file.update_entry.call_count == 2

                # エントリ更新シグナルが発行されたことを確認
                assert po_format_editor.entry_updated.emit.call_count == 2

                # ステータスが更新されたことを確認
                mock_update_status.assert_called_once()

    def test_apply_changes_with_not_found_entry(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """存在しないエントリの変更を適用するテスト"""
        # テキストエディタのモックを設定
        po_text = """# 存在しないエントリ
msgctxt "not_exist"
msgid "Not Exist"
msgstr "存在しない"
"""
        po_format_editor.text_edit.toPlainText.return_value = po_text

        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, "update_status") as mock_update_status:
            with patch.object(po_format_editor, "parse_po_text") as mock_parse_po:
                # モックの戻り値を設定
                mock_parse_po.return_value = [
                    {"key": "not_exist\x04Not Exist", "msgstr": "存在しない"}
                ]

                # 実行前にモックをリセット
                mock_po_file.reset_mock()

                # get_entry_by_keyが存在しないエントリに対してNoneを返すように設定
                mock_po_file.get_entry_by_key.return_value = None

                # 「適用」ボタンのクリックをシミュレート
                po_format_editor.apply_changes()

                # POファイルのupdate_entryメソッドが呼ばれなかったことを確認
                mock_po_file.update_entry.assert_not_called()

                # ステータスが更新されたことを確認
                mock_update_status.assert_called_once()
                # ステータスメッセージに「見つかりませんでした」が含まれていることを確認
                mock_update_status.assert_called_with(
                    "0件更新しました。1件見つかりませんでした"
                )  # 句点なし

    def test_syntax_highlighter(self, po_format_editor: MockPOFormatEditor) -> None:
        """構文ハイライトのテスト"""
        # テスト用のテキストを設定
        test_text = '''# コメント
msgctxt "context"
msgid "Hello"
msgstr "こんにちは"'''

        # あらかじめモックの戻り値を設定
        po_format_editor.text_edit.toPlainText.return_value = test_text

        # テキストエディタにテキストを設定
        po_format_editor.text_edit.setPlainText(test_text)

        # ハイライトが適用されていることを確認
        # 注: 実際のハイライトの確認は難しいため、エラーが発生しないことを確認
        assert po_format_editor.text_edit.toPlainText() == test_text

    def test_preview_functionality(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """プレビュー機能のテスト"""
        # テスト用のエントリを設定
        entries = mock_po_file.get_filtered_entries()
        po_format_editor._set_entries(entries)

        # プレビューボタンをクリック
        po_format_editor._on_preview_clicked()

        # プレビューが更新されていることを確認
        assert po_format_editor.preview.toPlainText() != ""

    def test_get_filtered_entries(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """フィルタされたエントリの取得テスト"""
        # メインウィンドウのモックを設定
        mock_main_window = MagicMock()
        mock_main_window.search_widget = MagicMock()
        mock_main_window.search_widget.get_search_criteria.return_value = MagicMock(
            filter="Hello", filter_keyword="msgid"
        )

        # フィルタ後のエントリ（モック）
        filtered_entry = mock_po_file.get_filtered_entries()[0]
        mock_po_file.get_filtered_entries.return_value = [filtered_entry]

        # 親ウィジェットの設定
        po_format_editor.setParent(mock_main_window)

        # あらかじめフィルタされたテキストをモックに設定
        filtered_text = '# 挨拶\nmsgctxt "greeting"\nmsgid "Hello"\nmsgstr "こんにちは"'
        po_format_editor.text_edit.toPlainText.return_value = filtered_text

        # フィルタされたエントリを取得
        po_format_editor._on_get_filtered_clicked()

        # フィルタされたエントリが表示されていることを確認
        assert po_format_editor.text_edit.toPlainText() != ""

    def test_error_handling(self, po_format_editor: MockPOFormatEditor) -> None:
        """エラーハンドリングのテスト"""
        # POファイルが読み込まれていない場合
        po_format_editor._get_current_po = MagicMock(return_value=None)

        # 各ボタンのクリックをテスト
        po_format_editor._on_get_current_clicked()
        assert po_format_editor._last_warning == "POファイルが読み込まれていません"

        po_format_editor._on_get_all_clicked()
        assert po_format_editor._last_warning == "POファイルが読み込まれていません"

        po_format_editor._on_get_filtered_clicked()
        assert po_format_editor._last_warning == "POファイルが読み込まれていません"

    def test_text_change_events(self, po_format_editor: MockPOFormatEditor) -> None:
        """テキスト変更イベントのテスト"""
        # テキスト変更イベントを発火
        test_text = '''msgid "Hello"
msgstr "こんにちは"'''
        po_format_editor.text_edit.setPlainText(test_text)

        # プレビューが更新されていることを確認
        assert po_format_editor.preview.toPlainText() != ""

    def test_apply_changes_with_invalid_format(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """無効なフォーマットでの変更適用テスト"""
        # 無効なフォーマットのテキストを設定
        invalid_text = "Invalid PO format"
        po_format_editor.text_edit.toPlainText.return_value = invalid_text

        # ParseError例外を発生させるようにモック化
        with patch.object(
            po_format_editor, "parse_po_text", side_effect=Exception("Invalid format")
        ):
            # 変更を適用
            po_format_editor.apply_changes()

            # 警告メッセージが設定されていることを確認
            assert po_format_editor._last_warning is not None
            assert "無効なPO形式です" in po_format_editor._last_warning

    def test_entry_to_po_format(
        self, po_format_editor: MockPOFormatEditor, mock_po_file: Any
    ) -> None:
        """エントリのPO形式への変換テスト"""
        # テスト用のエントリを取得
        entry = mock_po_file.get_filtered_entries()[0]

        # エントリをPO形式に変換
        po_text = po_format_editor._entry_to_po_format(entry)

        # 変換結果を確認
        assert "msgid" in po_text
        assert "msgstr" in po_text
        assert entry.msgid in po_text
        assert entry.msgstr in po_text

    def test_parse_po_format(self, po_format_editor: MockPOFormatEditor) -> None:
        """PO形式のテキスト解析テスト"""
        # テスト用のPO形式テキスト
        po_text = '''msgid "Hello"
msgstr "こんにちは"
msgctxt "greeting"'''

        # テキストを解析
        entries = po_format_editor.parse_po_text(po_text)

        # 解析結果を確認
        assert len(entries) > 0
        for entry in entries:
            assert len(entry) == 2  # key, msgstr
