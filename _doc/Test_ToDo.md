了解しました。既存の実装がある程度進んでいることを前提に、その**改修済み箇所に対応するテスト**の修正・追加に焦点を当てたToDoリストを作成します。
## ToDo - Update Tests for Refined Cache System

**Objective:** Ensure the existing test suite is updated and new tests are added to thoroughly validate the behavior and integration of the newly refined cache (`EntryCacheManager`) and database (`DatabaseAccessor`, `InMemoryEntryStore`) components, according to the design specified in `_doc/2_2_dbcash_architecture.md`.

**Primary Reference:** `_doc/2_2_dbcash_architecture.md`

---

### Test Update Task List

**IMPORTANT:** Ensure all tests run successfully using `uv run pytest`.

#### 1. Unit Tests for `EntryCacheManager`

*   **Files:** `tests/core/test_cache_manager.py` (新規作成または既存ファイルを修正)
    *   `[x]` **Test Custom LRU (CompleteEntryCache):**
        *   Verify that items are evicted based on least recent use when `max_size` is exceeded.
        *   Verify eviction based on estimated memory size if implemented.
        *   Test `get` updates the access order.
    *   `[x]` **Test Custom LRU (FilterCache):**
        *   Verify eviction based on least recent use when `max_size` is exceeded.
        *   Test `get` updates the access order.
        *   Verify `_make_key` produces consistent keys for identical filter conditions.
    *   `[x]` **Test TTL (CompleteEntryCache):**
        *   If TTL is implemented (> 0), verify that `get_entry` returns `None` for expired entries.
        *   Verify that expired entries are eventually removed (or marked as expired).
    *   `[x]` **Test Prefetching API:**
        *   Test `prefetch_entries` correctly calls the `fetch_callback`.
        *   Test that fetched entries are added to `CompleteEntryCache`.
        *   Test `is_key_being_prefetched` returns correct status during and after prefetching.
        *   Test interaction with thread safety mechanisms (`_lock`, `_prefetching_keys`).
    *   `[x]` **Test Invalidation API:**
        *   Test `invalidate_entry` correctly removes the entry from `CompleteEntryCache` and `_entry_timestamps`.
        *   Test `invalidate_filter_cache` clears the `FilterCache`.
        *   Test `clear_all` clears all relevant cache structures.
    *   `[x]` **Test Configuration:**
        *   Verify that cache sizes, TTL, and prefetch settings are correctly loaded and applied from `get_cache_config()`. Test behavior when cache is disabled (`CACHE_ENABLED=False`).

#### 2. Unit/Integration Tests for `DatabaseAccessor` & `InMemoryEntryStore`

*   **Files:** `tests/core/test_database_accessor.py`, `tests/models/test_database.py` (新規作成または既存ファイルを修正)
    *   `[x] 完了` **Test FTS5 Search (`advanced_search`):**
        *   Verify that `advanced_search` uses `MATCH` operator when `search_text` is provided. (Mock `sqlite3.Cursor.execute` to check the generated SQL or test against a real `InMemoryEntryStore` with FTS5 enabled).
        *   Test various keyword search scenarios (single word, multiple words, different fields).
        *   Test `exact_match` and `case_sensitive` parameters with FTS5 (FTS5 has its own tokenization rules, so exact match might need careful handling or alternative queries).
    *   `[x] 完了` **Test Dictionary Return Types:** Ensure all data retrieval methods (`get_entry_by_key`, `get_entries_by_keys`, `get_filtered_entries`, `advanced_search`, etc.) consistently return `EntryDict` (or `List[EntryDict]`/`Dict[str, EntryDict]`) and **not** `EntryModel` objects.
    *   `[ ]` **Test Update Hook Setup (Integration):**
        *   Create an `InMemoryEntryStore` instance.
        *   Set up a mock update hook callback function.
        *   Perform INSERT, UPDATE, DELETE operations on the `entries` table.
        *   Verify that the mock callback is triggered with the correct operation type, table name, and rowid/key.

#### 3. Integration Tests for Cache Invalidation

*   **Files:** `tests/integration/test_cache_invalidation.py` (新規作成推奨)
    *   `[ ]` **Test DB Update -> Cache Invalidation:**
        *   Set up `InMemoryEntryStore`, `DatabaseAccessor`, and `EntryCacheManager`.
        *   Register a mock handler or directly link the DB update hook to `EntryCacheManager.invalidate_entry` / `invalidate_filter_cache`.
        *   Add an entry, ensure it's cached in `CompleteEntryCache`.
        *   Generate and cache a filter result including this entry in `FilterCache`.
        *   Update the entry in the database using `DatabaseAccessor`.
        *   Verify the entry is removed from `CompleteEntryCache` via `invalidate_entry`.
        *   Verify `FilterCache` is cleared via `invalidate_filter_cache`.
        *   Test DELETE and INSERT operations similarly trigger invalidation.

#### 4. Integration Tests for Data Flow & Caching Logic

*   **Files:** `tests/integration/test_viewer_po_file*.py`, `tests/integration/test_facades.py` (新規作成または既存ファイルを修正)
    *   `[ ]` **Test Filtering Data Flow (Cache Miss):**
        *   Start with an empty cache.
        *   Call `ViewerPOFile.get_filtered_entries` (or Facade equivalent).
        *   Verify `EntryCacheManager.get_filter_cache` is called and returns `None`.
        *   Verify `DatabaseAccessor.advanced_search` (or equivalent) is called.
        *   Verify `EntryCacheManager.set_filtered_entries` is called with the results from the DB (converted to `EntryModel`s).
        *   Verify the final result matches the DB result.
    *   `[ ]` **Test Filtering Data Flow (Cache Hit):**
        *   Pre-populate the `FilterCache` using `set_filtered_entries`.
        *   Call `ViewerPOFile.get_filtered_entries` with the same filter conditions.
        *   Verify `EntryCacheManager.get_filter_cache` is called and returns the cached list.
        *   Verify `DatabaseAccessor` is **not** called.
        *   Verify the final result matches the cached list.
    *   `[ ]` **Test Single Entry Retrieval (Cache Miss & Hit):** Simulate the flow for `get_entry_by_key`, verifying interactions with `CompleteEntryCache` and `DatabaseAccessor`.
    *   `[ ]` **Test `EntryModel` Instantiation:** Add assertions in relevant tests to confirm `EntryModel.model_construct` is **not** being called when fetching data from the DB via `DatabaseAccessor`. Check that `EntryModel(**data)` or `model_validate` is used.

#### 5. Integration Tests for Prefetching

*   **Files:** `tests/integration/test_prefetching.py` (新規作成推奨)
    *   `[ ]` **Test Prefetch Trigger:** Simulate UI scroll events that trigger `EntryListFacade` (or equivalent) to call `EntryCacheManager.prefetch_entries`.
    *   `[ ]` **Test Prefetch Callback:** Verify `prefetch_entries` calls the correct `fetch_callback` (`ViewerPOFile.get_entries_by_keys`).
    *   `[ ]` **Test Prefetch Caching:** Verify that entries fetched via prefetching are correctly added to `CompleteEntryCache`.
    *   `[ ]` **Test Prefetch Status:** Verify `is_key_being_prefetched` correctly reflects the state.

#### 6. GUI Integration Tests (Review and Refactor)

*   **Files:** `tests/gui/**/*.py`
    *   `[ ]` **Review Table Update Tests:** Examine tests involving `TableManager.update_table` or `EntryListFacade.update_table`. Ensure they still pass and correctly reflect the data flow where filtering/sorting happens *before* the update call. Mock `ViewerPOFile.get_filtered_entries` or the Facade method appropriately.
    *   `[ ]` **Review Filtering/Search Tests:** Check GUI tests that simulate filter/search changes. Ensure they correctly trigger Facade methods and that the table updates as expected based on the (mocked) filtered data.
    *   `[ ]` **Review Entry Selection/Editing Tests:** Ensure tests involving `EntryEditor` and its interaction with Facades (`EntryEditorFacade`) correctly handle data loading (checking cache first) and saving (updating DB and invalidating cache via the update hook).

#### 7. Performance Tests

*   **Files:** `tests/performance/` (新規作成または既存ファイルを修正)
    *   `[ ]` **Benchmark FTS5 vs LIKE:** Create benchmark tests comparing `DatabaseAccessor.advanced_search` using FTS5 vs. a simulated `LIKE` query for keyword searches on a large dataset.
    *   `[ ]` **Benchmark Filtering (Cache Hit vs Miss):** Measure the time taken for `ViewerPOFile.get_filtered_entries` (or Facade equivalent) with and without filter cache hits.
    *   `[ ]` **Benchmark Scrolling/Prefetching:** If feasible, simulate scrolling and measure the impact of prefetching on subsequent entry retrieval times.

#### 8. Test Cleanup

*   `[ ]` **Remove Obsolete Mocks/Tests:** Delete any test code specifically designed for the *old* caching implementation that is no longer relevant.
*   `[ ]` **Ensure Test Independence:** Verify that tests clean up any modified global state (like shared cache instances or mock settings) properly using fixtures (`setup_method`, `teardown_method`, or pytest fixtures).

---

**Final Verification:** After completing these test updates, run the *entire* test suite (`uv run pytest`). Address any failures. Ensure test coverage for the new cache/DB logic is adequate (use `--cov`).