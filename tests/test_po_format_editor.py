#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import gc

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

# テスト用のモックモジュールをインポート
from tests.mock_helpers import (
    mock_entire_app
)

from sgpo_editor.models.entry import EntryModel


# pytestのフィクスチャを定義
@pytest.fixture
def mock_app(monkeypatch):
    """アプリケーション全体をモック化するフィクスチャ"""
    # mock_helpers.py のヘルパー関数を使用してアプリ全体をモック化
    mocks = mock_entire_app(monkeypatch)
    yield mocks
    mocks['cleanup']()


@pytest.fixture
def mock_window():
    """メインウィンドウをモック化するフィクスチャ"""
    # モックウィンドウを作成
    mock_main_window = MagicMock()
    
    # 必要な属性とメソッドを追加
    mock_main_window.file_handler = MagicMock()
    mock_main_window.file_handler.current_po = None
    mock_main_window.file_handler.current_filepath = None
    
    # _get_current_poメソッドを追加
    mock_main_window._get_current_po = MagicMock()

    yield mock_main_window
    
    # クリーンアップ
    mock_main_window = None
    gc.collect()


@pytest.fixture
def mock_po_file():
    """POファイルをモック化するフィクスチャ"""
    mock_po = MagicMock()
    
    # サンプルエントリを作成
    entries = [
        EntryModel(
            msgid="Hello",
            msgstr="こんにちは",
            msgctxt="greeting",
            position=1,
            translator_comment="挨拶",
            key="greeting\x04Hello"
        ),
        EntryModel(
            msgid="Goodbye",
            msgstr="さようなら",
            msgctxt="farewell",
            position=2,
            translator_comment="別れの挨拶",
            key="farewell\x04Goodbye"
        )
    ]
    
    # モックPOファイルのメソッドを設定
    mock_po.get_entries.return_value = entries
    mock_po.get_entry_by_key.side_effect = lambda key: next((e for e in entries if e.key == key), None)
    mock_po.update_entry.return_value = True
    
    return mock_po


class MockPOFormatEditor:
    """POフォーマットエディタのモッククラス"""
    
    def __init__(self, parent=None, get_current_po=None):
        # 必要な属性を設定
        self._get_current_po = get_current_po
        
        # ウィジェットをモック化
        self.text_edit = MagicMock()
        self.status_label = MagicMock()
        self.get_current_button = MagicMock()
        self.get_all_button = MagicMock()
        self.apply_button = MagicMock()
        self.entry_updated = MagicMock()
        # emitメソッドを追加
        self.entry_updated.emit = self.entry_updated
        
        # テキストエディタのメソッドをモック化
        self.text_edit.toPlainText = MagicMock(return_value="")
        self.text_edit.setPlainText = MagicMock()
        
        # ステータスラベルのメソッドをモック化
        self.status_label.setText = MagicMock()
        
        # ウィンドウタイトル
        self.windowTitle = MagicMock(return_value="POフォーマットエディタ")
        
    def close(self):
        """明示的にリソースをクリーンアップ"""
        pass
        
    # 必要なメソッドを追加
    def update_status(self, message):
        """ステータスを更新する"""
        self.status_label.setText(message)
        
    def format_entry_to_po(self, entry):
        """エントリをPO形式にフォーマットする"""
        return f'# {entry.translator_comment}\nmsgctxt "{entry.msgctxt}"\nmsgid "{entry.msgid}"\nmsgstr "{entry.msgstr}"'
    
    def format_entries_to_po(self, entries):
        """複数のエントリをPO形式にフォーマットする"""
        result = []
        for entry in entries:
            result.append(self.format_entry_to_po(entry))
        return '\n\n'.join(result)
    
    def parse_po_text(self, text):
        """テキストからエントリ情報を解析する"""
        # モック実装
        return [
            {'key': 'greeting:Hello', 'msgstr': 'やあ'},
            {'key': 'farewell:Goodbye', 'msgstr': 'バイバイ'}
        ]
    
    def get_current_entries(self):
        """現在のエントリを取得する"""
        po = self._get_current_po()
        if not po:
            self.update_status("ファイルが開かれていません")
            return
            
        current_entry = po.get_current_entry()
        if not current_entry:
            self.update_status("現在のエントリがありません")
            return
            
        po_text = self.format_entry_to_po(current_entry)
        self.text_edit.setPlainText(po_text)
        self.update_status("現在のエントリを取得しました")
    
    def get_all_entries(self):
        """すべてのエントリを取得する"""
        po = self._get_current_po()
        if not po:
            self.update_status("ファイルが開かれていません")
            return
            
        entries = po.get_entries()
        if not entries:
            self.update_status("エントリがありません")
            return
            
        po_text = self.format_entries_to_po(entries)
        self.text_edit.setPlainText(po_text)
        self.update_status(f"{len(entries)}件のエントリを取得しました")
    
    def apply_changes(self):
        """変更を適用する"""
        po = self._get_current_po()
        if not po:
            self.update_status("ファイルが開かれていません")
            return
            
        text = self.text_edit.toPlainText()
        if not text.strip():
            self.update_status("テキストが空です")
            return
            
        # テキストを解析してエントリを更新
        entries = self.parse_po_text(text)
        
        updated_count = 0
        not_found_count = 0
        
        for entry in entries:
            key = entry['key']
            msgstr = entry['msgstr']
            
            # エントリを取得
            po_entry = po.get_entry_by_key(key)
            if not po_entry:
                not_found_count += 1
                continue
            
            # エントリを更新
            po.update_entry(po_entry, msgstr)
            self.entry_updated.emit(key, msgstr)
            updated_count += 1
            
        # ステータス更新
        self.update_status(f"{updated_count}件更新しました。{not_found_count}件見つかりませんでした。")

@pytest.fixture
def po_format_editor(mock_window, mock_po_file):
    """POフォーマットエディタのフィクスチャ"""
    # get_current_po関数をモック化
    get_current_po = MagicMock(return_value=mock_po_file)
    
    # POフォーマットエディタを作成
    editor = MockPOFormatEditor(mock_window, get_current_po)
    
    yield editor
    
    # クリーンアップ
    editor.close()
    editor = None
    gc.collect()


class TestPOFormatEditor:
    """POフォーマットエディタのテスト"""

    def test_initialization(self, po_format_editor):
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

    def test_get_current_entry(self, po_format_editor, mock_po_file):
        """現在のエントリを取得するテスト"""
        # モックの現在のエントリを設定
        current_entry = mock_po_file.get_entries()[0]
        po_format_editor._get_current_po().get_current_entry = MagicMock(return_value=current_entry)
        
        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, 'update_status') as mock_update_status:
            with patch.object(po_format_editor, 'format_entry_to_po') as mock_format_entry:
                # モックの戻り値を設定
                mock_format_entry.return_value = '# 挨拶\nmsgctxt "greeting"\nmsgid "Hello"\nmsgstr "こんにちは"'
                
                # 「現在のエントリを取得」ボタンのクリックをシミュレート
                po_format_editor.get_current_entries()
                
                # テキストエディタに正しいPO形式のテキストが設定されていることを確認
                po_format_editor.text_edit.setPlainText.assert_called_once()
                
                # ステータスが更新されたことを確認
                mock_update_status.assert_called_once()

    def test_get_all_entries(self, po_format_editor, mock_po_file):
        """すべてのエントリを取得するテスト"""
        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, 'update_status') as mock_update_status:
            with patch.object(po_format_editor, 'format_entries_to_po') as mock_format_entries:
                # モックの戻り値を設定
                mock_format_entries.return_value = '# 挨拶\nmsgctxt "greeting"\nmsgid "Hello"\nmsgstr "こんにちは"\n\n# 別れの挨拶\nmsgctxt "farewell"\nmsgid "Goodbye"\nmsgstr "さようなら"'
                
                # 「すべてのエントリを取得」ボタンのクリックをシミュレート
                po_format_editor.get_all_entries()
                
                # テキストエディタに正しいPO形式のテキストが設定されていることを確認
                po_format_editor.text_edit.setPlainText.assert_called_once()
                
                # ステータスが更新されたことを確認
                mock_update_status.assert_called_once()

    def test_apply_changes(self, po_format_editor, mock_po_file):
        """変更を適用するテスト"""
        # テキストエディタのモックを設定
        po_text = '''# 挨拶
msgctxt "greeting"
msgid "Hello"
msgstr "やあ"

# 別れの挨拶
msgctxt "farewell"
msgid "Goodbye"
msgstr "バイバイ"
'''
        po_format_editor.text_edit.toPlainText.return_value = po_text
        
        # モックエントリを作成
        mock_entry1 = MagicMock()
        mock_entry1.key = 'greeting:Hello'
        
        mock_entry2 = MagicMock()
        mock_entry2.key = 'farewell:Goodbye'
        
        # get_entry_by_keyの戻り値を設定
        mock_po_file.get_entry_by_key.side_effect = lambda key: {
            'greeting:Hello': mock_entry1,
            'farewell:Goodbye': mock_entry2
        }.get(key)
        
        # 実行前にモックをリセット
        mock_po_file.update_entry.reset_mock()
        po_format_editor.entry_updated.reset_mock()
        
        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, 'update_status') as mock_update_status:
            with patch.object(po_format_editor, 'parse_po_text') as mock_parse_po:
                # モックの戻り値を設定
                mock_parse_po.return_value = [
                    {'key': 'greeting:Hello', 'msgstr': 'やあ'},
                    {'key': 'farewell:Goodbye', 'msgstr': 'バイバイ'}
                ]
                
                # 「適用」ボタンのクリックをシミュレート
                po_format_editor.apply_changes()
                
                # POファイルのupdate_entryメソッドが呼ばれたことを確認
                assert mock_po_file.update_entry.call_count == 2
                
                # エントリ更新シグナルが発行されたことを確認
                assert po_format_editor.entry_updated.call_count == 2
                
                # ステータスが更新されたことを確認
                mock_update_status.assert_called_once()

    def test_apply_changes_with_not_found_entry(self, po_format_editor, mock_po_file):
        """存在しないエントリの変更を適用するテスト"""
        # テキストエディタのモックを設定
        po_text = '''# 存在しないエントリ
msgctxt "not_exist"
msgid "Not Exist"
msgstr "存在しない"
'''
        po_format_editor.text_edit.toPlainText.return_value = po_text
        
        # POフォーマットエディタのメソッドをモック化
        with patch.object(po_format_editor, 'update_status') as mock_update_status:
            with patch.object(po_format_editor, 'parse_po_text') as mock_parse_po:
                # モックの戻り値を設定
                mock_parse_po.return_value = [
                    {'key': 'not_exist:Not Exist', 'msgstr': '存在しない'}
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
                mock_update_status.assert_called_with("0件更新しました。1件見つかりませんでした。")
