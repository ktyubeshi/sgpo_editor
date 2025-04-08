# SGPOエディタ ToDoリスト

このドキュメントは、SGPOエディタプロジェクトの今後の開発タスクを管理します。

## P1: 最優先タスク (バグ修正・安定性)

* **`src/sgpo_editor/gui/widgets/po_format_editor.py`**
    * [x] `_on_apply_clicked` メソッドで発生するエラー（`_doc/issue/po_format_window/適用に失敗する.md`参照）の修正。
        * 原因調査: `ViewerPOFile.get_entry_by_key` でエントリが見つからない、または `ViewerPOFile.update_entry` の呼び出しに問題がある可能性。`get_filtered_entries` を使用した代替検索ロジックの検証。
        * `ViewerPOFile.update_entry` の呼び出し前に、EntryModelオブジェクトが正しく構築・更新されているか確認。
        * データベース更新 (`Database.update_entry`) がトランザクション内で正しく実行され、コミットされているか確認。
    * [x] `_parse_po_format` の実装が、複数行のmsgid/msgstrや特殊文字を正しく処理できるか検証・修正。可能であれば `polib` や `sgpo` ライブラリの解析機能を利用する。

* **`src/sgpo_editor/core/viewer_po_file.py`**
    * [x] キャッシュ無効化ロジック (`_force_filter_update`) が `update_entry` 後に確実に機能し、`get_filtered_entries` で適切にリセットされるように修正・検証。
    * [x] `update_entry` 実行後、MainWindowの `_update_table` が呼び出され、キャッシュフラグがリセットされた状態で `get_filtered_entries` が実行されることを保証する仕組みの確認・修正。
    * [ ] 修正によって影響を受けた単体テストの修正。特に以下のテストに注目：
        * `tests/integration/test_viewer_po_file.py::test_get_entries`
        * `tests/integration/test_viewer_po_file.py::test_search_entries`
        * `tests/integration/test_viewer_po_file_filtered_entries.py` のテスト
        * `tests/integration/test_viewer_po_file_stats.py` のテスト
        * `tests/gui/keyword_filter/test_keyword_filter.py::TestKeywordFilter::test_filter_text_and_keyword_together`

* **`src/sgpo_editor/gui/main_window.py`**
    * [ ] `_on_entry_updated` メソッド内でテーブル更新 (`entry_list_facade.update_table()`) を呼び出す際に、`ViewerPOFile` のキャッシュ状態 (`_force_filter_update`) が適切に考慮されているか確認・修正。テーブル更新後に選択状態が正しく維持されるかも確認。

## P2: 高優先度タスク (設計改善・主要機能)

* **`src/sgpo_editor/core/viewer_po_file.py`**
    * [ ] **責務分割**: キャッシュ管理ロジックを新しいクラス (`EntryCacheManager` など) に分離するリファクタリング。
    * [ ] **責務分割**: データベースアクセスロジック (`db.get_entries` など) を新しいクラス (`DatabaseAccessor` など) に分離するリファクタリング。
    * [ ] ファイル読み込み (`load`) 処理の非同期化を検討し、UIの応答性を改善する。進捗表示も実装する。
    * [ ] **【キャッシュ改善】**: `_entry_cache` (完全なEntryModelオブジェクトのキャッシュ) と `_basic_info_cache` (基本情報のみのキャッシュ) の命名と役割を明確化する。
    * [ ] **【キャッシュ改善】**: `get_entry_by_key`, `get_entries_by_keys`, `get_entry_basic_info` におけるキャッシュの利用ロジックと命名を見直し、役割を明確にする。
    * [ ] **【キャッシュ改善】**: フィルタリング結果のキャッシュ (`_filtered_entries_cache`, `_filtered_entries_cache_key`, `_force_filter_update`) の命名と、`get_filtered_entries` における更新/無効化ロジックの役割を明確化する。
    * [ ] **【キャッシュ改善】**: `update_entry` 内でのキャッシュ更新 (`_entry_cache`, `_basic_info_cache`) およびキャッシュ無効化フラグ (`_force_filter_update`) 設定の役割をドキュメント化し、関連する命名を見直す。
    * [ ] **【キャッシュ改善】**: `_clear_cache`, `enable_cache`, `prefetch_entries` の命名とキャッシュ戦略における役割を明確化する。

* **`src/sgpo_editor/gui/evaluation_dialog.py` & `src/sgpo_editor/utils/llm_utils.py`**
    * [ ] LLM評価実行 (`_evaluate`) を非同期処理（例: `QThread`, `QRunnable`）に変更し、UIのフリーズを防止する。
    * [ ] APIキーが設定されていない場合のUIフィードバックを改善する。
    * [ ] `_load_api_keys`/`_save_api_keys` でのエラーハンドリングを強化する。

* **`src/sgpo_editor/gui/table_manager.py`**
    * [ ] 列の表示/非表示機能 (`toggle_column_visibility`) が確実に動作し、状態がUI (メニュー) と同期するように修正・検証。
    * [ ] Score列の表示・ソート機能の実装。`_sort_entries_by_score` の実装と `update_table_contents` でのスコア表示。
    * [ ] **【キャッシュ改善】**: 内部の `_entry_cache` と `ViewerPOFile` のキャッシュとの関係性・役割分担を明確にする。命名も見直す。

* **`src/sgpo_editor/models/entry.py`**
    * [ ] `score` プロパティの実装。LLM評価結果 (`overall_quality_score`) や手動設定スコアとの連携方法を定義する。

* **`src/sgpo_editor/models/database.py`**
    * [ ] クラス名を `Database` から `InMemoryEntryStore` など、役割が明確になる名前に変更する。
    * [ ] `get_entries` メソッドの `filter_text` 引数を削除し、`translation_status` と `flag_conditions` に完全に移行する (後方互換性を考慮しつつ)。
    * [ ] `get_entries` のORDER BY句で、ユーザーが指定した列名 (`sort_column`) の安全性を検証するロジックを追加（SQLインジェクション対策）。

* **`src/sgpo_editor/gui/event_handler.py`**
    * [ ] **【キャッシュ改善】**: 内部の `_entry_cache` や `_prefetch_visible_entries`, `_update_detail_view` でのキャッシュ利用ロジックと命名、役割を明確化する。`ViewerPOFile` のキャッシュとの連携方法を見直す。

* **`src/sgpo_editor/gui/facades/entry_list_facade.py`**
    * [ ] **【キャッシュ改善】**: テーブル更新 (`update_table`) における `ViewerPOFile.get_filtered_entries` の呼び出し方やキャッシュの利用について、役割を明確にする。

* **`src/sgpo_editor/gui/widgets/po_format_editor.py`**
    * [ ] **【キャッシュ改善】**: `_on_apply_clicked` 内での `get_filtered_entries` や `update_entry` の呼び出しが、`ViewerPOFile` のキャッシュ更新/無効化とどのように連携するか、命名と役割を明確にする。

## P3: 中優先度タスク (コード品質・保守性)

* **全体**
    * [ ] TypeAlias を活用して、複雑な型ヒント (`Dict[str, Any]` など) を分かりやすく定義する (`src/sgpo_editor/types.py` を作成または各モジュールで定義)。
    * [ ] logging のレベルとメッセージを見直し、デバッグや運用時の情報収集に役立つように調整する。
    * [ ] docstring の記述を充実させ、各クラス・メソッドの役割、引数、戻り値を明確にする。

* **`src/sgpo_editor/gui/widgets/preview_widget.py`**
    * [ ] `_process_escape_sequences` の実装を見直し、標準ライブラリ (`html.unescape` など) やQtの機能 (`QTextDocument.toHtml` / `setHtml`) を活用して簡潔化・堅牢化する。

* **`src/sgpo_editor/gui/event_handler.py`**
    * [ ] ファサードパターン導入後の `EventHandler` の役割を見直し、重複する処理があれば削除またはリファクタリングする。現状は互換性のために残されている可能性がある。

* **`src/sgpo_editor/po.py`**
    * [ ] `PoFile` クラスの役割と `ViewerPOFile` との関係性を見直し、不要であれば削除またはリファクタリングする。現状ではCLI用、または初期の実装の名残の可能性がある。

* **`src/sgpo_editor/gui/facades/`**
    * [ ] 各ファサードクラスの責務が適切か再評価し、必要であればリファクタリングする。

* **`src/sgpo_editor/models/database.py` & `src/sgpo_editor/models/evaluation_db.py`**
    * [ ] データベーススキーマ（特に `evaluation_db.py`）が `EntryModel` のフィールドと整合性が取れているか確認する。
    * [ ] トランザクション管理が適切に行われているか確認する。

## P4: 低優先度タスク (将来的な改善)

* **`src/sgpo_editor/gui/main_window.py`**
    * [ ] `_show_translation_evaluate_dialog` で `EvaluationDatabase` が利用できない場合のフォールバック処理（従来の `TranslationEvaluateDialog` を使う部分）の必要性を再検討する。
    * [ ] ツールバーアクションの表示/非表示ロジックを、機能の有効/無効状態と連動させるように改善する。

* **`src/sgpo_editor/gui/metadata_dialog.py` & `src/sgpo_editor/gui/metadata_panel.py`**
    * [ ] メタデータの編集/表示機能のUI/UXを改善する（例: 型に応じた入力ウィジェットの変更、リスト/辞書のインライン編集など）。

* **`_doc/`**
    * [ ] 今回のレビューとToDoリスト作成に合わせて、設計ドキュメント (`1_system_overview.md` 〜 `6_glossary.md`) の内容を最新化する。特にアーキテクチャ図やデータフロー図。
    * [ ] テスト計画 (`5_test_plan.md`) に、LLM評価機能やメタデータ機能に関するテスト項目を追加する。

* **テスト**
    * [ ] `pytest-qt` を活用したGUI操作のテストを追加し、手動テストへの依存を減らす。
    * [ ] パフォーマンステスト（大規模ファイル読み込み、フィルタリング速度）を定期的に実行する仕組みを検討する。

## テスト修正

* **テーブル関連のテスト修正**
    * [ ] `tests/gui/table/test_table_score_display.py` のテスト
    * [ ] `tests/gui/table/test_table_status_display.py::test_table_status_column_display`
    * [ ] `tests/gui/table/test_table_update_issue.py` のテスト
* **EntryEditorのテスト修正**
    * [ ] `tests/gui/test_entry_editor/test_entry_editor_state.py::test_entry_editor_state_apply_changes`
* **キーワードフィルター関連のテスト修正**
    * [ ] `tests/gui/test_keyword_filter/test_filter_reset.py` のテスト
    * [ ] `tests/gui/test_keyword_filter/test_filter_reset_basic.py` のテスト
    * [ ] `tests/gui/test_keyword_filter/test_main_window_filter.py` のテスト
* **Entryモデル関連のテスト修正**
    * [ ] `tests/models/entry/test_entry_list_integration.py::test_entry_list_status_display`
    * [ ] `tests/models/entry/test_entry_structure.py::TestEntryStructure` のテスト