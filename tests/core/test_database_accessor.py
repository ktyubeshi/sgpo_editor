import pytest
from sgpo_editor.core.database_accessor import DatabaseAccessor
from sgpo_editor.models.database import InMemoryEntryStore


@pytest.fixture
def db_store():
    # テスト用のInMemoryEntryStoreインスタンスを返す（必要に応じて初期化処理を追加）
    return InMemoryEntryStore()


@pytest.fixture
def db_accessor(db_store):
    # テスト用のDatabaseAccessorインスタンスを返す（必要に応じて初期化処理を追加）
    return DatabaseAccessor(db_store)


def test_fts5_search_basic(db_accessor, db_store):
    # テスト用エントリを追加
    entry = {
        "key": "test1",
        "msgid": "hello",
        "msgstr": "world",
        "obsolete": False,
        "position": 0,
    }
    db_store.add_entry(entry)

    # FTS5検索: msgidに"hello"が含まれるエントリを検索
    results = db_accessor.advanced_search(search_text="hello")
    assert isinstance(results, list)
    assert any(r["msgid"] == "hello" for r in results)
    # 結果が辞書型で返ること
    for r in results:
        assert isinstance(r, dict)


def test_fts5_search_various_patterns(db_accessor, db_store):
    # 複数のテスト用エントリを追加
    entries = [
        {
            "key": "k1",
            "msgid": "hello world",
            "msgstr": "foo bar",
            "obsolete": False,
            "position": 0,
        },
        {
            "key": "k2",
            "msgid": "goodbye",
            "msgstr": "see you",
            "obsolete": False,
            "position": 1,
        },
        {
            "key": "k3",
            "msgid": "hello friend",
            "msgstr": "greetings",
            "obsolete": False,
            "position": 2,
        },
    ]
    for e in entries:
        db_store.add_entry(e)

    # 複数語検索（AND）
    results = db_accessor.advanced_search(search_text="hello world")
    assert any(r["key"] == "k1" for r in results)
    # 部分一致（hello）
    results = db_accessor.advanced_search(search_text="hello")
    keys = {r["key"] for r in results}
    assert "k1" in keys and "k3" in keys
    # msgstrフィールドで検索
    results = db_accessor.advanced_search(
        search_text="greetings", search_fields=["msgstr"]
    )
    assert any(r["key"] == "k3" for r in results)
    # msgidフィールドで検索（goodbye）
    results = db_accessor.advanced_search(
        search_text="goodbye", search_fields=["msgid"]
    )
    assert any(r["key"] == "k2" for r in results)


def test_fts5_search_exact_and_case(db_accessor, db_store):
    # テスト用エントリを追加
    entries = [
        {
            "key": "k1",
            "msgid": "Hello World",
            "msgstr": "Foo Bar",
            "obsolete": False,
            "position": 0,
        },
        {
            "key": "k2",
            "msgid": "hello world",
            "msgstr": "foo bar",
            "obsolete": False,
            "position": 1,
        },
        {
            "key": "k3",
            "msgid": "HELLO WORLD",
            "msgstr": "FOO BAR",
            "obsolete": False,
            "position": 2,
        },
    ]
    for e in entries:
        db_store.add_entry(e)

    # exact_match=True, case_sensitive=False
    results = db_accessor.advanced_search(
        search_text="hello world", exact_match=True, case_sensitive=False
    )
    keys = {r["key"] for r in results}
    # FTS5はデフォルトで大文字小文字区別しないため、すべてヒットする可能性が高い
    assert "k1" in keys and "k2" in keys and "k3" in keys

    # exact_match=True, case_sensitive=True
    results = db_accessor.advanced_search(
        search_text="Hello World", exact_match=True, case_sensitive=True
    )
    keys = {r["key"] for r in results}
    # 実装によるが、case_sensitive=Trueなら"Hello World"のみヒットすることを期待
    assert "k1" in keys

    # exact_match=False, case_sensitive=False
    results = db_accessor.advanced_search(
        search_text="hello", exact_match=False, case_sensitive=False
    )
    keys = {r["key"] for r in results}
    assert "k1" in keys and "k2" in keys and "k3" in keys

    # exact_match=False, case_sensitive=True
    results = db_accessor.advanced_search(
        search_text="Foo", exact_match=False, case_sensitive=True
    )
    keys = {r["key"] for r in results}
    assert "k1" in keys


def test_dict_return_types(db_accessor, db_store):
    # テスト用エントリを追加
    entry1 = {
        "key": "d1",
        "msgid": "foo",
        "msgstr": "bar",
        "obsolete": False,
        "position": 0,
    }
    entry2 = {
        "key": "d2",
        "msgid": "baz",
        "msgstr": "qux",
        "obsolete": False,
        "position": 1,
    }
    db_store.add_entry(entry1)
    db_store.add_entry(entry2)

    # get_entry_by_key
    result = db_accessor.get_entry_by_key("d1")
    assert isinstance(result, dict)
    assert result["key"] == "d1"

    # get_entries_by_keys
    results = db_accessor.get_entries_by_keys(["d1", "d2"])
    assert isinstance(results, dict)
    assert set(results.keys()) == {"d1", "d2"}
    for v in results.values():
        assert isinstance(v, dict)

    # get_filtered_entries
    filtered = db_accessor.get_filtered_entries({"msgid": "foo"})
    assert isinstance(filtered, list)
    for r in filtered:
        assert isinstance(r, dict)

    # advanced_search
    adv = db_accessor.advanced_search(search_text="foo")
    assert isinstance(adv, list)
    for r in adv:
        assert isinstance(r, dict)


def test_update_hook_called_on_insert_update_delete(db_store):
    # コールバックの呼び出し履歴を記録するリスト
    calls = []

    def mock_hook(operation, db_name, table_name, rowid):
        calls.append((operation, table_name, rowid))

    # update hookを登録
    db_store.set_update_hook(mock_hook)

    # INSERT/UPDATE/DELETEのテスト
    entry = {
        "key": "test_key",
        "msgid": "test_msgid",
        "msgstr": "test_msgstr",
        "fuzzy": False,
        "obsolete": False,
    }
    db_store.add_entry(entry)
    db_store.update_entry("test_key", {"msgstr": "updated_msgstr"})
    db_store.delete_entry("test_key")

    # 3回呼ばれること
    assert len(calls) >= 3
    # 操作種別が含まれること（1:INSERT, 2:DELETE, 23:UPDATE など sqlite3の仕様に依存）
    op_types = [c[0] for c in calls]
    assert any(op in op_types for op in (1, 18))  # 1:INSERT, 18:REPLACE
    assert any(op in op_types for op in (2, 9))  # 2:DELETE, 9:TRUNCATE
    assert any(op in op_types for op in (23, 18))  # 23:UPDATE, 18:REPLACE
