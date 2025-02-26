# PO Viewer コードベース概要

## プロジェクト概要

PO Viewer（sgpo_editor）は、POファイル（gettext翻訳ファイル）の表示、編集、チェックを行うためのツールです。GUIとCLIの両方のインターフェースを提供しており、翻訳作業の効率化を支援します。

## プロジェクト構造

```
po_viewer/
├── _doc/                   # ドキュメント（設計書、概要など）
├── data/                   # データファイル（使用例やテスト用データ）
├── logs/                   # ログファイル（アプリケーションログの出力先）
├── sgpo_editor/            # メインパッケージ
│   ├── core/               # コア機能（POファイル処理など）
│   │   └── viewer_po_file.py  # POファイル読み書きの中核クラス
│   ├── gui/                # GUIコンポーネント
│   │   ├── widgets/        # 各種ウィジェット
│   │   │   ├── entry_editor.py  # 翻訳エントリ編集ウィジェット
│   │   │   ├── search.py        # 検索ウィジェット
│   │   │   └── stats.py         # 統計情報ウィジェット
│   │   ├── models/         # GUIモデル
│   │   │   ├── entry.py         # エントリデータモデル
│   │   │   └── stats.py         # 統計情報モデル
│   │   ├── main_window.py  # メインウィンドウ実装
│   │   ├── table_manager.py  # テーブル管理クラス
│   │   ├── file_handler.py   # ファイル操作処理
│   │   ├── event_handler.py  # イベント処理
│   │   └── ui_setup.py       # UI初期化・設定
│   ├── models/             # データモデル
│   │   └── database.py     # データベース操作クラス
│   ├── sgpo/               # POファイル処理モジュール
│   │   ├── core.py             # SGPOFile実装
│   │   └── duplicate_checker.py  # 重複チェック機能
│   └── types/              # 型定義
│       └── po_entry.py     # POエントリ型定義
├── tests/                  # テストコード
└── run.py                  # 起動スクリプト
```

## 主要コンポーネント

### 1. コア機能 (`sgpo_editor.core`)

#### ViewerPOFile (`viewer_po_file.py`)
POファイルの読み書きを担当する中核クラス。データベースと連携してPOエントリを管理し、フィルタリングや検索機能を提供します。

```python
# 主な機能
- load(path): POファイルを読み込む
- save(path): POファイルを保存する
- get_entries(): エントリの一覧を取得
- update_entry(entry): エントリを更新する
- get_stats(): 統計情報を取得する
- search_entries(search_text): エントリを検索する
- get_filtered_entries(): フィルタリングされたエントリを取得
```

### 2. POファイル処理 (`sgpo_editor.sgpo`)

#### SGPOFile (`core.py`)
POファイルを安全に処理するための拡張クラス。polibをベースに、SmartGit用の機能拡張を行っています。

```python
# 主な機能
- from_file(filename): ファイルからSGPOFileインスタンスを作成
- from_text(text): テキストからSGPOFileインスタンスを作成
- import_pot(pot): POTファイルからエントリをインポート
- find_by_key(msgctxt, msgid): キーに一致するエントリを検索
- sort(): エントリをソート
- check_duplicates(): 重複エントリをチェック
- diff(other): 2つのPOファイル間の差分を比較
```

### 3. GUI (`sgpo_editor.gui`)

#### MainWindow (`main_window.py`)
GUIアプリケーションのメインウィンドウ。メニュー、ツールバー、ドックウィジェットなどの管理を行います。各種マネージャークラス（TableManager、UIManager、FileHandlerなど）を使用して処理を委譲しています。

```python
# 主な機能
- open_file(file_path): POファイルを開く
- save_file(): 現在のPOファイルを保存
- save_file_as(): 別名で保存
- _on_entry_selected(): エントリ選択時の処理
- _on_entry_updated(): エントリ更新時の処理
- _on_filter_changed(): フィルター変更時の処理
```

#### TableManager (`table_manager.py`)
POエントリテーブルの表示と操作を管理するクラス。エントリの表示、ソート、選択などを処理します。

```python
# 主な機能
- update_table(): テーブル表示を更新
- select_entry(): エントリを選択
- _on_header_clicked(): ヘッダークリック時のソート処理
```

#### EntryEditor (`widgets/entry_editor.py`)
翻訳エントリを編集するためのウィジェット。msgctxt、msgid、msgstrの表示と編集機能、およびFuzzyフラグの切り替えを提供します。

```python
# 主な機能
- set_entry(entry): エントリを設定
- _on_apply_clicked(): 適用ボタンクリック時の処理
- set_layout_type(layout_type): レイアウトタイプを設定
- _emit_text_changed(): テキスト変更イベント発行
```

#### SearchWidget (`widgets/search.py`)
検索機能を提供するウィジェット。テキスト検索とフィルタリング機能を備えています。

#### StatsWidget (`widgets/stats.py`)
統計情報を表示するウィジェット。翻訳済み、未翻訳、要確認などの数を表示します。

### 4. データモデル (`sgpo_editor.models`)

#### Database (`database.py`)
POエントリを管理するデータベース。SQLiteを使用してエントリの永続化と検索を行います。

#### EntryModel (`gui/models/entry.py`)
POエントリのデータモデル。GUIとコア機能の間のデータ変換を担当します。

#### StatsModel (`gui/models/stats.py`)
統計情報のデータモデル。翻訳の進捗状況を表すデータを保持します。

## 技術スタック

- **Python 3.8以上**
- **GUI**: PySide6（Qt for Python）
- **POファイル解析**: polib
- **CLI**: typer
- **ターミナル表示**: rich
- **データ検証**: pydantic
- **ビルドシステム**: hatchling

## アーキテクチャパターン

このプロジェクトは主にMVCパターンに基づいて設計されています：

- **Model**: `sgpo_editor.core.ViewerPOFile`、`sgpo_editor.models`、`sgpo_editor.gui.models`
- **View**: `sgpo_editor.gui.widgets`
- **Controller**: `sgpo_editor.gui.main_window.MainWindow` および各種マネージャークラス

## 主要な処理フロー

1. アプリケーション起動（`run.py` → `sgpo_editor.gui.main_window.main()`）
2. メインウィンドウ表示（`MainWindow`）
3. POファイルを開く（`MainWindow.open_file()` → `FileHandler.open_file()` → `ViewerPOFile.load()`）
4. エントリ一覧表示（`TableManager.update_table()`）
5. エントリ選択（`TableManager._on_item_selection_changed()` → `MainWindow._on_entry_selected()` → `EntryEditor.set_entry()`）
6. エントリ編集（`EntryEditor._on_text_changed()` → `EntryEditor._emit_text_changed()` → `EntryEditor._on_apply_clicked()` → `MainWindow._on_entry_updated()` → `ViewerPOFile.update_entry()`）
7. POファイル保存（`MainWindow.save_file()` → `FileHandler.save_file()` → `ViewerPOFile.save()`）

## 拡張ポイント

1. **新しいウィジェット**: `sgpo_editor.gui.widgets`に新しいウィジェットを追加することで、UIを拡張できます
2. **POファイル処理の拡張**: `sgpo_editor.sgpo.SGPOFile`を拡張することで、POファイル処理機能を追加できます
3. **新しいデータモデル**: `sgpo_editor.models`に新しいモデルを追加することで、データ処理を拡張できます
4. **レイアウトのカスタマイズ**: `EntryEditor.set_layout_type()`を使用して、エディタのレイアウトをカスタマイズできます

## 設定と状態管理

- **QSettings**: アプリケーションの設定と状態（ウィンドウサイズ、ドックウィジェットの位置など）を保存・復元
- **ロギング**: `logging`モジュールを使用して、アプリケーションのログを記録

## テスト

テストは`tests`ディレクトリに配置されており、pytestフレームワークを使用しています。単体テスト、統合テスト、UIテストなど、様々なレベルのテストを行っています。
