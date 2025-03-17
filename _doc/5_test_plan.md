---
created: 2025-03-12T16:47
updated: 2025-03-12T16:47
---
# SGPO Editor テスト計画

## 1. テスト戦略の概要

SGPO Editorのテスト戦略は、品質を確保し、継続的な改善を促進するために、複数のテストレベルと種類を組み合わせたアプローチを採用しています。本ドキュメントでは、テスト目標、テスト範囲、テスト手法、およびテストプロセスについて詳細に説明します。

### 1.1 テスト目標

テスト活動の主な目標は以下の通りです：

- ソフトウェア要件に対する完全な適合性の検証
- ユーザビリティと操作性の確保
- 異常系動作時の適切なエラー処理と回復性の検証
- パフォーマンスとスケーラビリティの要件の確認
- 国際化とローカライゼーションの機能検証

### 1.2 テスト範囲

テスト対象は以下の要素を含みます：

- コアロジック（POファイル操作、検索、フィルタリング）
- ユーザーインターフェース（レイアウト、操作性、表示）
- ファイル操作とデータ管理
- 設定と状態管理
- エラー処理と例外処理

## 2. テストレベル

SGPO Editorのテストは以下のレベルで実施されます：

### 2.1 単体テスト（ユニットテスト）

個々のコンポーネントとモジュールの機能を検証します。

- **テスト対象**: 個々のクラスとメソッド
- **テストツール**: pytest
- **テスト実行**: 自動化（CIパイプライン及び手動実行）
- **テスト例**:
  - PoFileクラスのロード機能
  - ViewerPOFileのフィルタリング機能
  - TableManagerの表示更新機能

```python
# ViewerPOFileのフィルタリング機能テスト例
def test_get_filtered_entries():
    # テスト用POファイルを準備
    po_file = create_test_po_file()
    viewer = ViewerPOFile(po_file)
    
    # フィルタリング条件を設定
    filtered = viewer.get_filtered_entries(
        filter_text="未翻訳", 
        search_text="test", 
        match_mode="部分一致"
    )
    
    # 結果を検証
    assert len(filtered) == 2
    assert all("test" in entry.msgid for entry in filtered)
    assert all(entry.msgstr == "" for entry in filtered)
```

### 2.2 統合テスト

複数のコンポーネント間の連携を検証します。

- **テスト対象**: コンポーネント間のインターフェース
- **テストツール**: pytest + モック
- **テスト実行**: 自動化（CIパイプライン及び手動実行）
- **テスト例**:
  - FileHandlerとPoFileの連携
  - MainWindowとEntryEditorの連携
  - TableManagerとViewerPOFileの連携

```python
# FileHandlerとPoFileの連携テスト例
def test_file_handler_and_po_file_integration(monkeypatch):
    # ファイルダイアログをモック
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName",
        lambda *args, **kwargs: ("/mock/path/to/test.po", "All Files (*)")
    )
    
    # POファイルクラスをモック
    mock_po = MagicMock()
    monkeypatch.setattr("sgpo_editor.po.PoFile", lambda path: mock_po)
    
    # MainWindowを初期化
    main_window = MainWindow()
    main_window._open_file()
    
    # 検証
    assert main_window.file_handler.current_po is not None
    assert main_window.file_handler.file_path == "/mock/path/to/test.po"
```

### 2.3 システムテスト

アプリケーション全体の機能と要件適合性を検証します。

- **テスト対象**: アプリケーション全体の機能
- **テスト手法**: シナリオベーステスト、探索的テスト
- **テスト実行**: 手動（一部自動化）
- **テスト例**:
  - エンドツーエンドのワークフロー（ファイルを開く → 編集 → 保存）
  - 異なるレイアウト設定での操作
  - フィルタと検索の組み合わせ使用

### 2.4 受け入れテスト

ユーザー要件に対する適合性を検証します。

- **テスト対象**: ユーザー要件と期待される機能
- **テスト手法**: ユーザーストーリー、受け入れ基準
- **テスト実行**: 手動（一部自動化）
- **テスト例**:
  - 翻訳者が効率的に作業できるか
  - 進捗状況が明確に表示されるか
  - エラー発生時に適切にガイダンスが提供されるか

## 3. テスト種類

### 3.1 機能テスト

基本機能と拡張機能の検証を行います。

- **POファイル操作テスト**: 読み込み、表示、編集、保存
- **検索・フィルタリングテスト**: 条件指定、結果表示
- **統計表示テスト**: 翻訳進捗状態の正確な集計と表示
- **エントリ操作テスト**: 選択、表示、編集、適用

### 3.2 GUIテスト

ユーザーインターフェースの動作と表示を検証します。

- **レイアウトテスト**: 異なるレイアウト設定での表示確認
- **コンポーネント操作テスト**: ボタン、メニュー、テーブルなどの操作
- **キーボードショートカットテスト**: ショートカットキーの動作確認
- **表示テスト**: フォント、色、アイコンなどの視覚要素

```python
# レイアウト切り替えテスト例
def test_layout_switching(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    
    # 初期状態を確認
    assert window.ui_manager.current_layout == LayoutType.STANDARD
    
    # コンパクトレイアウトに切り替え
    window.ui_manager.switch_layout(LayoutType.COMPACT)
    assert window.ui_manager.current_layout == LayoutType.COMPACT
    
    # レイアウトの視覚的状態を確認
    compact_layout_visible = window.entry_editor.layout_types[LayoutType.COMPACT].isVisible()
    assert compact_layout_visible
```

### 3.3 パフォーマンステスト

アプリケーションのパフォーマンスと応答性を検証します。

- **大規模POファイルのロードテスト**: 大量エントリでの読み込み速度
- **フィルタリング速度テスト**: 大量データでのフィルタリング応答性
- **メモリ使用量テスト**: リソース使用効率
- **UI応答性テスト**: 操作中のUI凍結がないことの確認

### 3.4 ローカライゼーションテスト

国際化とローカライゼーション機能を検証します。

- **多言語対応テスト**: 異なる言語設定での表示確認
- **文字エンコーディングテスト**: 特殊文字やUnicodeの処理
- **RTL言語対応テスト**: 右から左へ記述する言語のレイアウト

### 3.5 互換性テスト

異なる環境での動作を検証します。

- **OS互換性テスト**: Windows、macOS、Linuxでの動作確認
- **Python/Qt互換性テスト**: サポート対象のPythonとQtバージョンでの動作確認

## 4. テスト環境

### 4.1 テスト環境構成

SGPO Editorのテストは以下の環境で実施されます：

- **開発環境**: 開発者のローカル環境（Windows/macOS/Linux）
- **CI環境**: GitHub Actions（または同等のCI）
- **検証環境**: テスト専用環境

### 4.2 テストデータ

テストには以下のデータを使用します：

- **サンプルPOファイル**: 異なるサイズと翻訳状態のテスト用POファイル
- **モックデータ**: 自動テスト用の生成データ
- **実データ**: 実際のプロジェクトからの匿名化されたPOファイル

## 5. テスト実行と自動化

### 5.1 テスト実行コマンド

テストの実行には`uv run pytest`を使用します：

```bash
# すべてのテストを実行
$ uv run pytest

# 特定のテストファイルを実行
$ uv run pytest tests/test_main_window.py

# 特定のテストメソッドを実行
$ uv run pytest tests/test_main_window.py::TestMainWindow::test_table_sorting -v

# カバレッジレポートを生成
$ uv run pytest --cov=sgpo_editor tests/
```

### 5.2 継続的インテグレーション

CIパイプラインでは以下のタスクを自動化します：

- **コードリント**: flake8/pylint
- **型チェック**: mypy
- **単体テスト**: pytest
- **統合テスト**: pytest
- **カバレッジレポート**: pytest-cov

### 5.3 テスト結果レポート

テスト結果は以下の形式で報告されます：

- **テスト実行概要**: 成功/失敗/スキップされたテストの要約
- **詳細エラーレポート**: 失敗したテストの詳細情報
- **カバレッジレポート**: コードカバレッジの統計と視覚化

## 6. 特殊なテスト技術

### 6.1 モックとスタブの使用

GUI要素や外部依存をモック化してテストを分離し、安定性を向上させます：

```python
@pytest.fixture(scope="function")
def mock_qt_dialogs(monkeypatch):
    """Qt対話型ダイアログをモック化するフィクスチャ"""
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName",
        lambda *args, **kwargs: ("/mock/path/to/test.po", "All Files (*)")
    )
    # その他のモック設定...
    yield
```

### 6.2 データドリブンテスト

多様なテストデータを使用して同じテストロジックを繰り返し実行します：

```python
@pytest.mark.parametrize("filter_text,search_text,expected_count", [
    ("未翻訳", "", 10),
    ("翻訳済み", "test", 5),
    ("要確認", "important", 3),
    ("", "not_exist", 0),
])
def test_filter_entries(filter_text, search_text, expected_count):
    # テスト実装...
    assert len(filtered_entries) == expected_count
```

### 6.3 スナップショットテスト

UIコンポーネントの表示状態を保存し、変更を検出します：

```python
def test_entry_editor_layout(snapshot):
    editor = EntryEditor()
    editor.update_entry(test_entry)
    
    # スナップショットと比較
    assert snapshot(editor.toPixmap()) == "entry_editor_standard_layout.png"
```

## 7. テスト管理

### 7.1 テスト計画と追跡

テスト活動は以下の方法で計画・追跡されます：

- **テスト計画**: 四半期ごとの機能と非機能テスト計画
- **テストケース管理**: GitHub Issuesまたは専用テスト管理ツール
- **バグ追跡**: GitHub Issues

### 7.2 テスト優先順位付け

限られたリソースで効果的なテストを行うため、以下の優先順位を設定します：

1. **クリティカル**: コア機能（ファイル操作、データ整合性）
2. **高**: 主要機能（UI操作、検索、フィルタリング）
3. **中**: 補助機能（統計表示、ヘルプ）
4. **低**: 便利機能（ショートカット、カスタマイズ）

## 8. QAプロセス

### 8.1 バグトリアージ

発見された問題は以下のプロセスで分類・対応されます：

1. **問題の報告**: テンプレートに沿った報告
2. **分類と優先度付け**: 影響度と緊急度に基づく評価
3. **担当者割り当て**: 適切な開発者への割り当て
4. **修正とレビュー**: コードレビューによる品質確保
5. **検証**: 問題が解決されたことの確認

### 8.2 リグレッションテスト

新機能追加や修正後に既存機能が正常に動作することを確認するため、以下のリグレッションテスト戦略を採用します：

- **自動化テストの実行**: すべての既存テストの実行
- **重要なユースケースの手動検証**: コア機能の確認
- **影響範囲のテスト**: 変更の影響を受ける可能性がある機能の集中テスト

## 9. テスト成熟度と改善

テストプロセスは継続的に評価・改善され、以下の指標をトラッキングします：

- **テストカバレッジ**: コードカバレッジと機能カバレッジ
- **バグ発見率**: テストフェーズごとのバグ発見数
- **テスト効率**: テスト実行時間とリソース使用量
- **自動化率**: 自動化されたテストの割合

## 10. テスト関連ファイル

### 10.1 テスト設定ファイル

#### pytest.ini
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    gui: tests that require a GUI
    slow: tests that are slow
    integration: integration tests
```

#### mypy.ini
```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True

[mypy.plugins.qt]
enabled = True
```

### 10.2 テストヘルパー

#### conftest.py
```python
@pytest.fixture(scope="session")
def qapp():
    """QApplicationのフィクスチャ"""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app

@pytest.fixture(scope="function")
def cleanup_windows():
    """テスト後にすべてのウィンドウをクリーンアップするフィクスチャ"""
    yield
    # テスト終了後のクリーンアップ...
```

### 10.3 モックヘルパー

モックヘルパー関数は、単独のモジュールとして実装されています：

```python
def mock_file_dialog_get_open_file_name(monkeypatch, return_path="/mock/path/to/file.po"):
    """QFileDialog.getOpenFileNameをモック化する"""
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName",
        lambda *args, **kwargs: (return_path, "All Files (*)")
    )
```
