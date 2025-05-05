# Context Summary: Cache Strategy Refinement

## 1. Codebase Overview

This codebase implements **SGPO Editor**, a desktop GUI application for editing and managing gettext PO files, built with Python and PySide6.

Key characteristics and components include:

*   **Architecture:** A layered architecture separating GUI (`sgpo_editor.gui`), core logic (`sgpo_editor.core`), and data models (`sgpo_editor.models`). It utilizes the **Facade pattern** (`sgpo_editor.gui.facades`) to decouple UI components from core functionalities.
*   **Technology:**
    *   Python 3.8+
    *   PySide6 for the graphical user interface.
    *   Pydantic V2 for data modeling (`EntryModel`) and validation.
    *   pytest for testing.
    *   uv for project and dependency management.
    *   SQLite (in-memory) for temporary data storage and querying (`InMemoryEntryStore`).
    *   A Python object caching layer (`EntryCacheManager`).
    *   A sidecar SQLite database (`EvaluationDatabase`) for persisting LLM evaluation results.
*   **Functionality:** Provides features for loading, displaying, editing, filtering, sorting, and saving PO files. Includes advanced features like metadata editing, review comments, quality scoring, and potentially LLM-based translation evaluation.
*   **Data Flow:** UI components interact with Facades, which in turn coordinate with `ViewerPOFile` (composed of several specialized components like `EntryRetrieverComponent`, `FilterComponent`, `UpdaterComponent`, `StatsComponent`). `ViewerPOFile` utilizes `EntryCacheManager` for Python object caching and `DatabaseAccessor` for interacting with the `InMemoryEntryStore`.
*   **Caching:** An `EntryCacheManager` exists, managing `EntryModel` object caches. An `InMemoryEntryStore` (SQLite) serves as a high-speed query layer. An `EvaluationDatabase` persists evaluation data separately.

## 2. Purpose of Current Changes: Implementing Enhanced Cache Design

The primary goal is to **refine and enhance the existing caching system** based on the specifications outlined in the document: `_doc/2_2_dbcash_architecture.md`. This involves verifying, modifying, and potentially adding features to the current cache (`EntryCacheManager`), database access (`DatabaseAccessor`, `InMemoryEntryStore`), and related components to fully align with the new design principles.

*   **New Design Specification:** The enhanced strategy, API, behavior, and configuration are detailed in `_doc/2_2_dbcash_architecture.md`. Key aspects include custom LRU logic with memory limits, SQLite update hook integration for automatic cache invalidation, explicit use of FTS5 for searching, and avoiding Pydantic's `model_construct`.
*   **Motivation:** To significantly improve UI responsiveness (especially with large PO files), optimize memory usage, ensure robust data consistency between the cache and the database, and increase the maintainability and testability of the data layer.
*   **Scope of Work:** The changes involve:
    1.  **Verifying and Enhancing `EntryCacheManager`:** Implementing custom LRU, memory limits, TTL (if specified), prefetching mechanism, and automatic invalidation logic triggered by DB updates.
    2.  **Verifying and Enhancing `DatabaseAccessor` & `InMemoryEntryStore`:** Ensuring efficient FTS5 search implementation, optimizing SQL queries, confirming results are returned as dictionaries/tuples, and setting up the SQLite `update_hook`.
    3.  **Refactoring Cache Usage:** Reviewing and updating how Facades (`EntryListFacade`, `EntryEditorFacade`) and `ViewerPOFile` components interact with `EntryCacheManager` and `DatabaseAccessor` to match the specified data flows.
    4.  **Ensuring Pydantic Validation:** Confirming that `EntryModel` instantiation consistently uses standard validation (`__init__` or `model_validate`) and avoids `model_construct`.
    5.  **Updating Configuration:** Modifying `src/sgpo_editor/config.py` to include any new cache-related settings from the design document.
    6.  **Updating Tests:** Writing new unit tests for the enhanced cache/DB components and updating existing integration tests to reflect the changes.
    7.  **Updating Documentation:** Rewriting `_doc/todo.md` and potentially other related documents.

## 3. Impact and Considerations

*   **Performance:** Changes aim to improve performance, particularly in list rendering, filtering, and searching large files via FTS5 and optimized caching.
*   **Data Consistency:** The new invalidation mechanism (SQLite update hook) is critical for maintaining data integrity between the cache and the UI.
*   **Memory Usage:** The custom LRU with memory limits needs careful implementation and tuning.
*   **Testing:** Thorough testing is vital to confirm the correct behavior of the cache (hits, misses, invalidation, LRU eviction, prefetching) and ensure no regressions in application functionality or data integrity. Verification against `_doc/2_2_dbcash_architecture.md` is paramount.

This summary provides the context for refining the cache system within the SGPO Editor application. All specific implementation details should follow `_doc/2_2_dbcash_architecture.md`.