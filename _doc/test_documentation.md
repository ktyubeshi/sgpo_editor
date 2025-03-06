# SGPO Editor テストドキュメント

このドキュメントでは、SGPO Editorプロジェクトのテストコードについて説明します。テストは主にPythonのunittestとpytestフレームワークを使用して実装されています。

## 目次

1. [テスト構成](#テスト構成)
2. [テスト設定ファイル](#テスト設定ファイル)
3. [モックヘルパー](#モックヘルパー)
4. [テストファイル一覧](#テストファイル一覧)
   - [メインウィンドウテスト](#メインウィンドウテスト)
   - [モデルテスト](#モデルテスト)
   - [コアロジックテスト](#コアロジックテスト)
   - [ユーティリティテスト](#ユーティリティテスト)

## テスト構成

テストコードは `tests` ディレクトリに配置されており、以下のような構成になっています：

- 基本的なGUIコンポーネントテスト
- モデルに関するテスト
- POファイル処理に関するテスト
- ユーティリティ関数のテスト

テストには主に以下のアプローチが使用されています：

1. **ユニットテスト**: 個々の関数やメソッドの機能を検証
2. **統合テスト**: 複数のコンポーネントの連携を検証
3. **モックベーステスト**: 外部依存を持つコンポーネントをモック化して検証

### __init__.py

テストパッケージの初期化ファイルです。このファイルは空で、Pythonにテストディレクトリをパッケージとして認識させる役割を持ちます。

### all_main_window_suite.py

SGPOエディタのMainWindowテストスイートの参照ポイントとして機能します。このファイルは直接テストを実行するためのものではなく、すべてのMainWindow関連のテストファイルへの参照として機能します。

実際のテストは以下の個別ファイルで実行されます：
- test_main_window.py - 基本機能とテーブルソートのテスト
- test_main_window_basic.py - 基本的なファイル操作のテスト
- test_main_window_table.py - テーブル操作関連のテスト
- test_main_window_entry.py - エントリ操作関連のテスト
- test_main_window_search.py - 検索機能関連のテスト
- test_main_window_layout.py - レイアウト関連のテスト
- test_main_window_error.py - エラー処理関連のテスト
- test_main_window_state.py - 状態管理関連のテスト

すべてのメインウィンドウ関連テストを一括実行するコマンド：
```bash
$ uv run pytest tests/test_main_window_*.py -v
```

個別のテストファイルを実行するコマンド：
```bash
$ uv run pytest tests/test_main_window_basic.py -v
```

特定のテストメソッドを実行するコマンド：
```bash
$ uv run pytest tests/test_main_window.py::TestMainWindow::test_table_sorting -v
```

## テスト設定ファイル

### conftest.py

pytestの設定ファイルで、テスト環境のセットアップやフィクスチャの定義を行います。このファイルはpytestの実行時に自動的に読み込まれます。

主な機能：

1. **QApplicationの管理**
   - `pytest_configure`: pytestの設定時にQApplicationのインスタンスを作成
   - `pytest_unconfigure`: pytestの終了時にQApplicationを終了し、リソースをクリーンアップ

2. **フィクスチャの提供**
   - `qapp`: QApplicationのフィクスチャ（セッションスコープ）
   - `cleanup_windows`: テスト後にすべてのウィンドウをクリーンアップするフィクスチャ（関数スコープ）
   - `mock_qt_dialogs`: Qt対話型ダイアログをモック化するフィクスチャ（関数スコープ）
   - `mock_main_window_components`: MainWindowのコンポーネントをモック化するフィクスチャ（関数スコープ）
   - `reset_qt_mocks`: すべてのテストの前後でQtモックをリセットするフィクスチャ（自動使用、関数スコープ）

3. **モック化の実装**
   - ファイル選択ダイアログのモック
   - メッセージボックスのモック
   - MainWindowの依存コンポーネントのモック

## モックヘルパー

テストではGUIコンポーネントなどの外部依存を持つ部分をモック化するためのヘルパー関数が提供されています：

### base_test_helpers.py

基本的なテストヘルパークラスを提供します：

- `TestBase`: GUIテストの基底クラス（モック設定、リソースクリーンアップなど）
- `MockMainWindow`: メインウィンドウをモック化するためのシンプルな実装

### mock_helpers.py

より詳細なモックヘルパー関数を提供します：

- `MockMainWindow`: テストガイドラインに基づくメインウィンドウのモック実装
- ダイアログのモック関数（`mock_file_dialog_get_open_file_name`など）
- メッセージボックスのモック関数（`mock_message_box_question`など）
- ユーザー操作をシミュレートする関数（`click_button`、`enter_text`など）
- 高レベルモックヘルパー関数（`mock_entire_app`など）

## テストファイル一覧

### メインウィンドウテスト

#### test_main_window.py

メインウィンドウの基本機能とテーブルソートのテストを実装しています。重複するテストは他のテストファイルに移動され、以下のテストのみが残されています：

- **ファイル操作テスト**
  - test_file_operations: ファイルの開く・保存操作のテスト
  - test_file_operations_error: ファイル操作のエラー処理テスト

- **レイアウト関連テスト**
  - test_layout_with_entry: エントリ表示中のレイアウト切り替えテスト
  - test_entry_list_layout: エントリリストのレイアウトテスト

- **エントリ表示テスト**
  - test_entry_selection_display: エントリ選択時の表示テスト

- **テーブルソートテスト**
  - test_table_sorting: テーブルのソート機能テスト

- **フィルタリングテスト**
  - test_state_based_filtering: 状態ベースのフィルタリングテスト
  - test_keyword_based_filtering: キーワードベースのフィルタリングテスト

- **GUI操作テスト**
  - test_gui_state_filter_interaction: GUI状態フィルタ操作テスト
  - test_gui_keyword_filter_interaction: GUIキーワードフィルタ操作テスト

- **メニューテスト**
  - test_view_menu_layout: 表示メニューのレイアウトテスト

#### test_main_window_basic.py

メインウィンドウの基本機能テスト：

- 初期状態の確認
- ファイルを開く機能（成功、キャンセル）
- 名前を付けて保存機能（成功、キャンセル）
- POファイルがない状態での保存
- ウィンドウを閉じるイベント処理

#### test_main_window_entry.py

エントリ関連の操作テスト：

- エントリテキスト変更時の処理
- 適用ボタンクリック時の処理
- エントリナビゲーション（次/前/最初/最後のエントリ）
- エントリ選択表示

#### test_main_window_layout.py

レイアウト関連の機能テスト：

- ドック状態の保存と復元
- 表示メニューのレイアウト切り替え
- レイアウト切り替えの動作
- エントリ表示中のレイアウト切り替え

#### test_main_window_error.py

エラー処理関連のテストを実装しています：

- **一般的なエラー処理**
  - test_general_error_handling: 一般的なエラー処理のテスト
  - test_error_dialog_display: エラーダイアログ表示のテスト

- **ファイル操作エラー**
  - test_file_open_error: ファイルを開く際のエラー処理
  - test_file_save_error: ファイル保存エラーの処理
  - test_file_save_as_error: 名前を付けて保存時のエラー処理

- **テーブル関連エラー**
  - test_table_update_error: テーブル更新時のエラー処理
  - test_table_sort_error: テーブルソート時のエラー処理

- **検索関連エラー**
  - test_search_error: 検索時のエラー処理
  - test_filter_error: フィルタリング時のエラー処理

#### test_main_window_state.py

状態管理関連のテストを実装しています：

- **アプリケーション状態テスト**
  - test_initial_state: 初期状態の確認テスト
  - test_invalid_state_entry_display: 無効な状態でのエントリ表示テスト
  - test_state_after_file_open: ファイルを開いた後の状態テスト

- **テーブル状態テスト**
  - test_table_progress_tracking: テーブルの進捗追跡テスト
  - test_table_entry_count_validation: テーブルのエントリ数検証テスト
  - test_table_state_after_sort: ソート後のテーブル状態テスト

- **ファイル状態テスト**
  - test_save_po_file_with_path: パス属性を持つPOファイルの保存テスト
  - test_file_modified_state: ファイル変更状態のテスト

- **エントリ状態テスト**
  - test_entry_update: エントリ更新テスト
  - test_entry_list_data: エントリリストのデータテスト
  - test_entry_state_after_edit: 編集後のエントリ状態テスト

#### test_main_window_search.py

検索関連の機能テスト：

- 検索/フィルタリング機能
- エントリの状態ベースフィルタ
- キーワードベースのフィルタリング
- GUIの状態フィルタ操作
- GUIのキーワードフィルタ操作
- POファイルが開かれていない状態での検索
- 検索中のエラー処理
- 完全一致検索

#### test_main_window_table.py

テーブル操作関連のテスト：

- テーブル更新
- フィルタ条件を使ったテーブル更新
- 検索条件を使ったテーブル更新
- テーブルセルクリック時の処理

### モデルテスト

#### test_entry_model.py

`EntryModel`クラスのテスト：

- フラグ処理（文字列、空文字列、リスト、デフォルト値）

#### test_models.py

モデルクラスのテスト：

- `EntryModel` の機能検証：
  - 基本プロパティ
  - キー生成
  - 翻訳状態
  - フラグ操作
  - POEntryからの変換
  - 辞書形式への変換と復元
- `StatsModel` の機能検証：
  - 基本プロパティ
  - 進捗率計算

### コアロジックテスト

#### test_viewer_po_file.py

`ViewerPOFile`クラスのテスト：

- POファイルの読み込み
- エントリの取得とフィルタリング
- エントリの更新
- エントリの検索
- 統計情報の取得
- POファイルの保存

#### test_sgpo.py

`SGPOFile`クラスのテスト：

- 初期化
- ファイルからの読み込み
- テキストからの読み込み
- キーによるエントリ検索
- ソート機能
- フォーマット機能
- キーリストの取得
- 未知エントリのインポート

### ユーティリティテスト

#### test_duplicate_checker.py

重複エントリチェック機能のテスト：

- 圧縮表記を含む重複エントリのチェック
- 重複がない場合のチェック
- 複数の重複エントリのチェック
- 圧縮表記の展開機能

#### test_debug.py

デバッグ関連機能のテスト。

## モックフィクスチャ

テストでは以下のようなフィクスチャが使用されています：

- `mock_components`: 各コンポーネントのモックを設定するフィクスチャ
- `mock_main_window`: モック化されたMainWindowのフィクスチャ
- `mock_app`: アプリケーション全体をモック化するフィクスチャ
- `mock_window`: メインウィンドウをモック化するフィクスチャ
- `test_po_file`: テスト用のPOファイルを作成するフィクスチャ

## まとめ

SGPO Editorプロジェクトでは、様々なレベルでのテストが実装されており、アプリケーションの品質を確保するための仕組みが整えられています。GUI操作のテストにはモックを活用し、実際のウィンドウを表示することなくテストを実行できるよう工夫されています。

## テスト実行方法

テストは以下のコマンドで実行できます：

```bash
# 全てのテストを実行
$ uv run pytest

# 特定のテストファイルを実行
$ uv run pytest tests/test_main_window.py

# 特定のテストパターンを実行
$ uv run pytest tests/test_main_window_*.py

# 詳細出力でテストを実行
$ uv run pytest -v

# 特定のマーカーを持つテストを実行
$ uv run pytest -m main_window
```

## テストコード構造の改善

テストコードの構造を改善し、重複を削除して管理しやすくしました。以下の変更が行われました：

1. **新規テストファイルの作成**
   - test_main_window_error.py - エラー処理関連のテスト
   - test_main_window_state.py - 状態管理関連のテスト
   - test_main_window_basic.py - 基本的なファイル操作のテスト
   - test_main_window_table.py - テーブル操作関連のテスト
   - test_main_window_entry.py - エントリ操作関連のテスト
   - test_main_window_search.py - 検索機能関連のテスト
   - test_main_window_layout.py - レイアウト関連のテスト

2. **test_main_window.pyの重複テスト削除**
   - 重複するテストを削除し、以下のテストのみを残しました：
     - ファイル操作テスト（test_file_operations, test_file_operations_error）
     - レイアウト関連テスト（test_layout_with_entry, test_entry_list_layout）
     - エントリ選択表示テスト（test_entry_selection_display）
     - テーブルソートテスト（test_table_sorting）
     - フィルタリング関連テスト（test_state_based_filtering, test_keyword_based_filtering）
     - GUI操作テスト（test_gui_state_filter_interaction, test_gui_keyword_filter_interaction）
     - メニュー関連テスト（test_view_menu_layout）

3. **テストファイルの役割明確化**
   - test_main_window.py: 基本機能とテーブルソートのテスト
   - test_main_window_basic.py: 基本的なファイル操作のテスト
   - test_main_window_table.py: テーブル操作関連のテスト
   - test_main_window_entry.py: エントリ操作関連のテスト
   - test_main_window_search.py: 検索機能関連のテスト
   - test_main_window_layout.py: レイアウト関連のテスト
   - test_main_window_error.py: エラー処理関連のテスト
   - test_main_window_state.py: 状態管理関連のテスト

4. **all_main_window_suite.pyの更新**
   - 新しいテストファイル構造を反映するように更新
   - 各テストファイルの役割を明確に記述

5. **テスト実行の簡素化**
   - すべてのメインウィンドウ関連テストを一括実行するコマンド：
     ```bash
     $ uv run pytest tests/test_main_window_*.py -v
     ```
   - 個別のテストファイルを実行するコマンド：
     ```bash
     $ uv run pytest tests/test_main_window_basic.py -v
     ```

この改善により、テストコードの管理が容易になり、テストの重複が削除されました。また、テストの実行時間も短縮され、特定の機能に関するテストを個別に実行することが容易になりました。
