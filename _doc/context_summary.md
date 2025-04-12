# SGPO Editor: コーディングエージェント向け開発ガイド (コンポジション優先版)

## 1. プロジェクト概要 (Context)

*   **アプリケーション:** SGPO Editor は、gettext PO ファイル（翻訳リソース）を効率的に編集・管理するためのデスクトップ GUI アプリケーションです。
*   **目的:** 翻訳者やローカライゼーション担当者向けに、PO ファイルの表示、編集、検索、フィルタリング、統計表示、翻訳品質評価 (LLM 利用) などの機能を提供します。
*   **技術スタック:**
    *   言語: Python (>=3.8)
    *   GUI: PySide6 (Qt for Python)
    *   PO 操作: `sgpo` ライブラリ (または `polib`) - 現在は `sgpo` が主に使われている
    *   依存関係管理: `uv`
    *   データモデル: Pydantic (`EntryModel`)
    *   テスト: `pytest`, `pytest-qt`
    *   リンター/フォーマッタ: Ruff, flake8
    *   型チェック: mypy
    *   データベース: インメモリ SQLite (`InMemoryEntryStore`), 評価データ用サイドカー SQLite (`EvaluationDatabase`)
    *   キャッシュ: `EntryCacheManager` による複数レベルキャッシュ

## 2. 現在のアーキテクチャと課題 (Current State & Challenges)

*   **基本アーキテクチャ:** Model-View-Controller (MVC) パターンを基本とし、UI・ロジック・データの分離を目指しています。ファサードパターン (`EntryEditorFacade`, `EntryListFacade`, `ReviewDialogFacade`) が導入されています。`ViewerPOFile` はコンポジションパターンで再設計済みです。
*   **進行中のリファクタリング:** 現在、キャッシュ管理の一元化とファサードパターンの徹底が進行中です。
*   **主な課題:**
    1.  **キャッシュ機構の完全な一元化未完了:** `EntryCacheManager` が中心となっていますが、`TableManager` 等のUI層にまだキャッシュ関連のコードや状態（例: `_entry_cache`, `_row_key_map` の使用）が残存している可能性があり、`EntryCacheManager` のAPI利用への完全移行が必要です。
    2.  **ファサードパターン適用の不徹底:** `EventHandler` にまだロジック（コメントアウト含む）が残っており、ファサードへの完全な移譲が完了していません。`MainWindow` や他のUIウィジェットからコア層/モデル層への直接アクセスも残っている可能性があります。
    3.  **UI とロジックの結合度:** `TableManager` が依然として表示以外のロジック（例: ソート状態の保持？）を含んでいる可能性があり、表示責務への特化が未完了です。
    4.  **インスペクションエラー:** 未解決参照、型エラー、不正な引数リストなど、リファクタリング途中に起因する可能性のあるクリティカルなエラーが多数検出されています。これらはコードの安定性と信頼性に影響します。
    5.  **重複コード:** キャッシュ管理、DBアクセス、UI更新処理などで重複コードが検出されており、保守性を低下させています。

## 3. 目指すべきアーキテクチャ (Target Architecture / "あるべき姿")

リファクタリングを通じて、以下の状態を目指します。コード生成・修正の際は、これらの原則に従ってください。

*   **責務の明確化と分離 (コンポジション優先):**
    *   `ViewerPOFile` は機能コンポーネント (`EntryRetrieverComponent`等) の調整役として機能します (**達成済み**)。
    *   各機能コンポーネントは単一責務を持ち、独立してテスト可能です。
    *   UI ウィジェット (`src/sgpo_editor/gui/widgets/`, `TableManager`) は、表示とユーザー操作のイベント発行に専念し、データ処理ロジック（ソート、キャッシュ管理等）を持たないようにします。
*   **キャッシュ管理の完全な一元化:**
    *   エントリデータに関するキャッシュ管理は `src/sgpo_editor/core/cache_manager.py` の `EntryCacheManager` に**完全に集約**します。UI層での独自キャッシュは**廃止**します。
    *   UI層が必要とする行とキーのマッピング機能は `EntryCacheManager` が提供するAPI (`add_row_key_mapping` 等) を利用します。
    *   キャッシュの更新や無効化は `EntryCacheManager` のAPIを通じて行います。
*   **ファサードパターンの徹底:**
    *   UI 層 (`gui` パッケージ) からコアロジック層 (`core` パッケージ) やデータモデル層 (`models` パッケージ) へのアクセスは、**原則として** `src/sgpo_editor/gui/facades/` 以下のファサードクラスを経由して行います。
    *   `EventHandler` が持つデータ操作ロジックは、適切なファサードに**完全に移譲**します。EventHandlerは最終的に廃止される可能性があります。
*   **明確な依存関係:**
    *   依存関係の方向を UI → Facade → Core (ViewerPOFile + Components) → Cache / DB Access → Data Models となるように維持します。
    *   下位レイヤーから上位レイヤーへの直接的な依存は避けてください。
*   **テスト容易性:**
    *   クラス間の依存関係は、コンストラクタやメソッド引数を通じた**依存性注入 (DI)** を基本とし、テスト時にモックオブジェクトを注入しやすくします。
    *   GUI テストでは、`_doc/test_guideline.md` のベストプラクティス（ダイアログモック等）に従います。
*   **型安全性:**
    *   `typing` モジュールと Pydantic モデルを積極的に活用し、`Any` の使用を避け、可能な限り具体的な型ヒントを付与します。`src/sgpo_editor/types.py` の型エイリアスも活用してください。**インスペクションで指摘された型エラーは修正してください。**

## 4. コーディングガイドライン (Coding Guidelines)

*   **スタイル:**
    *   フォーマット: Ruff (`uv run ruff format`)。
    *   リンター: flake8 (`.flake8`) および Ruff。エラー修正時はまずフォーマッタ実行 (`.cursor/rules/linter-error-python.mdc` 参照)。
    *   原則: PEP 8 準拠。
*   **言語:**
    *   識別子、コメントは英語。
    *   UIテキストは `src/sgpo_editor/i18n/translator.py` の `translate()` で国際化。
*   **設計原則:**
    *   単一責任の原則 (SRP)。
    *   疎結合。**継承よりコンポジションを優先**。
*   **エラーハンドリング:**
    *   `try...except` で適切な例外処理。
    *   `logging` モジュールで情報記録 (`.cursor/rules/debug.mdc` 参照)。
    *   ユーザーには `QMessageBox` で分かりやすいエラー表示。
*   **テスト:**
    *   機能追加/バグ修正時には対応するテストコード (`pytest`) を `tests/` に追加/更新推奨。
    *   GUIテストは `pytest-qt` 利用、`_doc/test_guideline.md` 参照。
*   **依存関係管理:**
    *   新規ライブラリ追加は `uv add <package_name>`、`pyproject.toml` に記録。
*   **ドキュメント:**
    *   クラスや複雑な関数にはdocstring記述。
    *   大きな設計変更時は関連ドキュメント更新推奨。

## 5. 重要なコンポーネントとファイル (Key Components & Files)

*   **UI 層:** `src/sgpo_editor/gui/`
    *   `main_window.py`: メインウィンドウ、UI 統合、イベントディスパッチ（ファサードへ移行中）
    *   `facades/`: UI 操作の抽象化レイヤー (**修正の中心**)
    *   `widgets/`: 各種 UI 部品 (EntryEditor, SearchWidget, StatsWidget)
    *   `event_handler.py`: GUI イベント処理 (**廃止予定、ロジックはファサードへ**)
    *   `table_manager.py`: テーブル表示管理 (**表示責務に特化、キャッシュ削除**)
    *   `ui_setup.py`: メニュー、ツールバー、ドック管理
*   **コア層:** `src/sgpo_editor/core/`
    *   `viewer_po_file.py`: PO データ管理の中心（コンポジション化済み）
    *   `po_components/`: `ViewerPOFile` の機能別コンポーネント
    *   `cache_manager.py`: キャッシュ管理の責任クラス (**修正の中心**)
    *   `database_accessor.py`: DB アクセスの責任クラス
    *   `po_factory.py`, `po_interface.py`, `polib_adapter.py`, `sgpo_adapter.py`: PO ライブラリ抽象化
*   **モデル層:** `src/sgpo_editor/models/`
    *   `entry.py`: `EntryModel` (Pydantic)
    *   `database.py`: `InMemoryEntryStore` (インメモリ DB)
    *   `evaluation_db.py`: `EvaluationDatabase` (永続 DB)
*   **設定/国際化:** `src/sgpo_editor/config.py`, `src/sgpo_editor/i18n/`
*   **ドキュメント:** `_doc/` (特に `todo.md`, `2_architecture_design.md`, `test_guideline.md`, この `context_summary.md`)
*   **プロジェクト定義:** `pyproject.toml`
*   **インスペクション結果:** `inspection/`