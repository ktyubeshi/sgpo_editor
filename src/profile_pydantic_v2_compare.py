#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pydantic V2 パフォーマンス比較テストスクリプト (検証あり vs model_construct)

目的:
- Pydantic V2 環境下で、データ検証を伴うモデル生成と model_construct() による
  検証スキップ生成のパフォーマンスを比較する。
- 大量エントリ（約1万件）を扱った際の主要操作（フィルタリング、取得）における
  モデル生成コストの影響を確認する。

テストする操作とアプローチ:
1.  データ準備 (DBロード)
2.  フィルタリング
    - アプローチ1: DB結果 -> dict -> EntryModel.model_validate(dict)
    - アプローチ2: DB結果 -> dict -> EntryModel.model_construct(**dict)
3.  単一エントリ取得
    - アプローチ1: DB結果 -> dict -> EntryModel.model_validate(dict)
    - アプローチ2: DB結果 -> dict -> EntryModel.model_construct(**dict)
4.  複数エントリ取得
    - アプローチ1: DB結果 -> List[dict] -> [EntryModel.model_validate(d) ...]
    - アプローチ2: DB結果 -> List[dict] -> [EntryModel.model_construct(**d) ...]
"""

import time
import random
import cProfile
import pstats
import io
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, cast, Set
import gc

# --- sgpo_editor から必要なクラスをインポート ---
try:
    from sgpo_editor.models.database import InMemoryEntryStore
    from sgpo_editor.core.database_accessor import DatabaseAccessor
    from sgpo_editor.core.cache_manager import EntryCacheManager
    from sgpo_editor.core.viewer_po_file import ViewerPOFile  # ViewerPOFileを直接使用
    from sgpo_editor.models.entry import EntryModel
    from sgpo_editor.core.constants import TranslationStatus
    from sgpo_editor.types import (
        EntryDict,
        EntryDictList,
        FlagConditions,
        FilterSettings,
    )
    from sgpo_editor.models.evaluation_state import EvaluationState

except ImportError as e:
    print(f"Import Error: {e}")
    print("Please run this script from the project root directory")
    print("or ensure the 'src' directory is in your PYTHONPATH.")
    exit(1)
# --- ここまで ---

# --- 設定 ---
NUM_ENTRIES = 10000
NUM_RUNS_GET = 100  # 単一取得の繰り返し回数
NUM_MULTI_GET = 100  # 複数取得の件数
KEYWORD_TO_SEARCH = "pydantic_perf"  # 新しいキーワード
PERCENT_WITH_KEYWORD = 10
PERCENT_FUZZY = 15
PERCENT_UNTRANSLATED = 20

PROFILE_OUTPUT_DIR = Path(__file__).parent / "performance_profiles_v2_compare"
PROFILE_OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PydanticPerfTest")
# --- ここまで ---


# --- 関数定義 ---
def create_mock_entry_dicts(num_entries: int) -> EntryDictList:
    """テスト用のEntry辞書リストを作成する (変更なし)"""
    logger.info(f"{num_entries} 件のモックエントリを生成中...")
    entries = []
    keyword_count = 0
    fuzzy_count = 0
    untranslated_count = 0
    translated_count = 0

    for i in range(num_entries):
        key = f"key_{i}"
        position = i
        fuzzy = random.randint(1, 100) <= PERCENT_FUZZY
        is_translated = random.randint(1, 100) > PERCENT_UNTRANSLATED
        msgstr = f"Translated text {i}" if is_translated and not fuzzy else ""
        flags = ["fuzzy"] if fuzzy and is_translated else []

        msgid = f"Source text {i} for testing."
        if random.randint(1, 100) <= PERCENT_WITH_KEYWORD:
            msgid += f" {KEYWORD_TO_SEARCH}"
            keyword_count += 1

        if fuzzy:
            fuzzy_count += 1
        if not msgstr and not fuzzy:
            untranslated_count += 1
        if msgstr and not fuzzy:
            translated_count += 1

        entry_dict: EntryDict = {
            "key": key,
            "msgid": msgid,
            "msgstr": msgstr,
            "msgctxt": f"context_{i % 10}",
            "obsolete": False,
            "fuzzy": fuzzy,  # DB用にブール値で保持
            "flags": flags,
            "position": position,
            "references": [f"file_{i % 5}.py:{position + 10}"],
            "comment": f"Comment for entry {i}" if i % 7 == 0 else None,
            "tcomment": f"Translator comment {i}" if i % 11 == 0 else None,
            "id": i + 1,
            "previous_msgid": None,
            "previous_msgid_plural": None,
            "previous_msgctxt": None,
            "occurrences": [],
            "review_data": {},
            # EntryModelが期待する可能性のあるフィールドを追加（Optionalなので無くても良い）
            "metadata": {},
            "overall_quality_score": None,
            "category_quality_scores": {},
            "check_results": [],
            "score": None,
            "review_comments": [],
            "metric_scores": {},
            "evaluation_state": EvaluationState.NOT_EVALUATED,  # デフォルト値
        }
        entries.append(entry_dict)

    logger.info("モックエントリ生成完了:")
    logger.info(f"  - '{KEYWORD_TO_SEARCH}' を含む: {keyword_count} 件")
    logger.info(f"  - Fuzzy: {fuzzy_count} 件")
    logger.info(f"  - 未翻訳: {untranslated_count} 件")
    logger.info(f"  - 翻訳済み(非Fuzzy): {translated_count} 件")
    return cast(EntryDictList, entries)


def setup_environment() -> Dict[str, Any]:
    """テスト環境をセットアップし、DBにデータをロードする"""
    logger.info("テスト環境のセットアップ開始...")
    db_store = InMemoryEntryStore()
    db_accessor = DatabaseAccessor(db_store)

    mock_data = create_mock_entry_dicts(NUM_ENTRIES)

    logger.info("InMemoryEntryStore へのデータ読み込み開始...")
    start_time = time.perf_counter()
    db_accessor.add_entries_bulk(mock_data)  # ここでは辞書を直接DBにロード
    load_time = time.perf_counter() - start_time
    logger.info(f"データ読み込み完了 ({load_time:.4f} 秒)")

    return {
        "db_accessor": db_accessor,
        "mock_data_keys": [d["key"] for d in mock_data],
        "load_time": load_time,
    }


def time_operation(description: str, func, *args, **kwargs) -> float:
    """指定された関数の実行時間を計測し、ログ出力するヘルパー"""
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    duration = time.perf_counter() - start_time
    logger.info(f"{description}: {duration:.6f} 秒")
    # オプション: 結果のサイズなどもログ出力
    if isinstance(result, list):
        logger.info(f"  -> 結果件数: {len(result)}")
    elif isinstance(result, dict):
        logger.info(f"  -> 結果件数: {len(result)}")
    return duration


# --- ここまで ---


# --- テスト関数 ---
def test_filtering(env: Dict[str, Any]):
    """フィルタリング操作のパフォーマンスをテスト"""
    logger.info(
        "\n--- フィルタリング パフォーマンステスト (model_validate vs model_construct) ---"
    )
    db_accessor: DatabaseAccessor = env["db_accessor"]

    filter_kw_status_set: Set[str] = {
        TranslationStatus.TRANSLATED,
        TranslationStatus.FUZZY,
    }
    filter_kw_fields = ["msgid", "msgstr"]

    # --- アプローチ1: model_validate (Pydanticの通常の検証・変換) ---
    logger.info("[アプローチ1: model_validate]")

    def filter_with_validate(search_text: Optional[str], status: Optional[Set[str]]):
        # DBから辞書のリストを取得
        entry_dicts = db_accessor.advanced_search(
            search_text=search_text,
            search_fields=filter_kw_fields,
            translation_status=status,
        )
        # EntryModelに変換 (検証あり)
        # Pydantic V2 では model_validate が推奨されるが、from_dictも内部で呼ぶ
        # ここではより明示的に model_validate を使う（なければ from_dict）
        if hasattr(EntryModel, "model_validate"):
            models = [EntryModel.model_validate(d) for d in entry_dicts]
        else:
            models = [EntryModel.from_dict(d) for d in entry_dicts]  # V1互換
        return models

    time_validate_kw = time_operation(
        "キーワードあり", filter_with_validate, KEYWORD_TO_SEARCH, filter_kw_status_set
    )
    time_validate_no_kw = time_operation(
        "キーワードなし", filter_with_validate, None, filter_kw_status_set
    )

    # --- アプローチ2: model_construct (検証スキップ) ---
    logger.info("\n[アプローチ2: model_construct]")

    def filter_with_construct(search_text: Optional[str], status: Optional[Set[str]]):
        # DBから辞書のリストを取得
        entry_dicts = db_accessor.advanced_search(
            search_text=search_text,
            search_fields=filter_kw_fields,
            translation_status=status,
        )
        # EntryModelに変換 (検証スキップ)
        models = [EntryModel.model_construct(**d) for d in entry_dicts]
        return models

    time_construct_kw = time_operation(
        "キーワードあり", filter_with_construct, KEYWORD_TO_SEARCH, filter_kw_status_set
    )
    time_construct_no_kw = time_operation(
        "キーワードなし", filter_with_construct, None, filter_kw_status_set
    )

    # --- 結果サマリ ---
    logger.info("\n--- フィルタリング 結果サマリ ---")
    logger.info(
        f"キーワードあり: model_validate = {time_validate_kw:.6f} 秒, model_construct = {time_construct_kw:.6f} 秒"
    )
    logger.info(
        f"キーワードなし: model_validate = {time_validate_no_kw:.6f} 秒, model_construct = {time_construct_no_kw:.6f} 秒"
    )


def test_get_single_entry(env: Dict[str, Any]):
    """単一エントリ取得のパフォーマンスをテスト"""
    logger.info(
        "\n--- 単一エントリ取得 パフォーマンステスト (model_validate vs model_construct) ---"
    )
    db_accessor: DatabaseAccessor = env["db_accessor"]
    keys: List[str] = env["mock_data_keys"]
    test_keys_single = random.sample(keys, NUM_RUNS_GET)

    # --- アプローチ1: model_validate ---
    logger.info("[アプローチ1: model_validate]")
    validate_times = []
    for key in test_keys_single:
        start = time.perf_counter()
        entry_dict = db_accessor.get_entry_by_key(key)
        if entry_dict:
            if hasattr(EntryModel, "model_validate"):
                _ = EntryModel.model_validate(entry_dict)
            else:
                _ = EntryModel.from_dict(entry_dict)
        validate_times.append(time.perf_counter() - start)
    validate_avg_time = sum(validate_times) / NUM_RUNS_GET
    logger.info(f"model_validate (平均): {validate_avg_time * 1000:.6f} ミリ秒")

    # --- アプローチ2: model_construct ---
    logger.info("\n[アプローチ2: model_construct]")
    construct_times = []
    for key in test_keys_single:
        start = time.perf_counter()
        entry_dict = db_accessor.get_entry_by_key(key)
        if entry_dict:
            _ = EntryModel.model_construct(**entry_dict)
        construct_times.append(time.perf_counter() - start)
    construct_avg_time = sum(construct_times) / NUM_RUNS_GET
    logger.info(f"model_construct (平均): {construct_avg_time * 1000:.6f} ミリ秒")

    # --- 結果サマリ ---
    logger.info("\n--- 単一取得 結果サマリ ---")
    logger.info(
        f"平均取得時間: model_validate = {validate_avg_time * 1000:.6f} ミリ秒, model_construct = {construct_avg_time * 1000:.6f} ミリ秒"
    )


def test_get_multiple_entries(env: Dict[str, Any]):
    """複数エントリ取得のパフォーマンスをテスト"""
    logger.info(
        "\n--- 複数エントリ取得 パフォーマンステスト (model_validate vs model_construct) ---"
    )
    db_accessor: DatabaseAccessor = env["db_accessor"]
    keys: List[str] = env["mock_data_keys"]
    test_keys_multi = random.sample(keys, NUM_MULTI_GET)

    # --- アプローチ1: model_validate ---
    logger.info("[アプローチ1: model_validate]")

    def get_multi_with_validate(keys_list: List[str]):
        entry_dicts_map = db_accessor.get_entries_by_keys(keys_list)
        if hasattr(EntryModel, "model_validate"):
            models = [EntryModel.model_validate(d) for d in entry_dicts_map.values()]
        else:
            models = [EntryModel.from_dict(d) for d in entry_dicts_map.values()]
        return models

    time_validate = time_operation(
        f"{NUM_MULTI_GET}件取得", get_multi_with_validate, test_keys_multi
    )

    # --- アプローチ2: model_construct ---
    logger.info("\n[アプローチ2: model_construct]")

    def get_multi_with_construct(keys_list: List[str]):
        entry_dicts_map = db_accessor.get_entries_by_keys(keys_list)
        models = [EntryModel.model_construct(**d) for d in entry_dicts_map.values()]
        return models

    time_construct = time_operation(
        f"{NUM_MULTI_GET}件取得", get_multi_with_construct, test_keys_multi
    )

    # --- 結果サマリ ---
    logger.info("\n--- 複数取得 結果サマリ ---")
    logger.info(
        f"{NUM_MULTI_GET}件取得時間: model_validate = {time_validate:.6f} 秒, model_construct = {time_construct:.6f} 秒"
    )


# --- メイン実行 ---
if __name__ == "__main__":
    logger.info(
        f"===== Pydantic V2 パフォーマンス比較テスト開始 (エントリ数: {NUM_ENTRIES}) ====="
    )

    profiler = cProfile.Profile()
    profiler.enable()

    # 環境セットアップ（DBへのデータロードのみ）
    environment = setup_environment()

    # 各テスト実行
    test_filtering(environment)
    test_get_single_entry(environment)
    test_get_multiple_entries(environment)

    profiler.disable()
    logger.info("===== パフォーマンス比較テスト完了 =====")

    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    ps.print_stats(40)  # ボトルネック特定のため表示件数を増やす

    profile_output_file = (
        PROFILE_OUTPUT_DIR / f"pydantic_v2_compare_{NUM_ENTRIES}_entries.prof"
    )
    profiler.dump_stats(profile_output_file)
    logger.info(f"\nプロファイル結果:\n{s.getvalue()}")
    logger.info(
        f"詳細なプロファイルデータは '{profile_output_file}' に保存されました。"
    )
    logger.info("snakeviz などで可視化できます: snakeviz {profile_output_file}")

    logger.info("テスト完了後GC実行...")
    gc.collect()
    logger.info("GC完了")
