#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import pytest

"""
SGPOエディタのMainWindowテストスイート

このファイルはテストを実行するためのものではなく、すべてのMainWindow関連のテストファイルへの参照ポイントとして機能します。
実際のテストは以下の個別ファイルで実行されます:
- test_main_window.py - 基本機能とテーブルソートのテスト
- test_main_window_basic.py - 基本的なファイル操作のテスト
- test_main_window_table.py - テーブル操作関連のテスト
- test_main_window_entry.py - エントリ操作関連のテスト
- test_main_window_search.py - 検索機能関連のテスト
- test_main_window_layout.py - レイアウト関連のテスト
- test_main_window_error.py - エラー処理関連のテスト
- test_main_window_state.py - 状態管理関連のテスト

テストを実行するには、以下のコマンドを使用します:
$ uv run pytest tests/test_main_window_*.py -v

または個別のテストファイルを実行:
$ uv run pytest tests/test_main_window_basic.py -v
"""


# このファイルにはダミーテスト関数のみが含まれています
@pytest.mark.main_window
@pytest.mark.skip("テストスイートは個別のテストファイルで実行します")
def test_dummy():
    """ダミーテスト - このファイルは直接実行するためのものではありません"""
    assert True
