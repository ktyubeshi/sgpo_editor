# ToDo - Implement New Cache Design

**Objective:** Replace the existing cache system with the new design specified in `2_2_dbcash_architecture.md`. This involves implementing the new cache module and refactoring all existing code that uses the old cache to use the new one.

**Primary Reference:** `2_2_dbcash_architecture.md` (All implementation details, API definitions, configurations, and behaviors must strictly follow this document).

---

## Task List

**IMPORTANT:** Perform all changes within a dedicated feature branch (e.g., `feature/new-cache-design`).

### 1. Implement New Cache Module

* **File:** `src/db/dbcash.py` (Or create a new file/module as specified in `2_2_dbcash_architecture.md` if the structure changes)
    * `[ ]` **Implement Core Cache Logic:**
        * Define and implement the main cache class(es) and functions as per the API specification in `2_2_dbcash_architecture.md`.
        * Ensure all public methods (e.g., `get`, `set`, `delete`, `exists`, `clear`, `initialize`) are implemented according to the specified signatures, behavior, and error handling.
        * Implement logic for cache expiration (TTL), size limits, and invalidation as defined in the design document.
    * `[ ]` **Implement Configuration Handling:**
        * Read necessary configuration parameters (e.g., connection details, default TTL, max size) from the application's configuration system (likely involving `src/config.py`). Refer to `2_2_dbcash_architecture.md` for required parameters.
    * `[ ]` **Add Type Hinting:** Use appropriate type hints for all functions and methods, referencing types from `src/models/type_definitions.py` or defining new ones if necessary.

### 2. Update Configuration

* **File:** `src/config.py`
    * `[ ]` **Add New Cache Settings:** Define and add all configuration variables required by the new cache module, as specified in `2_2_dbcash_architecture.md`. Include sensible default values where appropriate.
    * `[ ]` **(Optional) Mark Old Cache Settings as Obsolete:** Add comments indicating that configuration variables related to the *old* cache system are deprecated and will be removed. (Actual removal will happen later).

### 3. Refactor Cache Usage in Data Operations

* **File:** `src/db/db_operations.py` (And potentially other files in `src/db/`)
    * `[ ]` **Identify Old Cache Usage:** Locate all instances where the old cache system is imported and used (e.g., function calls for getting, setting, deleting cached data).
    * `[ ]` **Replace with New Cache API:**
        * Modify the code to import and use the *new* cache module/class(es) implemented in Step 1.
        * Replace calls to old cache functions/methods with the corresponding calls to the new API.
        * Adjust function arguments, data serialization/deserialization (if cache format changed), and error handling as required by the new API and `2_2_dbcash_architecture.md`.
        * Update cache key generation logic if the new design specifies changes.

### 4. Refactor Cache Usage in Business Logic

* **File:** `src/logic/translation_core.py` (And potentially other files in `src/logic/`)
    * `[ ]` **Identify Old Cache Usage:** Locate all usages of the old cache system within the business logic layer.
    * `[ ]` **Replace with New Cache API:** Perform the same replacement steps as described for `src/db/db_operations.py`, ensuring adherence to the new cache's API and behavior as defined in `2_2_dbcash_architecture.md`. Pay close attention to how application-level data is cached and invalidated.

### 5. Refactor Cache Usage in API Endpoints

* **Files:** `src/api/endpoints/*.py`
    * `[ ]` **Identify Old Cache Usage:** Locate any caching mechanisms used at the API endpoint level (e.g., response caching, caching results of expensive operations) that utilize the old cache system. This might involve decorators or direct calls.
    * `[ ]` **Replace with New Cache API:** Update the code to use the new cache system. Refactor decorators or function calls, ensuring correct cache keys, TTLs, and conditional caching logic align with `2_2_dbcash_architecture.md`.

### 6. Refactor Cache Usage in Utilities

* **Files:** `src/utils/*.py`
    * `[ ]` **Identify Old Cache Usage:** Search for any utility functions that interact with or depend on the old cache system.
    * `[ ]` **Update or Remove Utilities:**
        * If utilities are still needed, refactor them to use the *new* cache API.
        * If utilities were specific to the old cache, mark them for removal or remove them if clearly unused elsewhere.
        * Implement any *new* utility functions required by the new cache design (as specified in `2_2_dbcash_architecture.md`).

### 7. Update Data Models (If Necessary)

* **Files:** `src/models/data_models.py`, `src/models/type_definitions.py`
    * `[ ]` **Review Cache Data Structures:** Check `2_2_dbcash_architecture.md` to see if the structure or format of data stored in the cache has changed significantly.
    * `[ ]` **Update Type Definitions:** If necessary, update relevant `TypedDict`, `TypeAlias`, Pydantic models, or other type definitions to reflect the new structure of cached data.

### 8. Implement/Update Tests

* **Files:** `tests/` (specifically tests related to cache, db, logic, api)
    * `[ ]` **Write Unit Tests for New Cache Module:** Create comprehensive unit tests for the new cache module (`src/db/dbcash.py` or equivalent). Test all public methods, configuration options, edge cases (e.g., cache full, item expired, key not found), and error handling as defined in `2_2_dbcash_architecture.md`. Use mocking where appropriate (e.g., for external dependencies like Redis if used).
    * `[ ]` **Update Integration Tests:** Identify existing integration tests that implicitly or explicitly tested behavior involving the *old* cache. Modify these tests:
        * Update test setup/teardown related to caching.
        * Adjust mocks and assertions to work with the *new* cache API and behavior.
        * Ensure tests correctly validate scenarios like cache hits, misses, and invalidation within the application flow.
    * `[ ]` **Remove Obsolete Tests:** Delete test files or individual test cases that were solely dedicated to testing the *old*, now removed, cache system.

### 9. Final Cleanup (After all steps above are complete and verified)

* **Files:** Entire Codebase
    * `[ ]` **Remove Old Cache Code:** Search and remove all code related to the old cache system (imports, function/class definitions, utility functions).
    * `[ ]` **Remove Old Cache Configuration:** Remove the deprecated configuration settings from `src/config.py` identified in Step 2.
    * `[ ]` **Remove Old Cache Dependencies:** If the old cache had specific library dependencies that are no longer needed, remove them from the project's dependency file (e.g., `requirements.txt`, `pyproject.toml`).

---

**Final Verification:** After completing all tasks, run the entire test suite (unit, integration, etc.) to ensure all tests pass and no regressions have been introduced. Manually verify key functionalities if necessary. Ensure the implementation strictly adheres to `2_2_dbcash_architecture.md`.