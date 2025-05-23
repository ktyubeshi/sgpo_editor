import asyncio
import cProfile
import logging
import pstats
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sgpo_editor.core.po_factory import POLibraryType
from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.models.entry import EntryModel

# 1. Imports and Setup
logging.basicConfig(level=logging.WARNING)

PROFILE_RESULTS_DIR = Path(__file__).parent / "profile_results"
# Use a larger PO file for performance profiling
SAMPLE_PO_PATH = Path(__file__).parent / "sample_data" / "sample_10000.po"


# 2. Helper Function `run_profile`
def run_profile(profile_name: str, func_to_call, *args, top_n: int = 20) -> pstats.Stats:
    """
    Runs the profiler on a given function and saves/prints the stats.
    """
    PROFILE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    profiler = cProfile.Profile()
    profiler.enable()

    result = func_to_call(*args)

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')

    print(f"\n--- Profiling results for: {profile_name} ---")
    stats.print_stats(top_n)

    profile_file_path = PROFILE_RESULTS_DIR / f"{profile_name}.prof"
    stats.dump_stats(str(profile_file_path))
    print(f"Full profile stats saved to: {profile_file_path}")

    profile_txt_path = PROFILE_RESULTS_DIR / f"{profile_name}.txt"
    with open(profile_txt_path, "w") as f:
        # Redirect stdout to the file
        old_stdout = pstats.sys.stdout
        pstats.sys.stdout = f
        try:
            stats.print_stats(30)
        finally:
            # Restore stdout
            pstats.sys.stdout = old_stdout
    print(f"Top 30 text stats saved to: {profile_txt_path}")

    return stats, result # Return result as well for functions that produce data


# 3. Profiling Functions
def perform_load_and_model_creation(po_path: Path, lib_type: POLibraryType):
    """
    Profiles ViewerPOFile.load() and subsequent EntryModel creation.
    """
    viewer = ViewerPOFile(library_type=lib_type)
    asyncio.run(viewer.load(str(po_path)))
    # EntryModels are created during load by ViewerPOFile
    return viewer


def perform_model_instantiation_from_dicts(entries_data: List[Dict[str, Any]]):
    """
    Profiles EntryModel.from_dict() instantiation.
    """
    models = [EntryModel.from_dict(data) for data in entries_data]
    return models


def perform_model_to_dict_conversion(entry_models: List[EntryModel]):
    """
    Profiles EntryModel.to_dict() conversion.
    """
    dicts = [model.to_dict() for model in entry_models]
    return dicts


def perform_model_property_access(entry_models: List[EntryModel]):
    """
    Profiles accessing various properties of EntryModel.
    """
    for model in entry_models:
        _ = model.fuzzy
        _ = model.is_translated
        _ = model.is_untranslated
        _ = model.score
        _ = model.overall_quality_score
        _ = model.evaluation_state
    return entry_models # Return to ensure work is done


def perform_cached_retrieval(viewer: ViewerPOFile, keys: List[str]):
    """
    Profiles ViewerPOFile.get_entry_by_key() for cache performance.
    """
    entries = [viewer.get_entry_by_key(key) for key in keys]
    return entries


# 4. Main Execution Block
if __name__ == "__main__":
    PROFILE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not SAMPLE_PO_PATH.exists():
        logging.error(f"Sample PO file not found: {SAMPLE_PO_PATH}. Please ensure it exists.")
        exit(1)

    print(f"Using sample PO file: {SAMPLE_PO_PATH}")

    # Data Preparation
    print("Preparing data for profiling...")
    initial_viewer_polib = ViewerPOFile(library_type=POLibraryType.POLIB)
    try:
        asyncio.run(initial_viewer_polib.load(str(SAMPLE_PO_PATH)))
    except Exception as e:
        logging.error(f"Failed to load sample PO file with POLIB: {e}")
        # Fallback: Try with SGPO if POLIB fails, or exit.
        # For now, let's assume if POLIB fails, SGPO might also have issues with the same file,
        # or the file is fundamentally problematic.
        print("Attempting to load with SGPO as a fallback for data preparation...")
        initial_viewer_sgpo = ViewerPOFile(library_type=POLibraryType.SGPO)
        try:
            asyncio.run(initial_viewer_sgpo.load(str(SAMPLE_PO_PATH)))
            entry_models_list = initial_viewer_sgpo.get_all_entries()
            if not entry_models_list: # Check after sgpo load
                 print("Warning: SGPO loaded, but the sample PO file might be empty or invalid. Profiling results may not be meaningful.")
                 # We can decide to exit or proceed with empty lists
        except Exception as e_sgpo:
            logging.error(f"Failed to load sample PO file with SGPO as well: {e_sgpo}")
            print("Exiting due to failure in preparing initial data.")
            exit(1)
    else:
        entry_models_list = initial_viewer_polib.get_all_entries()

    if not entry_models_list:
        print("Warning: The sample PO file resulted in an empty list of models. Profiling results may not be meaningful.")
        # Initialize with empty lists to avoid crashes in subsequent steps, though results will be trivial.
        entry_dicts_list = []
        entry_keys_list = []
    else:
        entry_dicts_list = [model.to_dict() for model in entry_models_list]
        entry_keys_list = [model.key for model in entry_models_list if model.key is not None] # Ensure key is not None

    print(f"Prepared {len(entry_models_list)} models for profiling.")

    # Run Profiling Scenarios
    if entry_models_list: # Only run these if we have data
        print("\nStarting profiling scenarios...")

        run_profile("profile_load_polib", perform_load_and_model_creation, SAMPLE_PO_PATH, POLibraryType.POLIB)
        run_profile("profile_load_sgpo", perform_load_and_model_creation, SAMPLE_PO_PATH, POLibraryType.SGPO)

        if entry_dicts_list:
            run_profile("profile_instantiation_from_dicts", perform_model_instantiation_from_dicts, entry_dicts_list)
        else:
            print("Skipping 'profile_instantiation_from_dicts' as no entry dicts were prepared.")

        run_profile("profile_to_dict_conversion", perform_model_to_dict_conversion, entry_models_list)
        run_profile("profile_property_access", perform_model_property_access, entry_models_list)

        # Cached Retrieval Scenario
        print("\nProfiling cached retrieval...")
        if entry_keys_list: # Only proceed if there are keys to retrieve
            print("Setting up ViewerPOFile for cache retrieval test (POLIB)...")
            cache_test_viewer = ViewerPOFile(library_type=POLibraryType.POLIB)
            try:
                # Load the PO file to populate the cache. This load is NOT part of the timed profile for retrieval.
                asyncio.run(cache_test_viewer.load(str(SAMPLE_PO_PATH)))
                if cache_test_viewer.get_all_entries(): # Check if loading was successful
                    run_profile("cached_retrieval_first_pass", perform_cached_retrieval, cache_test_viewer, entry_keys_list)
                    run_profile("cached_retrieval_second_pass", perform_cached_retrieval, cache_test_viewer, entry_keys_list)
                else:
                    print("Skipping cached retrieval tests: ViewerPOFile loaded but reported no entries.")
            except Exception as e:
                logging.error(f"Failed to setup ViewerPOFile for cache retrieval test: {e}")
                print("Skipping cached retrieval tests due to setup error.")
        else:
            print("Skipping cached retrieval tests as no entry keys were prepared (sample file might be empty or load failed).")

    else: # If entry_models_list was empty from the start
        print("Skipping main profiling scenarios as no models were loaded from the sample PO file during initial data preparation.")
        # Still attempt load profiles as they are independent of successful model creation count
        print("\nAttempting to run load profiles independently...")
        run_profile("profile_load_polib_independent", perform_load_and_model_creation, SAMPLE_PO_PATH, POLibraryType.POLIB)
        run_profile("profile_load_sgpo_independent", perform_load_and_model_creation, SAMPLE_PO_PATH, POLibraryType.SGPO)


    print("\nProfiling complete.")
    print(f"All results saved in: {PROFILE_RESULTS_DIR}")
