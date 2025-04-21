# ToDo - Refine Cache System based on New Design

**Objective:** Verify, enhance, and refactor the existing cache (`EntryCacheManager`) and database (`DatabaseAccessor`, `InMemoryEntryStore`) components to fully align with the improved design specified in `_doc/2_2_dbcash_architecture.md`.

**Primary Reference:** `_doc/2_2_dbcash_architecture.md` (All implementation details, API definitions, configurations, and behaviors must strictly follow this document).

---

## Task List

**IMPORTANT:** Perform all changes within a dedicated feature branch (e.g., `feature/refine-cache-design`).

### 1. Enhance Cache Module (`EntryCacheManager`)

*   **File:** `src/sgpo_editor/core/cache_manager.py`
    *   `[ ]` **Implement Custom LRU:** Verify or implement the custom LRU mechanism for `CompleteEntryCache` and `FilterCache` considering both item count (`max_size`) and estimated memory usage (`sys.getsizeof`), as per the design document.
    *   `[ ]` **Implement TTL Logic:** If specified in the design, implement Time-To-Live (TTL) functionality for `CompleteEntryCache`.
    *   `[ ]` **Implement Prefetching:** Implement the `prefetch_entries` method and related logic (`is_key_being_prefetched`, `_prefetching_keys`) to work with UI requests (likely from `EntryListFacade`) and the provided `fetch_callback`. Ensure thread safety if using background threads.
    *   `[ ]` **Implement Automatic Invalidation API:** Implement `invalidate_entry(key)` and `invalidate_filter_cache()` methods. These will be called externally (e.g., by the SQLite update hook handler or Facades). Ensure `invalidate_entry` also clears relevant filter cache entries if feasible, or rely on `invalidate_filter_cache` for broader invalidation upon DB change.
    *   `[ ]` **Implement Configuration Handling:** Ensure the cache manager correctly reads and applies settings from `src/sgpo_editor/config.py` (e.g., `CACHE_ENABLED`, `COMPLETE_CACHE_MAX_SIZE`, `FILTER_CACHE_MAX_SIZE`, `PREFETCH_ENABLED`, `PREFETCH_SIZE`, `CACHE_TTL`) upon initialization.
    *   `[ ]` **Refine Type Hinting:** Ensure all methods use precise type hints, including those defined in `src/sgpo_editor/types.py`.

### 2. Enhance Database Components (`DatabaseAccessor`, `InMemoryEntryStore`)

*   **Files:** `src/sgpo_editor/core/database_accessor.py`, `src/sgpo_editor/models/database.py`
    *   `[ ]` **Implement FTS5 Search:**
        *   In `InMemoryEntryStore`: Ensure the `entries_fts` virtual table is correctly created and maintained (e.g., via triggers) for relevant fields (`msgid`, `msgstr`, etc.).
        *   In `DatabaseAccessor`: Modify `advanced_search` (and potentially `get_filtered_entries` if it calls the former) to utilize the FTS5 `MATCH` operator for keyword searches instead of `LIKE`, when `search_text` is provided. Ensure correct query construction based on `search_fields`.
    *   `[ ]` **Implement SQLite Update Hook:**
        *   In `InMemoryEntryStore` or a dedicated handler class: Set up an SQLite `update_hook` (using `sqlite3.Connection.set_update_hook`).
        *   The hook callback must identify the modified `key` (or `rowid`) and the type of operation (INSERT, UPDATE, DELETE).
        *   The callback should then trigger the appropriate invalidation method(s) in the `EntryCacheManager` instance (e.g., `invalidate_entry(key)`, `invalidate_filter_cache()`). Dependency injection or a signaling mechanism might be needed to link the hook to the cache manager.
    *   `[ ]` **Optimize SQL Queries:** Review all queries in `DatabaseAccessor` (especially `advanced_search` and `get_filtered_entries`). Ensure proper use of WHERE, ORDER BY, LIMIT, OFFSET to minimize data transfer and Python-side processing. Verify index usage (`EXPLAIN QUERY PLAN`).
    *   `[ ]` **Ensure Dictionary Return Type:** Confirm that all data retrieval methods in `DatabaseAccessor` return results as lists of dictionaries (`EntryDict`) or dictionaries mapping keys to `EntryDict`, not `EntryModel` objects, as specified in the design.

### 3. Verify and Refactor Cache/DB Usage

*   **Files:** `src/sgpo_editor/core/viewer_po_file.py` (and its component files: `base.py`, `retriever.py`, `filter.py`, `updater.py`, `stats.py`), `src/sgpo_editor/gui/facades/*.py`
    *   `[ ]` **Data Flow Verification:** Trace the data flow for filtering, single entry retrieval, and updates. Ensure it matches the sequence described in the design document (UI ↔ Facade ↔ CacheManager ↔ DBAccessor ↔ SQLite).
    *   `[ ]` **Cache Interaction:** Verify that `ViewerPOFile` components and Facades correctly interact with `EntryCacheManager`: check cache first (`get_entry`, `get_filtered_entries`), cache results after DB fetch (`set_entry`, `set_filtered_entries`), and trigger invalidation appropriately (though automatic invalidation via hook is preferred).
    *   `[ ]` **DB Interaction:** Verify that database access *only* happens through `DatabaseAccessor` and occurs primarily on cache misses or when forced updates are needed.
    *   `[ ]` **`EntryModel` Instantiation:** Search the codebase (especially where data is retrieved from `DatabaseAccessor`) and ensure `EntryModel` instances are created using standard validation (`EntryModel(**data)` or `model_validate`) and **not** `model_construct()`.
    *   `[ ]` **Facade Logic:** Ensure Facades correctly handle data conversion (Dict → Model) if needed and manage interactions between UI events and cache/DB operations.

### 4. Update Configuration

*   **File:** `src/sgpo_editor/config.py`
    *   `[ ]` **Verify/Add Cache Settings:** Ensure all settings specified in `2_2_dbcash_architecture.md` (e.g., sizes, TTL, prefetch options) are present in `DEFAULT_CONFIG` and handled correctly by `EntryCacheManager`. Add any missing settings with appropriate defaults.

### 5. Implement/Update Tests

*   **Files:** `tests/`
    *   `[ ]` **Write Unit Tests for `EntryCacheManager`:** Test custom LRU logic (item count and memory), TTL expiration, prefetching mechanism (`prefetch_entries`, `is_key_being_prefetched`), invalidation methods (`invalidate_entry`, `invalidate_filter_cache`), and configuration handling. Use mocking for dependencies like `DatabaseAccessor`.
    *   `[ ]` **Write Unit/Integration Tests for `DatabaseAccessor`:** Test FTS5 search functionality (`advanced_search` with `MATCH`), optimized query results, and dictionary return types.
    *   `[ ]` **Write Integration Tests for Update Hook:** Simulate DB updates and verify that the corresponding `EntryCacheManager` invalidation methods are called correctly.
    *   `[ ]` **Update `ViewerPOFile` / Facade Tests:** Modify existing tests to reflect the refined cache/DB interaction logic. Test scenarios involving cache hits, misses, and invalidations.
    *   `[ ]` **Performance Tests:** Update or create performance tests (using `pytest-benchmark`) for key operations like filtering/searching large datasets to verify the effectiveness of FTS5 and caching, comparing against defined KPIs.

### 6. Documentation

*   **Files:** `_doc/context_summary.md`, `_doc/todo.md`, `_doc/2_architecture_design.md`, `_doc/2_2_dbcash_architecture.md`
    *   `[x]` **Update `context_summary.md`:** Reflect the refined understanding of the codebase and the goal of enhancing the existing cache system (Done via this response).
    *   `[x]` **Update `todo.md`:** Replace the content with this new task list (Done via this response).
    *   `[ ]` **Review/Update Architecture Docs:** Ensure `2_architecture_design.md` and `2_2_dbcash_architecture.md` accurately reflect the final implemented architecture and cache strategy. Add details about FTS5 usage and the update hook mechanism if missing.

### 7. Final Cleanup (After verification)

*   **Files:** Entire Codebase
    *   `[ ]` **Remove Redundant Logic:** Remove any old caching logic or state management within `ViewerPOFile` components or Facades that is now handled by `EntryCacheManager` or `DatabaseAccessor`.
    *   `[ ]` **Code Review:** Perform a code review focusing on adherence to the cache design document and overall code quality.

---

**Final Verification:** After completing all tasks, run the entire test suite (`uv run pytest`). Manually test UI responsiveness with large PO files for filtering, searching, and scrolling. Confirm data consistency after edits. Ensure the implementation strictly adheres to `_doc/2_2_dbcash_architecture.md`.