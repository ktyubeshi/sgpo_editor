#!/usr/bin/env python
# pylint: disable=protected-access, undefined-variable, no-member, unused-argument
from __future__ import annotations

import pytest

# pytestでは特別なテストスイートの設定は不要です
# pytestは自動的にtest_で始まる関数やクラスを検出します

# 以下のテストはpytestの構造に合わせて、各テストファイルで直接実行されます
# TestMainWindowBasic
# TestMainWindowTable
# TestMainWindowEntry
# TestMainWindowSearch
# TestMainWindowLayout

# 必要に応じて特定のテストを実行するためのマーカーを定義できます
@pytest.mark.main_window
@pytest.mark.skip("テストスイートは個別のテストファイルで実行します")
def test_dummy():
    """ダミーテスト - pytestの構造に合わせるため"""
    assert True
