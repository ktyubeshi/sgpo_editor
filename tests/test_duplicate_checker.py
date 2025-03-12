from __future__ import annotations

from sgpo.core import pofile_from_text


def test_check_duplicates_with_compressed_notation():
    """圧縮表記を含む重複エントリのチェック"""
    po_text = """
msgctxt "wnd(Log|Project|Std|).:"
msgid "Continue"
msgstr "続ける"

msgctxt "wndLog.:"
msgid "Continue"
msgstr "続ける"
"""
    po = pofile_from_text(po_text)
    duplicates = po.check_duplicates()

    assert len(duplicates) == 1
    assert duplicates[0].msgid == "Continue"
    assert duplicates[0].msgctxt1 == "wnd(Log|Project|Std|).:"
    assert duplicates[0].msgctxt2 == "wndLog.:"


def test_check_duplicates_with_no_duplicates():
    """重複がない場合のチェック"""
    po_text = """
msgctxt "wnd(Log|Project|).tbtFlowFeatureStart"
msgid "Start a new Git-Flow feature."
msgstr "新しい Git-Flow の feature を開始します。"

msgctxt "wnd(Log|Project|Std|).:"
msgid "Abort"
msgstr "中止"
"""
    po = pofile_from_text(po_text)
    duplicates = po.check_duplicates()

    assert len(duplicates) == 0


def test_check_duplicates_with_multiple_duplicates():
    """複数の重複エントリのチェック"""
    po_text = """
msgctxt "wnd(Log|Project|).:"
msgid "Continue"
msgstr "続ける"

msgctxt "wndLog.:"
msgid "Continue"
msgstr "続ける"

msgctxt "wnd(Log|Project|).:"
msgid "Abort"
msgstr "中止"

msgctxt "wndLog.:"
msgid "Abort"
msgstr "中止"
"""
    po = pofile_from_text(po_text)
    duplicates = po.check_duplicates()

    assert len(duplicates) == 2
    # 重複エントリの順序は保証されないため、msgidでソートして比較
    duplicates.sort(key=lambda x: x.msgid)
    assert duplicates[0].msgid == "Abort"
    assert duplicates[1].msgid == "Continue"


def test_expand_msgctxt():
    """圧縮表記の展開機能のテスト"""

    # 内部関数をテストするため、一時的にアクセス
    from sgpo.duplicate_checker import _expand_msgctxt

    expanded = _expand_msgctxt("wnd(Log|Project|Std|).:")
    assert set(expanded) == {"wndLog.:", "wndProject.:", "wndStd.:"}
