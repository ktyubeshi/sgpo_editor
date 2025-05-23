---
created: 2025-04-20
commit: e64e69b91162950fb48505412afee95aa9a4a210
---
# Entry Operations Profiling

This document records profiling results for common entry list operations executed through the `ViewerPOFile` API. The sample file `sample_data/sample_10000.po` (10k entries) was used.

## Summary

| Operation | Time (ms) |
|-----------|----------:|
| Load PO file | 7882.07 |
| Initial filter | 676.83 |
| Select entry by key | 0.44 |
| Update entry | 0.22 |
| Filter with keyword | 697.77 |
| Sort by `msgid` | 691.49 |

Detailed profiling data is saved in `profile_results/entry_operations.prof` and `profile_results/entry_operations.txt`.
