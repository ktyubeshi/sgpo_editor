import asyncio
import cProfile
import pstats
import time
from pathlib import Path

from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.core.po_factory import POLibraryType
from sgpo_editor.core.constants import TranslationStatus


PROFILE_DIR = Path(__file__).parent / "profile_results"
PROFILE_DIR.mkdir(exist_ok=True)
SAMPLE_PO_PATH = Path(__file__).parent / "sample_data" / "sample_10000.po"


def run_profile():
    viewer = ViewerPOFile(library_type=POLibraryType.SGPO)

    timings = {}
    start = time.perf_counter()
    asyncio.run(viewer.load(str(SAMPLE_PO_PATH)))
    timings["load"] = time.perf_counter() - start

    start = time.perf_counter()
    entries = viewer.filter.get_filtered_entries(
        filter_text=TranslationStatus.ALL,
        filter_keyword="",
        match_mode="部分一致",
        case_sensitive=False,
        filter_status=None,
        filter_obsolete=False,
        update_filter=True,
        search_text="",
    )
    timings["initial_filter"] = time.perf_counter() - start

    first_key = entries[0].key

    start = time.perf_counter()
    viewer.get_entry_by_key(first_key)
    timings["select_entry"] = time.perf_counter() - start

    start = time.perf_counter()
    viewer.update_entry(first_key, "msgstr", "updated")
    timings["update_entry"] = time.perf_counter() - start

    start = time.perf_counter()
    viewer.filter.get_filtered_entries(
        filter_text=TranslationStatus.ALL,
        filter_keyword="",
        match_mode="部分一致",
        case_sensitive=False,
        filter_status=None,
        filter_obsolete=False,
        update_filter=True,
        search_text="keyword",
    )
    timings["filter_keyword"] = time.perf_counter() - start

    viewer.filter.sort_column = "msgid"
    viewer.filter.sort_order = "ASC"
    start = time.perf_counter()
    viewer.filter.get_filtered_entries(
        filter_text=TranslationStatus.ALL,
        filter_keyword="",
        match_mode="部分一致",
        case_sensitive=False,
        filter_status=None,
        filter_obsolete=False,
        update_filter=True,
        search_text="",
    )
    timings["sort_msgid"] = time.perf_counter() - start

    return timings


def main():
    profiler = cProfile.Profile()
    profiler.enable()
    timings = run_profile()
    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.sort_stats("cumulative")
    prof_path = PROFILE_DIR / "entry_operations.prof"
    stats.dump_stats(str(prof_path))

    txt_path = PROFILE_DIR / "entry_operations.txt"
    with open(txt_path, "w") as f:
        stats.stream = f
        stats.print_stats(20)

    for k, v in timings.items():
        print(f"{k}: {v*1000:.2f} ms")
    print(f"Profile saved to {prof_path}")
    print(f"Text stats saved to {txt_path}")


if __name__ == "__main__":
    main()
