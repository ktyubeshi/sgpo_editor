# Updated Filtering Logic

This document outlines the latest filtering and caching strategy used in `ViewerPOFileFilter` and `EntryCacheManager`.

* Filter keywords provided to `get_filtered_entries` are merged with the current `search_text`.
* A unique filter key generated via MD5 is used to store filtered IDs in `EntryCacheManager`.
* When filter conditions change, `EntryCacheManager.invalidate_filter_cache` is called with the generated key.
* The cache manager maintains LRU caches for entries and filtered ID lists with size limits defined in configuration.
