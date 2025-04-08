# コーディング指示: SGPOエディタ GUIと機能改善 (エージェント1)

## 役割と目標

あなたはSGPOエディタの **GUIコンポーネントと特定機能（LLM評価、POフォーマットエディタなど）の改善** を担当します。目標は、提供されたToDoリスト (`ToDo1.md`) に基づいてコードを修正・実装し、アプリケーションのGUIにおける安定性、機能性、保守性を向上させることです。

## 背景情報

* **プロジェクト概要:** gettext POファイル (.po) を編集・管理するためのPySide6ベースのGUIアプリケーションです。翻訳者やローカライゼーションエンジニア向け。
* **アーキテクチャ:** MVCパターンを採用。GUI (`src/sgpo_editor/gui/`)、コアロジック (`src/sgpo_editor/core/`)、データモデル (`src/sgpo_editor/models/`) が分離されています。ファサードパターン (`src/sgpo_editor/gui/facades/`) も導入されています。
* **技術スタック:** Python 3.8+, PySide6, sgpo, pytest, uv。
* **主要コンポーネント:**
    * **GUI:** `MainWindow`, `TableManager`, `EntryEditor`, `SearchWidget`, `POFormatEditor`, `EvaluationDialog`, `MetadataPanel` など。
    * **Facades:** `EntryListFacade`, `EntryEditorFacade` がGUIとコア間のインターフェースを提供。
    * **Models:** `EntryModel` (Pydantic) がPOエントリデータを表現。評価スコアやコメントも含む。
    * **Core:** `ViewerPOFile` 派生クラス群がPOデータ操作（キャッシュ、DBアクセス含む）を担当（エージェント2が主に担当）。
* **現在の課題:**
    * POフォーマットエディタのバグ。
    * LLM評価機能の非同期化。
    * 一部の編集操作（コメント、スコア等）のDBへの即時反映。
    * GUIコンポーネント (`TableManager`, `EventHandler`) 内のキャッシュとコアのキャッシュ管理 (`EntryCacheManager`) との連携・役割分担の明確化。
    * UI/UXの改善点（列表示、メタデータ編集など）。

## 参照すべきファイル

* **必須:** `ToDo1.md` (あなたの担当タスクリスト)
* **コード:** 主に `src/sgpo_editor/gui/` 配下のファイル、特に `widgets/`, `facades/`, `main_window.py`。
* **ドキュメント:** 必要に応じて `_doc/` 配下の設計書や課題メモを参照してください。

## 具体的な指示

1.  `ToDo1.md` に記載されている **P1 (最優先) タスク** から着手してください。
    * `POFormatEditor` のバグ修正。
    * `MainWindow._on_entry_updated` での選択状態維持の確認・修正。
2.  次に **P2 (高優先度) タスク** に進んでください。
    * `EvaluationDialog` の非同期化、UI改善、エラーハンドリング強化。
    * `TableManager` の列表示/非表示機能とScore列表示/ソートの検証・修正。
    * GUIコンポーネント (`TableManager`, `EventHandler`, `EntryListFacade`, `POFormatEditor`) における **キャッシュ利用の役割明確化と整理**。コアの `EntryCacheManager` との連携を考慮し、不要な内部キャッシュは削除または統合してください。関連するdocstringも更新してください。
    * `review_widgets.py` における **DB即時反映** の実装・確認。
3.  P1, P2完了後、**P3, P4タスク** に着手してください。
    * `PreviewWidget` のエスケープ処理改善。
    * `EventHandler` の役割見直し。
    * メタデータ関連UIの改善など。
4.  **テスト:** 担当範囲のコード変更に伴い、関連する **GUIテスト (`tests/gui/`)** を修正・追加し、パスすることを確認してください。`ToDo1.md` の「テスト修正」セクションも参照してください。

## 注意点

* コードの変更は `ToDo1.md` に記載されたタスク範囲に留めてください。
* 既存のコードスタイルや設計原則（MVC、ファサード）に従ってください。
* 変更箇所には適切なコメントを追加し、関連するdocstringも更新してください。
* 他のコンポーネントへの影響を考慮し、特にファサードクラスのインターフェース変更は慎重に行ってください。エージェント2と共有するコアコンポーネント (`ViewerPOFile` など) の利用方法に変更が必要な場合は、インターフェースの変更は避け、利用側の調整で対応してください。
* すべての修正・実装後に、関連するテストを実行し、パスすることを確認してください (`uv run pytest ...`)。

## 成果物

* 修正・追加された `src/sgpo_editor/gui/` 配下のPythonコードファイル。
* 修正・追加された `tests/gui/` 配下のテストコードファイル。
* 必要に応じて更新されたdocstring。

# SGPOエディタ ToDoリスト (エージェント1: GUIと機能改善)

## P1: 最優先タスク (バグ修正・安定性)

* **`src/sgpo_editor/gui/widgets/po_format_editor.py`** ([source: 2382])
    * [x] `_on_apply_clicked` ([source: 2408]) 内でのエラーを修正し、正しくエントリが更新 (`ViewerPOFile.update_entry` [source: 2417] 呼び出し) されるようにする。関連するデータ取得 (`get_entry_by_key`, `get_filtered_entries`) の動作も確認する。
* **`src/sgpo_editor/gui/main_window.py`** ([source: 3071])
    * [x] `_on_entry_updated` ([source: 3108]) 内で `entry_list_facade.update_table()` ([source: 2286]) を呼び出す際、更新後にエントリの選択状態が正しく維持されるか確認し、必要であれば `EntryListFacade.select_entry_by_key` ([source: 2293]) を使用して選択状態を復元するロジックを修正・強化する。

## P2: 高優先度タスク (設計改善・主要機能)

* **`src/sgpo_editor/gui/evaluation_dialog.py`** ([source: 1780])
    * [x] LLM評価実行メソッド `_evaluate` ([source: 1711]) を非同期処理（`QThread` または `QRunnable`）に変更し、UIフリーズを防止する。進捗表示 (`QProgressBar` [source: 1691]) と連携させる。
    * [x] `_set_api_keys` ([source: 1705]) 実行前にAPIキーが設定されているかチェックし、設定されていなければユーザーに通知するUIフィードバックを追加する。
    * [x] `_load_api_keys` ([source: 1706]) / `_save_api_keys` ([source: 1708]) でのエラーハンドリングを強化し、失敗した場合にユーザーにエラーメッセージを表示する。
* **`src/sgpo_editor/gui/table_manager.py`** ([source: 2758])
    * [x] `toggle_column_visibility` ([source: 2792]) がUIメニュー (`UIManager._setup_column_visibility_menu` [source: 2934]) と確実に同期し、状態がアプリケーション終了/再起動後も保存・復元されるか再検証する。
    * [x] Score列の表示・ソート機能が正しく動作するか検証する (`_sort_entries_by_score` [source: 2820], `_update_table_contents` [source: 2829])。`EntryModel.score` ([source: 2853]) と連携しているか確認する。
    * [x] **【キャッシュ改善】**: 内部キャッシュ `_entry_cache` ([source: 2760]) の役割を明確化し、`EntryCacheManager` ([source: 1466]) との連携方法・役割分担をdocstringに記述する。不要であれば削除または統合を検討する。
* **`src/sgpo_editor/gui/event_handler.py`** ([source: 2720])
    * [x] **【キャッシュ改善】**: 内部キャッシュ `_entry_cache` ([source: 2723]) 及びプリフェッチ `_prefetch_visible_entries` ([source: 2736])、詳細表示更新 `_update_detail_view` ([source: 2729]) におけるキャッシュ利用ロジックと `EntryCacheManager` ([source: 1466]) との連携方法・役割分担をdocstringに記述する。
* **`src/sgpo_editor/gui/facades/entry_list_facade.py`** ([source: 2284])
    * [x] **【キャッシュ改善】**: `update_table` ([source: 2286]) メソッド内での `ViewerPOFile.get_filtered_entries` ([source: 1613]) の呼び出し方が、キャッシュ状態 (`_force_filter_update` [source: 1471]) を適切に考慮しているか確認し、役割をdocstringに記述する。
* **`src/sgpo_editor/gui/widgets/po_format_editor.py`** ([source: 2382])
    * [x] **【キャッシュ改善】**: `_on_apply_clicked` ([source: 2408]) 内での `update_entry` ([source: 2417]) 呼び出しが、`ViewerPOFile` のキャッシュ更新/無効化とどのように連携するか、その役割をdocstringに記述する。
* **`src/sgpo_editor/gui/widgets/review_widgets.py`**
    * [x] `QualityScoreWidget`: `_on_apply_score` ([source: 2354]), `_on_add_category_score` ([source: 2356]), `_on_reset_scores` ([source: 2359]) でのDB更新 (`InMemoryEntryStore.update_entry_field` または `update_entry_review_data`) が正しく実装されているか確認する。
    * [x] `CheckResultWidget`: `_on_add_result` ([source: 2372]), `_on_remove_result` ([source: 2374]), `_on_clear_results` ([source: 2376]) 内で、対応するDB更新処理 (`InMemoryEntryStore.add_check_result`, `remove_check_result` など) を実装する。

## P3: 中優先度タスク (コード品質・保守性)

* **`src/sgpo_editor/gui/widgets/preview_widget.py`** ([source: 2438])
    * [x] `_process_escape_sequences` ([source: 2442]) をリファクタリングし、標準ライブラリ (`html.unescape` など) やQtの機能を活用して実装を改善する。
* **`src/sgpo_editor/gui/event_handler.py`** ([source: 2720])
    * [x] ファサード (`EntryEditorFacade`, `EntryListFacade`) 導入後の `EventHandler` の役割を再評価し、重複する処理があればファサードに統合し、`EventHandler` から削除またはリファクタリングする。
* **`src/sgpo_editor/gui/facades/`** ([source: 1670], [source: 2284])
    * [x] `EntryEditorFacade` と `EntryListFacade` の責務が適切か再評価し、必要であればリファクタリングする。

## P4: 低優先度タスク (将来的な改善)

* **`src/sgpo_editor/gui/main_window.py`** ([source: 3071])
    * [x] `_show_translation_evaluate_dialog` ([source: 3133]) 内のレガシーダイアログ (`TranslationEvaluateDialog`) 使用部分の必要性を検討し、不要であれば削除する。
    * [x] `setup_toolbar` ([source: 2945]) 内のアクションの表示/非表示ロジックを、機能の有効/無効状態と連動させるように改善する。
* **`src/sgpo_editor/gui/metadata_dialog.py`** ([source: 1980]) & **`src/sgpo_editor/gui/metadata_panel.py`** ([source: 2018])
    * [x] メタデータ編集/表示機能のUI/UXを改善する（例: 型に応じた入力ウィジェット、リスト/辞書のインライン編集）。
* **テスト (`tests/gui/`)**
    * [x] `pytest-qt` を活用したGUI操作（ボタンクリック、テキスト入力、コンボボックス選択など）のテストを追加する。

## テスト修正 (GUI関連)

* **`tests/gui/table/test_table_score_display.py`**
* **`tests/gui/table/test_table_status_display.py::test_table_status_column_display`**
* **`tests/gui/table/test_table_update_issue.py`**
* **`tests/gui/test_entry_editor/test_entry_editor_state.py::test_entry_editor_state_apply_changes`**
* **`tests/gui/test_keyword_filter/test_filter_reset.py`**
* **`tests/gui/test_keyword_filter/test_filter_reset_basic.py`**
* **`tests/gui/test_keyword_filter/test_main_window_filter.py`**
