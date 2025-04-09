# SGPO Editor 改善タスクリスト

コードの改善に向けたレビューと具体的なタスクリストを作成しました。

## 1. コード詳細分析

提供されたコードベースは、gettext POファイルを編集・管理するためのGUIアプリケーション「SGPO Editor」のようです。PythonとPySide6を主に使用し、POファイルの操作には `sgpo` ライブラリ（または `polib` との切り替え）を採用しています。

**主要コンポーネント:**

* **UI層 (sgpo_editor/gui):**
    * `MainWindow`: アプリケーションのメインウィンドウ。各コンポーネントを統合。 [source:3150]
    * `EntryEditor`: 選択されたPOエントリを編集するウィジェット。 [source:1437, 1449, 1725, 2513]
    * `TableManager`: POエントリの一覧を表示・管理するテーブル。 [source:1723, 2907]
    * `SearchWidget`: 検索・フィルタリング機能。 [source:1726, 1748, 2497]
    * `StatsWidget`: 翻訳統計情報の表示。 [source:1727, 1870]
    * `POFormatEditor`: PO形式テキストでの編集機能。 [source:16, 2556]
    * `PreviewWidget`: エスケープシーケンスやHTMLタグを解釈して表示するプレビュー機能。 [source:16, 2469]
    * `MetadataDialog`, `MetadataPanel`: メタデータ編集・表示機能。 [source:1872, 1911]
    * `EvaluationDialog`, `TranslationEvaluateDialog`: LLMによる翻訳品質評価機能。 [source:2221, 1922]
    * `facades`: `EntryEditorFacade`, `EntryListFacade` を提供し、複雑なUI操作をカプセル化。 [source:1583, 1859, 2359]
    * `EventHandler`: GUIイベント処理（一部ファサードと重複）。 [source:2616]
    * `FileHandler`: ファイル開閉・保存処理。 [source:2449]
    * `UIManager`: UIレイアウト、ドックウィジェット管理。 [source:2991]
* **コア層 (sgpo_editor/core):**
    * `ViewerPOFile`: POファイルの読み込み、表示、編集、フィルタリング、統計計算など多くの責務を持つ中心的なクラス。 [source:2322, 3032]
    * `ViewerPOFileRefactored`: `ViewerPOFile` のリファクタリング版。キャッシュとDBアクセスを分離する試み。 [source:1856]
    * `viewer_po_file_*.py`: `ViewerPOFile` の機能を分割したクラス群 (`Base`, `EntryRetriever`, `Filter`, `Updater`, `Stats`)。 [source:2322, 1523, 1837, 1561, 1543]
    * `EntryCacheManager`: エントリキャッシュ管理。 [source:14, 1856, 2154]
    * `DatabaseAccessor`: インメモリDBへのアクセス抽象化。 [source:14, 1856, 2180]
    * `po_factory.py`: `sgpo` と `polib` のファクトリ切り替え。 [source:14, 1466]
    * `po_interface.py`: `sgpo` と `polib` の共通インターフェース定義。 [source:14, 1473]
* **データモデル層 (sgpo_editor/models):**
    * `EntryModel`: PydanticベースのPOエントリモデル。メタデータや評価情報などの拡張フィールドを持つ。 [source:17, 1859, 2090, 2840]
    * `database.py`: インメモリSQLiteデータベース (`InMemoryEntryStore`)。フィルタリング等に利用。 [source:17, 2062, 2658]
    * `evaluation_db.py`: 翻訳評価データ永続化のためのSQLiteデータベース (`EvaluationDatabase`)。 [source:17, 1590]
    * `StatsModel`: 統計情報モデル。 [source:1871, 2314]
* **ユーティリティ層 (sgpo_editor/utils):**
    * `llm_utils.py`: LLM評価機能。 [source:1664]
    * `metadata_utils.py`: コメントからのメタデータ抽出・保存。 [source:1693]
* **その他:**
    * `sgpo`: POファイル操作ライブラリ (polibのラッパー？)。 [source:146, 1832, 2090]
    * `polib`: POファイル操作ライブラリ。 [source:1458, 1486]
    * `i18n`: 国際化対応。 [source:17, 1584]
    * `config.py`: アプリケーション設定管理。 [source:18, 1697]
    * ドキュメント (`_doc/`): 設計書、ガイドラインなど。 [source:3064]

**設計パターン:**

* **Model-View-Controller (MVC):** 基本的なアーキテクチャとして採用されているようです。 [source:2054-2058]
* **ファサード (Facade):** `EntryEditorFacade`, `EntryListFacade` でUI操作を単純化。 [source:1859, 2359]
* **オブザーバー (Observer):** PySide6のシグナル/スロット機構でイベント通知。
* **ファクトリ (Factory):** `po_factory.py` で `sgpo` / `polib` インスタンス生成を抽象化。 [source:1466]

**潜在的な問題点・改善点:**

* **`ViewerPOFile` の責務過多:** ファイル読み込み、キャッシュ、DB操作、フィルタリング、統計計算など多くの機能が集中しており、単一責任の原則に反しています。分割クラス群 (`viewer_po_file_*.py`) が存在するものの、`ViewerPOFile` 自体がまだ多くを使っている可能性があります。 [source:2060, 2074]
* **キャッシュ戦略の複雑性:** `ViewerPOFile` (または分割クラス), `EntryCacheManager`, `DatabaseAccessor`, `EventHandler` (`_entry_cache`), `TableManager` (`_entry_cache`) にキャッシュ機構が分散しており、全体像の把握と一貫性の維持が困難です。 [source:2154, 2618, 2921]
* **インメモリDBと永続DB:** `InMemoryEntryStore` と `EvaluationDatabase` の役割分担は設計書にあるものの、実際のコードでの連携や使い分けが不明瞭な箇所があるかもしれません。
* **EventHandlerとファサードの役割重複:** `EventHandler` が依然としてUIロジックの一部を担っており、ファサードとの役割分担が完全でない可能性があります。 [source:2617]
* **UIとロジックの結合度:** UIウィジェット (特に `MainWindow`, `EntryEditor`) がデータ操作ロジックを直接含んでいる箇所がある可能性があります。
* **テスト容易性:** `ViewerPOFile` のような巨大クラスは単体テストが困難です。モック化や依存性注入が十分でない可能性があります。GUIテストにおけるダイアログ表示のモック化など、ベストプラクティスが適用されているか確認が必要です（`_doc/test_guideline.md` [source:2082] に記載あり）。
* **型ヒント:** 一部の型ヒントが `Any` や `Optional` になっており、より厳密な型定義が望ましい箇所があります。
* **ドキュメントの追従:** コードの変更（特に`ViewerPOFile`の責務分割）がドキュメント (`_doc/`) に十分に反映されていない可能性があります。

## 2. あるべき姿のレビュー

現在のコードベースは機能が豊富ですが、保守性・拡張性の観点から以下の改善が望まれます。

* **責務の明確化と分離:**
    * `ViewerPOFile` の責務を完全に分割し、各クラス (`EntryCacheManager`, `DatabaseAccessor`, `ViewerPOFileFilter`, `ViewerPOFileUpdater`, `ViewerPOFileStats`) が独立して機能するようにします。`ViewerPOFileRefactored` を完成させ、古い `ViewerPOFile` を置き換えます。
    * キャッシュ管理は `EntryCacheManager` に一元化し、UI層（`EventHandler`, `TableManager`）の独自キャッシュは原則廃止、または `EntryCacheManager` と連携するようにします。
    * データベースアクセスは `DatabaseAccessor` に統一します。
    * UIイベント処理は `EventHandler` またはファサードに集約し、UIウィジェットクラスは表示と単純なイベント発行に専念させます。
* **ファサードパターンの一貫適用:**
    * UIコンポーネントからコアロジックやデータモデルへのアクセスは、原則としてファサード (`EntryEditorFacade`, `EntryListFacade` など) を経由するようにします。`EventHandler` のロジックも可能な限りファサードに移行します。
* **依存関係の整理:**
    * UI層 -> ファサード層 -> ビジネスロジック層 -> データアクセス層 のような明確な依存関係を構築します。循環参照を避けます。
* **キャッシュ戦略のシンプル化:**
    * `EntryCacheManager` を中心としたキャッシュ戦略を確立し、キャッシュのライフサイクル（生成、更新、無効化）を明確にします。`_force_filter_update` のようなフラグ管理はカプセル化します。
* **テスト容易性の向上:**
    * 依存性注入（DI）などを活用し、各コンポーネントをモックしやすくします。
    * GUIテストでは、`_doc/test_guideline.md` [source:2082] に記載されているダイアログのモック化などの手法を徹底します。
* **型安全性の強化:**
    * `Any` や `Optional` の使用を減らし、より具体的な型ヒントを使用します。`TypedDict` や `Protocol` の活用も検討します。 [source:2315]
* **ドキュメントの整備:**
    * アーキテクチャ、データフロー、キャッシュ戦略など、最新のコード設計に合わせてドキュメントを更新します。

## 3. 具体的な改善タスクリスト

**優先度:** 高 > 中 > 低

### 3.1. コア層のリファクタリング (優先度: 高)

* [✅] **`src/sgpo_editor/core/viewer_po_file.py` の廃止:**
    * `ViewerPOFile` クラス [source:3032] の機能を `ViewerPOFileRefactored` [source:1856] および各分割クラス (`viewer_po_file_*.py`) [source:2322, 1523, 1837, 1561, 1543] に完全に移行し、このファイルを削除します。
    * 依存箇所をリファクタリング後のクラス (`ViewerPOFileRefactored`) に修正します。
    * 優先度: **高**
* [✅] **`src/sgpo_editor/core/viewer_po_file_refactored.py` の完成:**
    * `ViewerPOFileStats` [source:1543] を継承していますが、他の分割クラス (`Base`, `EntryRetriever`, `Filter`, `Updater`) との統合または委譲関係を明確にし、`ViewerPOFile` の完全な代替となるようにします。
    * コンストラクタで `DatabaseAccessor` [source:2180] と `EntryCacheManager` [source:2154] のインスタンスを外部から受け取れるようにし (依存性注入)、テスト容易性を向上させます。
    * 優先度: **高**
* [ ] **`src/sgpo_editor/core/viewer_po_file_stats.py` の `save` メソッド移動:**
    * ファイル保存ロジック [source:1548] を、ファイル操作の責務を持つ別のクラス (例: `POFilePersistenceService` (新規作成) や `src/sgpo_editor/gui/file_handler.py` [source:2449]) に移譲します。
    * 優先度: **中**
* [✅] **`src/sgpo_editor/core/viewer_po_file_base.py` の非同期処理:** [source:2322]
    * `load` メソッド内の `asyncio.to_thread` [source:3050] 使用箇所の例外処理とリソース解放が適切に行われるように改善しました。
    * 各処理ステップごとの詳細なログ出力とエラーハンドリングを追加し、デバッグ容易性を向上しました。
    * 読み込み失敗時のクリーンアップ処理を徹底し、一貫性のある状態を維持するようにしました。
    * 優先度: **中** (✅完了)
* [✅] **`src/sgpo_editor/core/database_accessor.py` の役割強化:** [source:2180]
    * フィルタリング、ソート、検索ロジックを可能な限り `DatabaseAccessor` (および内部の `src/sgpo_editor/models/database.py` [source:2658]) に集約します。SQLレベルでの最適化とインデックスの有効活用を確認します。
    * advanced_search メソッドを強化し、より柔軟な検索条件（大文字小文字の区別、完全一致、検索対象フィールドの指定など）をサポートしました。
    * invalidate_entry メソッドを強化し、キャッシュシステムとの連携フローを明確化しました。
    * 優先度: **高** (✅完了)
* [ ] **`src/sgpo_editor/core/po_interface.py` 他アダプター:** [source:1473, 1486, 1507]
    * `POEntry`, `POFile` インターフェースと各アダプター (`polib_adapter.py`, `sgpo_adapter.py`) の実装に齟齬がないか確認します。
    * 優先度: **中**

### 3.2. キャッシュ管理の改善 (優先度: 高)

* [✅] **キャッシュの一元化 (`src/sgpo_editor/core/cache_manager.py`):** [source:2154]
    * 他のクラス (特にUI層の `src/sgpo_editor/gui/table_manager.py` [source:2921], `src/sgpo_editor/gui/event_handler.py` [source:2618]) にあるキャッシュ関連ロジック (`_entry_cache`, `_row_key_map`) を廃止し、`EntryCacheManager` に集約します。
    * キャッシュ無効化API (`invalidate_entry(key)`, `invalidate_filter_cache()`, `clear_all()` など) を `EntryCacheManager` に実装し、更新処理クラスから呼び出すようにします。
    * `_force_filter_update` フラグ [source:1844] の管理を `EntryCacheManager` 内部にカプセル化します。
    * 優先度: **高**
* [✅] **キャッシュ戦略の見直し (`src/sgpo_editor/core/cache_manager.py`):** [source:2154]
    * `_entry_basic_info_cache` の必要性を再評価します。完全キャッシュからの情報抽出で十分なパフォーマンスが得られるか検証します。維持する場合、より軽量なデータ構造 (辞書など) を検討します。
    * フィルタ結果キャッシュ (`_filtered_entries_cache`) のキー生成ロジック (`_generate_filter_cache_key` [source:1842]) を堅牢化します (例: 条件辞書の正規化＋ハッシュ化)。
    * 優先度: **高**

### 3.3. UIとロジックの分離 (優先度: 中)

* [ ] **`src/sgpo_editor/gui/table_manager.py` の責務削減:** [source:2907]
    * ソート (`_sort_entries`, `_sort_entries_by_score` [source:2966, 2972]) やフィルタリングのロジックを削除し、`src/sgpo_editor/gui/facades/entry_list_facade.py` [source:2359] またはコア層に委譲します。`TableManager` は渡されたデータを表示する責務に集中させます。
    * UI状態 (列表示設定など) の変更と同期ロジック (`toggle_column_visibility` [source:2942]) を `src/sgpo_editor/gui/ui_setup.py` [source:2991] の `UIManager` やファサードと連携するように見直します。
    * 優先度: **中**
* [ ] **`src/sgpo_editor/gui/main_window.py` のロジック移譲:** [source:3150]
    * `_on_entry_updated` [source:3195] 内のテーブル更新・選択維持ロジックを `EntryListFacade` [source:2359] に移譲します。
    * 他のデータ操作やUIロジックも可能な限りファサード経由で行うように修正します。
    * 優先度: **中**
* [ ] **`src/sgpo_editor/gui/event_handler.py` のリファクタリング:** [source:2616]
    * ファサードに移行可能なロジック (特に `_update_detail_view` [source:2628], `_on_apply_clicked` [source:2645] 内のデータ操作) を特定し、`EntryEditorFacade` [source:1859] または `EntryListFacade` [source:2359] に移譲します。
    * 将来的には `EventHandler` の役割を純粋なイベント接続に限定するか、ファサードに統合して廃止することを検討します。
    * 優先度: **中**
* [ ] **`src/sgpo_editor/gui/widgets/entry_editor.py` の改善:** [source:2513]
    * `set_entry` [source:2539], `_on_msgstr_changed` [source:2536] などでの `EntryModel` とUI要素のデータ同期ロジックを、`EntryEditorFacade` [source:1859] 経由での更新に統一します。
    * `_on_apply_clicked` [source:2530] はシグナル発行のみに限定します (DB更新はファサードへ)。
    * 優先度: **中**
* [ ] **`src/sgpo_editor/gui/widgets/po_format_editor.py` の確認:** [source:2556]
    * `_on_apply_clicked` [source:2587] 内のエントリ検索 (`get_entry_by_key`, `get_filtered_entries` [source:2588]) と更新 (`po_file.update_entry` [source:2595]) が、リファクタリング後のコア層 (特にキャッシュ管理を含む) と正しく連携するか確認します。
    * 優先度: **中**

### 3.4. ファサードパターンの徹底 (優先度: 中)

* [✅] **`src/sgpo_editor/gui/facades/entry_editor_facade.py` の拡張:** [source:1859]
    * レビューダイアログ (`TranslatorCommentWidget`, `ReviewCommentWidget` など) の表示・操作もファサード経由で行えるように `show_review_dialog` [source:2250] などのメソッドを追加・活用済み。
    * データベース参照の設定・取得もファサード経由 (`set_database`, `get_database`) で行うように追加済み。
    * *残課題:* `apply_changes` が更新以外の処理を含んでいないか再確認。
    * 優先度: **完了済み** (残課題は中)
* [ ] **`src/sgpo_editor/gui/facades/entry_list_facade.py` の活用:** [source:2359]
    * `MainWindow` [source:3150] や `EventHandler` [source:2616] からのテーブル操作（更新、選択など）を `EntryListFacade` 経由に統一します。
    * 優先度: **中**
* [ ] **他のUIウィジェット:**
    * `MetadataPanel` [source:1897], `EvaluationDialog` [source:2114] など、他のUIウィジェットもデータ操作を直接行わず、適切なファサードまたはシグナル/スロット経由で連携するように見直します。
    * 優先度: **中**

### 3.5. パフォーマンスとUI応答性の改善 (優先度: 中)

* [ ] **`src/sgpo_editor/gui/table_manager.py` の描画最適化:** [source:2907]
    * `_update_table_contents` [source:2975] のパフォーマンスを計測し、ボトルネックであれば `QAbstractItemModel` への移行を検討します。
    * 優先度: **中**
* [ ] **プリフェッチ戦略 (`src/sgpo_editor/gui/event_handler.py`):** [source:2636]
    * `_prefetch_visible_entries` の効果を測定し、必要であればロジックを改善します。`EntryCacheManager` [source:2154] への移譲も検討します。
    * 優先度: **中**
* [ ] **非同期処理の確認:**
    * `src/sgpo_editor/gui/file_handler.py` [source:2449] の `save_file` [source:2463] など、他の時間のかかる可能性のある処理も非同期化が必要か検討します。
    * `src/sgpo_editor/gui/evaluation_dialog.py` [source:2114] 内のLLM評価ワーカースレッド (`EvaluationWorker` [source:2118]) のエラーハンドリングとタイムアウト処理 [source:2124] を確認します。
    * 優先度: **中**

### 3.6. テストと品質保証 (優先度: 中)

* [ ] **テストカバレッジ向上:** `pytest-cov` でカバレッジを計測し、コアロジック、ファサード、主要なUIインタラクションに対するテストを追加・拡充します (`tests/` ディレクトリ、ファイルは未提供)。
    * 優先度: **中**
* [ ] **GUIテストの整備:** `pytest-qt` を使用し、主要なUIワークフローをテストします。`_doc/test_guideline.md` [source:2082] に記載のダイアログモック化手法を適用します。
    * 優先度: **中**
* [ ] **リファクタリングに伴うテスト修正:** 上記のリファクタリング作業に合わせて既存のテストを修正・更新します。
    * 優先度: **中**

### 3.7. その他・ドキュメント (優先度: 低)

* [ ] **型ヒント強化:** プロジェクト全体で `Any` や `Optional` を減らし、より具体的な型ヒントを使用します (`src/sgpo_editor/types.py` [source:2315] の活用含む)。
    * 優先度: **低**
* [ ] **`src/sgpo_editor/config.py` の確認:** [source:1697]
    * UIの状態（列幅、表示/非表示など [source:2912, 2960]）が設定ファイルに保存・復元されるか確認・実装します。
    * 優先度: **低**
* [ ] **ドキュメント更新 (`_doc/`):**
    * アーキテクチャ設計 (`_doc/2_architecture_design.md` [source:1999])、データモデル設計 (`_doc/3_data_model_design.md` [source:2013])、UIコンポーネント設計 (`_doc/4_ui_component_design.md` [source:1717]) などを最新のコード状態に合わせて更新します。
    * 特に責務分割、キャッシュ戦略、ファサードパターンに関する記述を充実させます。
    * 優先度: **低**

## 4. 最近の改善内容

### 非同期処理の改善と例外処理の強化

ViewerPOFileBaseクラスの非同期処理を大幅に改善し、より堅牢なエラーハンドリングを実装しました。

1. **詳細な例外処理**:
   * 各処理ステップ（ファイル読み込み、データベースクリア、エントリ変換、データベース追加、キャッシュロード）ごとに個別の例外処理を追加しました。
   * エラーメッセージを具体的にし、根本原因を特定しやすくしました。
   * `from e`構文を使用して元の例外を保持し、スタックトレースの完全性を確保しました。

2. **詳細なログ出力**:
   * 各ステップの開始・完了をログに記録することで、処理の流れを追跡しやすくしました。
   * エラー時のデバッグ情報を充実させ（エントリ数、経過時間など）、問題解決を容易にしました。

3. **リソース解放の徹底**:
   * メモリリーク防止のため、大きなデータ構造（entries_to_add, pofile）を明示的に解放するようにしました。
   * エラー発生時に一貫性のある状態を維持するためのクリーンアップ処理を実装しました。

4. **エラー回復処理**:
   * エラー時にデータベースとキャッシュを確実にリセットする処理を追加しました。
   * エラー回復処理自体も例外処理で保護し、二次的な障害を防止するようにしました。

この改善により、非同期ファイル読み込み処理の堅牢性が大幅に向上し、エラー発生時のアプリケーション全体の安定性が高まりました。

### データベース操作のファサードパターン適用

EntryEditorウィジェットのデータベース直接操作を排除し、EntryEditorFacadeを介した操作に変更しました。

1.  **EntryEditorFacadeの拡張 (`src/sgpo_editor/gui/facades/entry_editor_facade.py` [source:1859])**
    * `show_review_dialog` メソッドを追加：レビューダイアログ表示をファサード経由で行えるように [source:2250]。
    * `set_database` メソッドを追加：データベース参照設定をファサード経由で行えるように [source:2253]。
    * `get_database` メソッドを追加：データベース参照取得をファサード経由で行えるように [source:2254]。
2.  **EntryEditorの改善 (`src/sgpo_editor/gui/widgets/entry_editor.py` [source:2513])**
    * `_on_fuzzy_changed` メソッドから直接データベース更新を排除 [source:2538]。
    * `_on_apply_clicked` メソッドからデータベース更新ロジックを排除し、シグナル発行のみを行うように修正 [source:2530]。
    * 各メソッドにデバッグログを追加し、処理の流れを追跡しやすくした。
3.  **MainWindowの改善 (`src/sgpo_editor/gui/main_window.py` [source:3150])**
    * `_open_file` と `_open_recent_file` メソッド内のEntryEditor直接操作をEntryEditorFacade経由に変更 [source:3168, 3177]。
    * `UISetup` の `setup_toolbar` メソッド呼び出しをEntryEditorFacade経由に変更 [source:3197]。

これらの改善により、以下の効果が得られました：
* コードの結合度が低下し、保守性が向上。
* 責務の分離が進み、各クラスの役割が明確化。
* デバッグログが充実し、問題解決が容易に。
* ファサードパターンの一貫性が向上。

今後の課題としては、レビューダイアログウィジェットなど、まだデータベースに直接アクセスしている箇所のファサード化や、EventHandlerとファサードの役割整理が残っています。

### コードスタイルの統一とフォーマット修正

コードベース全体のスタイルを統一し、可読性を向上させました：

1. **テストコードの整形**
   * 余分な空白行の削除と適切な空白行の配置
   * 長い行の適切な折り返し処理
   * インデントの修正
   * 末尾カンマの配置の統一

2. **PEP 8に準拠した修正**
   * コードスタイルガイドラインに従った修正
   * 一貫したフォーマットの適用

これらの変更はコードの機能に影響を与えず、可読性とメンテナンス性の向上を目的としています。今後も継続的にコード品質の改善を進めていきます。

## タスクリスト

### 完了したタスク
* [✅] POEntryインターフェースに複数形サポート（msgid_plural、msgstr_plural）を追加
  * 抽象インターフェース（po_interface.py）に複数形のプロパティを追加
  * polibアダプター（polib_adapter.py）に実装を追加
  * sgpoアダプター（sgpo_adapter.py）に実装を追加

### 現在のタスク
* [ ] **キャッシュ処理の最適化**
  * EntryCacheManagerのキャッシュヒット率向上のための改善
  * パフォーマンス計測と最適化ポイントの特定
  * メモリ使用量の監視と最適化
  * 詳細なデバッグログの追加によるキャッシュ動作の可視化

### 今後のタスク
* [ ] タイプヒントの改善
  * より具体的な型情報を使用してコードの安全性を向上させる
* [ ] テストの拡充
  * 新しく追加した複数形サポートのテストケースを追加する
* [ ] ドキュメントの更新
  * 複数形サポートについてのドキュメントを追加する

## キャッシュ処理の最適化計画

### 現状の課題
1. 大量のエントリを持つPOファイルを操作する際のパフォーマンス問題
2. キャッシュミスによる不要なデータベースアクセス
3. フィルタリング時のキャッシュ更新ロジックの改善余地

### 実施内容
1. **キャッシュ戦略の最適化**
   * `EntryCacheManager`のキャッシュアルゴリズムを改善
   * 使用頻度の高いエントリを優先的にキャッシュする仕組みの導入
   * キャッシュサイズの動的調整機能の追加

2. **プリフェッチロジックの強化**
   * `prefetch_visible_entries`メソッドの処理を非同期化
   * スクロール方向予測に基づく先読み機能の実装
   * エントリ間の関連性に基づく関連エントリのプリフェッチ

3. **デバッグとパフォーマンス監視機能**
   * キャッシュヒット率と処理時間の計測・記録機能
   * メモリ使用量監視によるキャッシュサイズの最適化
   * 詳細なログ機能によるキャッシュの挙動追跡

4. **ファイル読み込み時の最適化**
   * `ViewerPOFileBase.load`メソッドのメモリ使用効率向上
   * エントリ一括変換とデータベース登録の改善
   * 段階的キャッシュ構築によるメモリ使用ピークの抑制
