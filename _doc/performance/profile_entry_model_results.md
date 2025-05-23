# EntryModel Profiling Results

This document summarizes the results of running `profile_entry_model.py` on a synthetic PO file containing 10,000 entries. The profiling was executed using `uv run python profile_entry_model.py`.

## Dataset
- File: `sample_data/sample_10000.po`
- Entries: 10,000

## Summary of profiling times
| Scenario | Total Calls | Primitive Calls | Time (s) |
|----------|------------:|----------------:|---------:|
| profile_load_polib | 531,154 | 531,152 | 0.683 |
| profile_load_sgpo | 571,159 | 571,157 | 9.069 |
| profile_instantiation_from_dicts | 600,003 | 590,003 | 0.392 |
| profile_to_dict_conversion | 270,003 | 230,003 | 0.205 |
| profile_property_access | 260,002 | 220,002 | 0.172 |
| cached_retrieval_first_pass | 899,003 | 889,003 | 0.671 |
| cached_retrieval_second_pass | 900,003 | 890,003 | 0.704 |

The results indicate that loading via **POLIB** is significantly faster than **SGPO** when processing 10,000 entries. Converting models to dictionaries and accessing properties are relatively lightweight operations. Cached retrieval demonstrates consistent performance between passes, suggesting minimal cache overhead.

