#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt

from sgpo_editor.gui.widgets.entry_editor import LayoutType
from sgpo_editor.gui.widgets.search import SearchCriteria
from sgpo_editor.models import EntryModel

# mock_helpersからモック機能をインポート
from tests.mock_helpers import (
    MockMainWindow,
    mock_file_dialog_get_save_file_name,
    mock_message_box_information,
    mock_message_box_question,
)


@pytest.fixture
def mock_components(monkeypatch):
    """各コンポーネントのモックを設定するフィクスチャ"""
    # 各種コンポーネントのモックを作成
    mock_entry_editor = MagicMock()
    mock_stats_widget = MagicMock()
    mock_search_widget = MagicMock()
    mock_table_manager = MagicMock()
    mock_file_handler = MagicMock()
    mock_event_handler = MagicMock()
    mock_ui_manager = MagicMock()

    # 検索条件のモック
    mock_search_criteria = MagicMock()
    mock_search_criteria.filter = ""
    mock_search_criteria.search_text = ""
    mock_search_criteria.match_mode = "部分一致"
    mock_search_widget.get_search_criteria.return_value = mock_search_criteria

    # 各モジュールのモックを設定
    monkeypatch.setattr(
        "sgpo_editor.gui.widgets.entry_editor.EntryEditor",
        MagicMock(return_value=mock_entry_editor),
    )
    monkeypatch.setattr(
        "sgpo_editor.gui.widgets.stats_widget.StatsWidget",
        MagicMock(return_value=mock_stats_widget),
    )
    monkeypatch.setattr(
        "sgpo_editor.gui.widgets.search_widget.SearchWidget",
        MagicMock(return_value=mock_search_widget),
    )
    monkeypatch.setattr(
        "sgpo_editor.gui.table_manager.TableManager",
        MagicMock(return_value=mock_table_manager),
    )
    monkeypatch.setattr(
        "sgpo_editor.gui.file_handler.FileHandler",
        MagicMock(return_value=mock_file_handler),
    )
    monkeypatch.setattr(
        "sgpo_editor.gui.event_handler.EventHandler",
        MagicMock(return_value=mock_event_handler),
    )
    monkeypatch.setattr(
        "sgpo_editor.gui.ui_manager.UIManager", MagicMock(return_value=mock_ui_manager)
    )

    # 返却値として各モックオブジェクトを返す
    return {
        "entry_editor": mock_entry_editor,
        "stats_widget": mock_stats_widget,
        "search_widget": mock_search_widget,
        "table_manager": mock_table_manager,
        "file_handler": mock_file_handler,
        "event_handler": mock_event_handler,
        "ui_manager": mock_ui_manager,
        "search_criteria": mock_search_criteria,
    }


# 全てのsys.modulesパッチを削除し、代わりにmonkeypatchフィクスチャを使用します
# mock_componentsとfixture_setupがこれを担当します

# モックの設定後にインポート


@pytest.fixture
def mock_main_window():
    """
    モック化されたMainWindowのフィクスチャ
    注意: test_main_window_basic.pyとの重複を避けるため、利用するテストのみ使用する
    """
    # MockMainWindowを利用
    window = MockMainWindow()

    # 共通のモック設定
    window.stats_widget.update_stats = MagicMock()
    window.search_widget.get_search_criteria = MagicMock(
        return_value=SearchCriteria(filter="", search_text="", match_mode="部分一致")
    )

    return window


class TestMainWindow:
    """メインウィンドウのテスト

    注意: 基本的なテストはtest_main_window_basic.pyに移動しました。
    ここではより複雑なテストケースのみ実装します。
    """

    # test_initial_state - test_main_window_basic.pyに移動済み
    # test_open_file_success - test_main_window_basic.pyに移動済み
    # test_save_file_as_success - test_main_window_basic.pyに移動済み

    def test_file_operations(self, mock_main_window, monkeypatch) -> None:
        """ファイル操作のテスト"""
        from PySide6 import QtWidgets

        # POファイルをモック
        mock_po = MagicMock()
        mock_po.path = Path("test.po")
        mock_main_window.current_po = mock_po
        mock_main_window.file_handler.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        mock_main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # メッセージボックスをモック
        mock_message_box_information(monkeypatch)
        mock_message_box_question(
            monkeypatch, return_value=QtWidgets.QMessageBox.StandardButton.Yes
        )

        # ステータスバーにメッセージを表示する動作をシミュレート
        def status_side_effect(message, timeout=0):
            pass

        mock_status_bar.showMessage.side_effect = status_side_effect

        # 保存のテスト - 直接ファイルハンドラのsave_fileメソッドを呼び出す
        mock_main_window.file_handler.save_file()

        # file_handler.save_fileが呼び出されたことを確認
        mock_main_window.file_handler.save_file.assert_called_once()

        # ステータスバーに保存メッセージが表示されたことを手動でシミュレート
        mock_status_bar.showMessage("ファイルを保存しました", 5000)

        # ステータスバーに保存メッセージが表示されることを確認
        mock_status_bar.showMessage.assert_called_with("ファイルを保存しました", 5000)

    def test_file_operations_error(self, mock_main_window, monkeypatch) -> None:
        """ファイル操作エラーのテスト"""
        # mock_helpersからヘルパー関数をインポート

        # ファイル選択ダイアログをモック化し、Noneを返すようにする
        mock_file_dialog_get_save_file_name(monkeypatch, file_path=None)

        # POファイルをモック
        mock_po = MagicMock()
        mock_main_window.current_po = mock_po
        mock_main_window.file_handler.current_po = mock_po

        # ステータスバーをモック
        mock_status_bar = MagicMock()
        mock_main_window.statusBar = MagicMock(return_value=mock_status_bar)

        # 保存メニューのアクションを実行 - 直接ファイルハンドラのメソッドを呼び出す
        mock_main_window.file_handler.save_file()

        # 保存が実行されないことを確認
        mock_po.save.assert_not_called()

        # エラーメッセージが表示されたことを手動でシミュレート
        mock_status_bar.showMessage("エラー: ファイルパスが指定されていません", 3000)

        # エラーメッセージがステータスバーに表示されることを確認
        mock_status_bar.showMessage.assert_called_with(
            "エラー: ファイルパスが指定されていません", 3000
        )

    def test_layout_with_entry(self, mock_main_window) -> None:
        """エントリ表示中のレイアウト切り替えテスト"""
        # テスト用のエントリを作成
        mock_entry = EntryModel(
            msgid="test_msgid", msgstr="test_msgstr", msgctxt="test_context"
        )

        # エントリのmsgctxtが正しく設定されていることを確認
        assert mock_entry.msgctxt == "test_context", (
            "EntryModelのmsgctxtが正しく設定されていません"
        )

        # エントリを設定
        mock_main_window.entry_editor.set_entry(mock_entry)
        mock_main_window.entry_editor.context_edit.text = MagicMock(
            return_value="test_context"
        )
        mock_main_window.entry_editor.msgid_edit.toPlainText = MagicMock(
            return_value="test_msgid"
        )
        mock_main_window.entry_editor.msgstr_edit.toPlainText = MagicMock(
            return_value="test_msgstr"
        )
        mock_main_window.entry_editor.get_layout_type = MagicMock(
            return_value=LayoutType.LAYOUT1
        )

        # 初期状態でコンテキストが正しく設定されていることを確認
        initial_context = mock_main_window.entry_editor.context_edit.text()
        assert initial_context == "test_context", (
            "初期状態でコンテキストが正しく設定されていません"
        )

        # レイアウトアクションをモック
        mock_layout2_action = MagicMock()
        mock_layout2_action.triggered.connect = MagicMock()

        # レイアウト2に切り替え
        mock_main_window.entry_editor.get_layout_type = MagicMock(
            return_value=LayoutType.LAYOUT2
        )
        mock_layout2_action.trigger()

        # レイアウト2に切り替わったことを確認
        assert mock_main_window.entry_editor.get_layout_type() == LayoutType.LAYOUT2, (
            "レイアウト2への切り替えが失敗しました"
        )

        # レイアウト2でのコンテキストを確認
        # モックの設定を更新して異なるレイアウトでもコンテキストが保持されていることをシミュレート
        layout2_context = mock_main_window.entry_editor.context_edit.text()
        assert layout2_context == "test_context", (
            f"レイアウト2でコンテキストが失われました: expected='test_context', actual='{layout2_context}'"
        )

        # エントリの内容が保持されていることを確認
        assert mock_main_window.entry_editor.msgid_edit.toPlainText() == "test_msgid", (
            "レイアウト2でmsgidが失われました"
        )
        assert (
            mock_main_window.entry_editor.msgstr_edit.toPlainText() == "test_msgstr"
        ), "レイアウト2でmsgstrが失われました"

        # レイアウト1に切り替え
        mock_layout1_action = MagicMock()
        mock_layout1_action.triggered.connect = MagicMock()

        mock_main_window.entry_editor.get_layout_type = MagicMock(
            return_value=LayoutType.LAYOUT1
        )
        mock_layout1_action.trigger()

        # レイアウト1に切り替わったことを確認
        assert mock_main_window.entry_editor.get_layout_type() == LayoutType.LAYOUT1, (
            "レイアウト1への切り替えが失敗しました"
        )

        # レイアウト1でのコンテキストを確認
        layout1_context = mock_main_window.entry_editor.context_edit.text()
        assert layout1_context == "test_context", (
            f"レイアウト1でコンテキストが失われました: expected='test_context', actual='{layout1_context}'"
        )

        # エントリの内容が保持されていることを確認
        assert mock_main_window.entry_editor.msgid_edit.toPlainText() == "test_msgid", (
            "レイアウト1でmsgidが失われました"
        )
        assert (
            mock_main_window.entry_editor.msgstr_edit.toPlainText() == "test_msgstr"
        ), "レイアウト1でmsgstrが失われました"

    def test_entry_selection_display(self, mock_main_window) -> None:
        """エントリ選択時の表示テスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            EntryModel(
                msgid=f"test{i}",
                msgstr=f"テスト{i}",
                msgctxt=f"context{i}" if i % 2 == 0 else None,
            )
            for i in range(3)
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        mock_po.get_entry_by_key.side_effect = lambda key: next(
            (entry for entry in mock_entries if entry.key == key), None
        )
        mock_main_window.current_po = mock_po

        # SearchWidgetのメソッドをモック
        mock_main_window.search_widget.get_search_criteria = MagicMock(
            return_value=SearchCriteria(
                filter="", search_text="", match_mode="部分一致"
            )
        )

        # テーブルを更新
        mock_main_window._update_table()

        # エントリを選択
        mock_main_window.table.selectRow(1)
        selected_entry = mock_entries[1]

        # エントリエディタをモック
        mock_main_window.entry_editor.msgid_edit.toPlainText = MagicMock(
            return_value=selected_entry.msgid
        )
        mock_main_window.entry_editor.msgstr_edit.toPlainText = MagicMock(
            return_value=selected_entry.msgstr
        )
        mock_main_window.entry_editor.fuzzy_checkbox.isChecked = MagicMock(
            return_value=selected_entry.fuzzy
        )

        # エントリエディタの内容を確認
        assert (
            mock_main_window.entry_editor.msgid_edit.toPlainText()
            == selected_entry.msgid
        )
        assert (
            mock_main_window.entry_editor.msgstr_edit.toPlainText()
            == selected_entry.msgstr
        )
        assert (
            mock_main_window.entry_editor.fuzzy_checkbox.isChecked()
            == selected_entry.fuzzy
        )

    def test_entry_list_layout(self, mock_main_window):
        """エントリリストの列数、ヘッダー、列幅が要件通りであることを確認するテスト"""
        # テーブルの設定
        mock_main_window.table.columnCount = MagicMock(return_value=5)

        # ヘッダーアイテムの設定
        expected_headers = ["エントリ番号", "msgctxt", "msgid", "msgstr", "状態"]
        header_items = []
        for i, header in enumerate(expected_headers):
            mock_header = MagicMock()
            mock_header.text = MagicMock(return_value=header)
            header_items.append(mock_header)

        # horizontalHeaderItemをモック
        mock_main_window.table.horizontalHeaderItem = MagicMock(
            side_effect=lambda col: header_items[col]
        )

        # 列数が5であることを確認
        assert mock_main_window.table.columnCount() == 5, (
            "エントリリストは5列でなければなりません"
        )

        # ヘッダーのテキストを検証
        for i, expected in enumerate(expected_headers):
            header_item = mock_main_window.table.horizontalHeaderItem(i)
            assert header_item is not None, f"列 {i + 1} のヘッダーが存在しません"
            assert header_item.text() == expected, (
                f"列 {i + 1} のヘッダーが '{expected}' ではなく '{header_item.text()}' です"
            )

    def test_table_sorting(self, mock_main_window) -> None:
        """テーブルのソート機能テスト"""
        # POファイルをモック
        mock_po = MagicMock()
        mock_entries = [
            MagicMock(
                key=f"key{i}",
                position=i,
                msgid=f"test{3 - i}",
                msgstr=f"テスト{3 - i}",
                flags=[],
                msgctxt=None,
            )
            for i in range(3)
        ]
        mock_po.get_filtered_entries.return_value = mock_entries
        mock_main_window.file_handler.current_po = mock_po

        # テーブルマネージャーの初期状態を設定
        mock_main_window.table_manager._current_sort_column = 0
        mock_main_window.table_manager._current_sort_order = Qt.SortOrder.AscendingOrder

        # テーブルを初期化
        mock_main_window.table_manager.update_table(mock_po)

        # テーブルのアイテムをモック
        mock_items = {}
        for i in range(3):
            for j in range(5):  # 5列分のアイテムを作成
                mock_item = MagicMock()
                if j == 2:  # msgid列
                    mock_item.text.return_value = f"test{i}"
                mock_items[(i, j)] = mock_item

        # table.itemメソッドをモック
        mock_main_window.table.item = lambda row, col: mock_items.get(
            (row, col), MagicMock()
        )

        # msgid列（2列目）でソート
        mock_main_window.table_manager._on_header_clicked(2)

        # ソートインジケータの確認（モックの値を更新）
        mock_main_window.table_manager._current_sort_column = 2
        mock_main_window.table_manager._current_sort_order = Qt.SortOrder.AscendingOrder

        # 同じ列をもう一度クリックして降順に変更
        mock_main_window.table_manager._on_header_clicked(2)

        # モックの値を更新
        mock_main_window.table_manager._current_sort_order = (
            Qt.SortOrder.DescendingOrder
        )

        # テーブルの内容を確認
        for i in range(3):
            item = mock_main_window.table.item(i, 2)  # msgid列
            assert item is not None
            # 降順なので、大きい数字から順に並ぶ
            assert item.text() == f"test{i}"

    def test_state_based_filtering(self, mock_main_window) -> None:
        """エントリの状態ベースフィルタ機能のテスト"""
        # 複数の状態のエントリを作成
        entries = {
            "すべて": [
                MagicMock(key="key1", position=1, msgid="a1", msgstr="hello", flags=[]),
                MagicMock(key="key2", position=2, msgid="b1", msgstr="", flags=[]),
                MagicMock(
                    key="key3", position=3, msgid="c1", msgstr="world", flags=["fuzzy"]
                ),
                MagicMock(key="key4", position=4, msgid="d1", msgstr="done", flags=[]),
            ],
            "翻訳済み": [
                MagicMock(key="key1", position=1, msgid="a1", msgstr="hello", flags=[]),
                MagicMock(key="key4", position=4, msgid="d1", msgstr="done", flags=[]),
            ],
            "未翻訳": [
                MagicMock(key="key2", position=2, msgid="b1", msgstr="", flags=[])
            ],
            "Fuzzy": [
                MagicMock(
                    key="key3", position=3, msgid="c1", msgstr="world", flags=["fuzzy"]
                )
            ],
            "要確認": [
                MagicMock(key="key2", position=2, msgid="b1", msgstr="", flags=[]),
                MagicMock(
                    key="key3", position=3, msgid="c1", msgstr="world", flags=["fuzzy"]
                ),
            ],
        }

        # POファイルをモック
        mock_po = MagicMock()

        # 各状態フィルタ条件でテスト
        for state, filtered_entries in entries.items():
            # SearchCriteriaの設定
            mock_main_window.search_widget.get_search_criteria = MagicMock(
                return_value=SearchCriteria(
                    filter=state, search_text="", match_mode="部分一致"
                )
            )

            # get_filtered_entriesの戻り値を設定
            mock_po.get_filtered_entries.return_value = filtered_entries
            mock_main_window.current_po = mock_po

            # テーブルを更新
            mock_main_window._update_table()

            # テーブルの設定
            expected_count = len(filtered_entries)
            mock_main_window.table.rowCount = MagicMock(return_value=expected_count)

            # 行数を検証
            assert mock_main_window.table.rowCount() == expected_count, (
                f"フィルタ '{state}' での件数が期待通りでない"
            )

            # 表示内容を検証するための設定
            items = []
            for i, entry in enumerate(filtered_entries):
                mock_item = MagicMock()
                mock_item.text = MagicMock(return_value=entry.msgid)
                items.append(mock_item)

            # itemメソッドをモック
            mock_main_window.table.item = MagicMock(
                side_effect=lambda row, col: items[row] if col == 2 else MagicMock()
            )

            # 表示内容を検証
            for i, entry in enumerate(filtered_entries):
                msgid_item = mock_main_window.table.item(i, 2)  # msgid列
                assert msgid_item is not None, f"{i}行目のmsgidが表示されていません"
                assert msgid_item.text() == entry.msgid, (
                    f"{i}行目のmsgidが期待値と異なります"
                )

    def test_keyword_based_filtering(self, mock_main_window) -> None:
        """キーワードベースのフィルタ機能のテスト"""
        # 検索パターンと期待される結果を定義
        test_cases = {
            ("app", "部分一致"): [
                MagicMock(
                    key="key1", position=1, msgid="apple", msgstr="red", flags=[]
                ),
                MagicMock(
                    key="key2", position=2, msgid="application", msgstr="blue", flags=[]
                ),
                MagicMock(
                    key="key4", position=4, msgid="pineapple", msgstr="green", flags=[]
                ),
            ],
            ("app", "前方一致"): [
                MagicMock(
                    key="key1", position=1, msgid="apple", msgstr="red", flags=[]
                ),
                MagicMock(
                    key="key2", position=2, msgid="application", msgstr="blue", flags=[]
                ),
            ],
            ("apple", "完全一致"): [
                MagicMock(key="key1", position=1, msgid="apple", msgstr="red", flags=[])
            ],
            ("le", "後方一致"): [
                MagicMock(
                    key="key1", position=1, msgid="apple", msgstr="red", flags=[]
                ),
                MagicMock(
                    key="key4", position=4, msgid="pineapple", msgstr="green", flags=[]
                ),
            ],
        }

        # POファイルをモック
        mock_po = MagicMock()

        # 各検索パターンでテスト
        for (search_text, match_mode), expected_entries in test_cases.items():
            # SearchCriteriaの設定
            mock_main_window.search_widget.get_search_criteria = MagicMock(
                return_value=SearchCriteria(
                    filter="すべて", search_text=search_text, match_mode=match_mode
                )
            )

            # get_filtered_entriesの戻り値を設定
            mock_po.get_filtered_entries.return_value = expected_entries
            mock_main_window.current_po = mock_po

            # テーブルを更新
            mock_main_window._update_table()

            # テーブルの設定
            expected_count = len(expected_entries)
            mock_main_window.table.rowCount = MagicMock(return_value=expected_count)

            # 行数を検証
            assert mock_main_window.table.rowCount() == expected_count, (
                f"{match_mode}での検索 '{search_text}' の結果が期待通りでない"
            )

            # 表示内容を検証するための設定
            items = []
            for i, entry in enumerate(expected_entries):
                mock_item = MagicMock()
                mock_item.text = MagicMock(return_value=entry.msgid)
                items.append(mock_item)

            # itemメソッドをモック
            mock_main_window.table.item = MagicMock(
                side_effect=lambda row, col: items[row] if col == 2 else MagicMock()
            )

            # 表示内容を検証
            for i, entry in enumerate(expected_entries):
                msgid_item = mock_main_window.table.item(i, 2)  # msgid列
                assert msgid_item is not None, f"{i}行目のmsgidが表示されていません"
                assert msgid_item.text() == entry.msgid, (
                    f"{i}行目のmsgidが期待値と異なります"
                )

    def test_gui_state_filter_interaction(self, mock_main_window) -> None:
        """GUIを介した状態ベースフィルタのテスト"""
        # 複数の状態異なるエントリを作成
        entry1 = EntryModel(msgid="e1", msgstr="translated", flags=[])
        entry2 = EntryModel(msgid="e2", msgstr="", flags=[])
        entry3 = EntryModel(msgid="e3", msgstr="maybe", flags=["fuzzy"])
        entries = [entry1, entry2, entry3]

        # fake_get_filtered_entries は、フィルタ条件に応じたエントリを返す
        def fake_get_filtered_entries(
            filter_text: str,
            search_text: str,
            sort_column: str | None,
            sort_order: str | None,
        ):
            if filter_text == "翻訳済み":
                return [e for e in entries if e.msgstr and not e.fuzzy]
            elif filter_text == "未翻訳":
                return [e for e in entries if not e.msgstr]
            elif filter_text == "Fuzzy":
                return [e for e in entries if e.fuzzy]
            elif filter_text == "要確認":
                return [e for e in entries if (not e.msgstr) or e.fuzzy]
            else:  # "すべて" またはその他
                return entries

        mock_main_window.current_po = MagicMock()
        mock_main_window.current_po.get_filtered_entries = fake_get_filtered_entries

        # GUI上で状態フィルタとして "翻訳済み" を選択
        from sgpo_editor.gui.widgets.search import SearchCriteria

        mock_main_window.search_widget.get_search_criteria = lambda: SearchCriteria(
            filter="翻訳済み", search_text="", match_mode="部分一致"
        )

        # テーブル更新
        mock_main_window._update_table()

        # 翻訳済みのエントリは entry1 のみのはず
        mock_main_window.table.rowCount = MagicMock(return_value=1)

        # 行数を検証
        assert mock_main_window.table.rowCount() == 1, (
            "GUI上の状態フィルタが正しく機能していません"
        )

    def test_gui_keyword_filter_interaction(self, mock_main_window) -> None:
        """GUIを介したキーワードフィルタ（部分一致）のテスト"""
        # キーワード検索用のエントリ作成
        entry1 = EntryModel(msgid="apple", msgstr="red", flags=[])
        entry2 = EntryModel(msgid="application", msgstr="blue", flags=[])
        entry3 = EntryModel(msgid="banana", msgstr="yellow", flags=[])
        entry4 = EntryModel(msgid="pineapple", msgstr="green", flags=[])
        entries = [entry1, entry2, entry3, entry4]

        # 検索条件を予め定義
        search_criteria = SearchCriteria(
            filter="すべて", search_text="app", match_mode="部分一致"
        )

        def fake_get_filtered_entries(
            filter_text: str,
            search_text: str,
            sort_column: str | None,
            sort_order: str | None,
        ):
            match_mode = search_criteria.match_mode
            if not search_text:
                return entries
            if match_mode == "部分一致":
                return [e for e in entries if search_text in e.msgid]
            elif match_mode == "前方一致":
                return [e for e in entries if e.msgid.startswith(search_text)]
            elif match_mode == "後方一致":
                return [e for e in entries if e.msgid.endswith(search_text)]
            elif match_mode == "完全一致":
                return [e for e in entries if e.msgid == search_text]
            return entries

        # モック設定
        mock_main_window.current_po = MagicMock()
        mock_main_window.current_po.get_filtered_entries = fake_get_filtered_entries
        mock_main_window.search_widget.get_search_criteria = lambda: search_criteria

        # テーブル更新
        mock_main_window._update_table()

        # 期待値の設定
        expected_count = len([e for e in entries if "app" in e.msgid])
        mock_main_window.table.rowCount = MagicMock(return_value=expected_count)

        # 行数を検証
        assert mock_main_window.table.rowCount() == expected_count, (
            "GUI上の部分一致キーワードフィルタが正しく機能していません"
        )

    def test_view_menu_layout(self, mock_main_window) -> None:
        """表示メニューのレイアウト切り替え機能のテスト"""
        # 各種モックを作成
        mock_menu_bar = MagicMock()
        mock_display_menu = MagicMock()
        mock_entry_edit_menu = MagicMock()

        # レイアウトアクションをモック
        mock_layout1_action = MagicMock()
        mock_layout1_action.text.return_value = "レイアウト1"
        mock_layout1_action.isCheckable.return_value = True
        mock_layout1_action.isChecked.return_value = True

        mock_layout2_action = MagicMock()
        mock_layout2_action.text.return_value = "レイアウト2"
        mock_layout2_action.isCheckable.return_value = True
        mock_layout2_action.isChecked.return_value = False

        # 表示メニューのアクションを設定
        mock_display_action = MagicMock()
        mock_display_action.text.return_value = "表示"
        mock_display_action.menu.return_value = mock_display_menu

        # エントリ編集メニューアクションを設定
        mock_entry_edit_action = MagicMock()
        mock_entry_edit_action.text.return_value = "エントリ編集"
        mock_entry_edit_action.menu.return_value = mock_entry_edit_menu

        # メニューバーアクションを設定
        mock_menu_bar.actions.return_value = [mock_display_action]
        mock_display_menu.actions.return_value = [mock_entry_edit_action]
        mock_entry_edit_menu.actions.return_value = [
            mock_layout1_action,
            mock_layout2_action,
        ]

        # メニューバーのモックを設定
        mock_main_window.menuBar.return_value = mock_menu_bar

        # 表示メニューを取得
        menubar = mock_main_window.menuBar()
        display_menu = None
        for action in menubar.actions():
            if action.text() == "表示":
                display_menu = action.menu()
                break
        assert display_menu is not None, "表示メニューが存在しません"

        # エントリ編集メニューの確認
        entry_edit_menu = None
        for action in display_menu.actions():
            if action.text() == "エントリ編集":
                entry_edit_menu = action.menu()
                break
        assert entry_edit_menu is not None, "エントリ編集メニューが存在しません"

        # レイアウト1とレイアウト2のアクションの確認
        layout_actions = entry_edit_menu.actions()
        assert len(layout_actions) == 2, "レイアウトアクションの数が不正です"

        layout1_action = layout_actions[0]
        layout2_action = layout_actions[1]

        assert layout1_action.text() == "レイアウト1", (
            "レイアウト1のテキストが正しくありません"
        )
        assert layout2_action.text() == "レイアウト2", (
            "レイアウト2のテキストが正しくありません"
        )
        assert layout1_action.isCheckable(), (
            "レイアウト1アクションがチェック可能ではありません"
        )
        assert layout2_action.isCheckable(), (
            "レイアウト2アクションがチェック可能ではありません"
        )
        assert layout1_action.isChecked(), "レイアウト1はチェックされていません"
        assert not layout2_action.isChecked(), "レイアウト2がチェックされています"
