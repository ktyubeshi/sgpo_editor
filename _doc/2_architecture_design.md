---
created: 2025-03-12T16:43
updated: 2025-04-15T10:30
---
# SGPO Editor アーキテクチャ設計

## 1. アーキテクチャ概要

SGPO Editorは、Model-View-Controller (MVC) アーキテクチャパターンに基づいて設計されています。このパターンにより、データ処理（Model）、ユーザーインターフェース（View）、およびビジネスロジック（Controller）の分離が実現され、コードの保守性と拡張性が向上しています。また、ファサードパターンを導入して、UI層とコア層の結合度を低減しています。

### 主要コンポーネント

```
┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
│                    │      │                    │      │                    │
│       Model        │◄────►│     Controller     │◄────►│        View        │
│                    │      │                    │      │                    │
└────────────────────┘      └────────────────────┘      └────────────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
│                    │      │                    │      │                    │
│   POファイルデータ    │      │    イベント処理     │      │     UI コンポーネント  │
│                    │      │                    │      │                    │
└────────────────────┘      └────────────────────┘      └────────────────────┘
```

## 2. レイヤー構成

SGPOエディタは以下の主要レイヤーで構成されています：

### プレゼンテーション層（GUI）
- ユーザーインターフェースコンポーネント
- イベント処理
- ビューの管理
- **ファサードクラス**: UI操作とコア機能を橋渡しする抽象化レイヤー

### ビジネスロジック層
- POファイル操作
- フィルタリング
- 検索
- 統計計算
- **キャッシュ管理**: パフォーマンス最適化のためのデータキャッシュ

### データアクセス層
- POファイルの読み込み/保存
- エントリデータの管理
- インメモリデータベース

### 共通・ユーティリティ層
- 共通関数
- ヘルパーユーティリティ
- ロギング

## 3. コンポーネント詳細

### 3.1 モデルコンポーネント

#### PoFile クラス
POファイルのデータモデルを表現し、ファイルの読み込み、保存、および操作機能を提供します。

```python
class PoFile:
    """POファイルを扱うクラス"""
    
    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)
        self.po = sgpo.pofile(str(self.file_path))
        self._modified = False
    
    def save(self, file_path: str | Path | None = None) -> None:
        """POファイルを保存する"""
        # 実装詳細...
```

#### ViewerPOFile クラス（リファクタリング後の構成）
UIと連携するためのPOファイル表示モデル。エントリのフィルタリングや検索機能を提供します。

このクラスはリファクタリングにより、以下のように責務分割された複数のクラスの集合体として構成されています：

```
┌─────────────────────────────────┐
│       ViewerPOFileRefactored     │
│    (ViewerPOFile としてexport)    │
└─────────────────────────────────┘
              │
              │ 継承
              ▼
┌─────────────────────────────────┐
│        ViewerPOFileStats        │
│      (統計情報と保存機能)         │
└─────────────────────────────────┘
              │
              │ 継承
              ▼
┌─────────────────────────────────┐
│       ViewerPOFileUpdater       │
│     (エントリ更新関連の機能)      │
└─────────────────────────────────┘
              │
              │ 継承
              ▼
┌─────────────────────────────────┐
│       ViewerPOFileFilter        │
│     (フィルタリング関連の機能)    │
└─────────────────────────────────┘
              │
              │ 継承
              ▼
┌─────────────────────────────────┐
│    ViewerPOFileEntryRetriever   │
│     (エントリ取得関連の機能)      │
└─────────────────────────────────┘
              │
              │ 継承
              ▼
┌─────────────────────────────────┐
│       ViewerPOFileBase          │
│   (基本的な初期化とファイル読込)  │
└─────────────────────────────────┘
              │
              │ 依存
              ▼
┌─────────────┐     ┌─────────────┐
│ CacheManager │◄───►│DatabaseAccessor│
└─────────────┘     └─────────────┘
```

各クラスの責務:
- **ViewerPOFileBase**: ファイル読み込みと基本初期化
- **ViewerPOFileEntryRetriever**: エントリの取得と検索
- **ViewerPOFileFilter**: フィルタリングと条件管理
- **ViewerPOFileUpdater**: エントリの更新と変更管理
- **ViewerPOFileStats**: 統計計算とファイル保存
- **ViewerPOFileRefactored**: 上記クラスを統合した最終的なインターフェース

#### EntryCacheManager クラス
エントリデータのキャッシュを一元管理し、パフォーマンスを向上させるクラスです。

```python
class EntryCacheManager:
    """POエントリのキャッシュを管理するクラス
    
    複数2種類のキャッシュを管理し、ViewerPOFileの責務を軽減します:
    1. complete_: 完全なEntryModelオブジェクトのキャッシュ
    3. filtered_entries_cache: フィルタリング結果のキャッシュ
    
    最適化機能:
    1. 使用頻度ベースのキャッシュ保持
    2. キャッシュサイズの自動調整
    3. 非同期プリフェッチ
    """
    
    def __init__(self):
        # キャッシュデータ構造
        self._complete_ = {}
        self._filtered_entries_cache = []
        # キャッシュ管理フラグ
        self._force_filter_update = False
        # 実装詳細...
```

#### DatabaseAccessor クラス
インメモリデータベースへのアクセスを抽象化するクラスです。

```python
class DatabaseAccessor:
    """データベースアクセスを抽象化するクラス
    
    インメモリSQLiteデータベースへのアクセスを提供し、
    クエリの構築や結果の変換を担当します。
    """
    
    def __init__(self, database):
        self.database = database
        # 実装詳細...
```

#### データベースコンポーネント

##### InMemoryEntryStore クラス
ViewerPOFileの内部キャッシュとして機能する、インメモリSQLiteデータベースを提供します。アプリケーション終了時にデータは消失し、永続化はPOファイルへの保存で行われます。フィルタリングとソートのためのクエリ機能を提供します。

```python
class InMemoryEntryStore:
    """インメモリSQLiteデータベースを使用したデータストア"""
    
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self._create_tables()
    
    def add_entries(self, entries: list):
        """エントリをデータベースに追加"""
        # 実装詳細...
```

##### EvaluationDatabase クラス
LLM評価データを永続化するためのサイドカーデータベース。POファイルと同じディレクトリに.evaldb拡張子で保存され、アプリケーション再起動後も評価データを保持します。

```python
class EvaluationDatabase:
    """LLM評価データを永続化するサイドカーデータベース"""
    
    def __init__(self, po_file_path: str | Path):
        self.db_path = Path(str(po_file_path) + ".evaldb")
        self.conn = sqlite3.connect(str(self.db_path))
        # 実装詳細...
```

### 3.2 ビューコンポーネント

#### MainWindow クラス
アプリケーションのメインウィンドウを表現し、他のすべてのUIコンポーネントを統合します。

```python
class MainWindow(QMainWindow):
    """メインウィンドウ"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # コンポーネントの初期化...
```

#### TableManager クラス
POエントリテーブルの表示と管理を担当します。

#### EntryEditor クラス
選択されたPOエントリの編集インターフェースを提供します。

#### StatsWidget クラス
翻訳の統計情報を表示します。

#### SearchWidget クラス
検索とフィルタリング機能を提供します。

### 3.3 ファサードコンポーネント

#### EntryEditorFacade クラス
エントリ編集に関連する操作をカプセル化し、UIとコア層の間を抽象化します。

```python
class EntryEditorFacade(QObject):
    """エントリ編集に関連する操作をカプセル化するファサードクラス
    
    責務:
    1. エントリエディタコンポーネントへの操作のカプセル化
    2. エントリ更新ロジックの一元管理
    3. エントリ変更の検知と通知
    4. ステータスメッセージの管理
    """
    
    # シグナル定義
    entry_applied = Signal(int)
    entry_changed = Signal()
    
    def __init__(self, entry_editor, get_current_po, show_status):
        # 実装詳細...
```

#### EntryListFacade クラス
エントリリスト表示に関連する操作をカプセル化し、テーブル操作とPOファイル操作を橋渡しします。

```python
class EntryListFacade(QObject):
    """エントリリスト表示に関連する操作をカプセル化するファサードクラス
    
    責務:
    1. テーブル表示の更新と管理
    2. エントリの検索とフィルタリング
    3. エントリ選択状態の管理
    4. ViewerPOFileとテーブル表示の同期
    """
    
    # シグナル定義
    selection_changed = Signal(object)
    filter_changed = Signal()
    
    def __init__(self, table, get_current_po, search_widget):
        # 実装詳細...
```

#### ReviewDialogFacade クラス
レビューダイアログと評価データベースの間を抽象化し、レビュー関連の操作をカプセル化します。

```python
class ReviewDialogFacade(QObject):
    """レビューダイアログに関連する操作をカプセル化するファサードクラス
    
    責務:
    1. レビューダイアログとデータベースの間の仲介
    2. レビュー関連のデータアクセスを抽象化
    3. ウィジェットとデータベースの結合度を下げる
    """
    
    # シグナル定義
    comment_added = Signal()
    score_updated = Signal()
    
    def __init__(self, database=None):
        # 実装詳細...
```

### 3.4 コントローラーコンポーネント

#### FileHandler クラス
ファイル操作（開く、保存、新規作成）を処理します。

```python
class FileHandler:
    """ファイル操作を担当するハンドラクラス"""
    
    def __init__(self, parent):
        """初期化"""
        self.parent = parent
        self.current_po = None
        self.file_path = None
```

#### EventHandler クラス
ユーザーインターフェースイベントの処理を担当します。ファサードパターンの導入により、一部の責務はファサードクラスに移行されています。

#### UIManager クラス
レイアウトと表示の管理を担当します。

## 4. データフロー

### 4.1 POファイルを開く
1. ユーザーが「ファイルを開く」アクションを実行
2. FileHandlerがダイアログを表示してファイル選択を処理
3. 選択されたファイルがPoFileクラスを通じて読み込まれる
4. ViewerPOFileのloadメソッドが呼び出され、データがロードされる
5. DatabaseAccessorを通じてInMemoryEntryStoreにデータが格納される
6. EntryCacheManagerのキャッシュがクリアされる
7. EntryListFacadeを通じてTableManagerがテーブルを更新
8. StatsWidgetが統計情報を更新

### 4.2 エントリの編集
1. ユーザーがテーブルでエントリを選択
2. EntryListFacadeが選択イベントを処理
3. 選択されたエントリのキーが取得される
4. ViewerPOFileからEntryModelが取得される（キャッシュ優先）
5. EntryEditorFacadeを通じてEntryEditorにEntryModelが設定される
6. ユーザーがエントリを編集し保存する
7. EntryEditorFacadeのapply_changesメソッドが呼び出される
8. ViewerPOFileのupdate_entryメソッドが呼び出される
9. データベースとキャッシュが更新される
10. EntryListFacadeを通じてテーブルが更新される
11. StatsWidgetが統計情報を更新

### 4.3 検索とフィルタリング

#### データベースアクセスにおける search_text（キーワード検索）仕様
- `DatabaseAccessor.get_filtered_entries` および `advanced_search` の両メソッドは、`search_text` が `None` または空文字列 `""` の場合、「フィルタなし」として全件返す。
- SQLレベルでは `if search_text:` の分岐により、WHERE句にキーワード条件が追加されない。
- 今後は「フィルタなし＝必ず空文字列 `""`」に統一し、UI/Facade/Component間で `None` を使わない方針とする。

1. ユーザーが検索条件を入力
2. SearchWidgetがイベントを発行
3. EntryListFacadeがイベントを処理し、update_filterメソッドを呼び出す
4. ViewerPOFileのget_filtered_entriesメソッドにフィルタ条件が渡される
5. フィルタキャッシュが確認され、必要に応じて再計算される
6. フィルタリング結果がEntryListFacadeに返される
7. EntryListFacadeがTableManagerを通じてテーブルを更新

## 5. コンポーネント間の依存関係

```
┌─────────────────────────────────────────────────────┐
│                     MainWindow                       │
└─────────────────────────────────────────────────────┘
          │            │             │
          ▼            ▼             ▼
┌────────────┐  ┌─────────────┐  ┌─────────────┐
│ FileHandler │  │ EventHandler │  │  UIManager  │
└────────────┘  └─────────────┘  └─────────────┘
          │            │             │
          └────────────┼─────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                     ファサード層                     │
├─────────────┬─────────────────────┬─────────────────┤
│EntryEditorFacade│   EntryListFacade   │ReviewDialogFacade│
└─────────────┴─────────────────────┴─────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│                   ViewerPOFile                       │
└─────────────────────────────────────────────────────┘
                  │         │
         ┌────────┘         └────────┐
         ▼                           ▼
┌─────────────────┐           ┌─────────────────┐
│ EntryCacheManager │           │ DatabaseAccessor │
└─────────────────┘           └─────────────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │InMemoryEntryStore│
                              └─────────────────┘
```

### 6. キャッシュ戦略

SGPO Editor のキャッシュは **2層構成**（CompleteEntryCache / FilterResultCache）に統一されています。詳細は「2_2_dbcash_architecture.md」を参照してください。

- 行番号とキーの対応付けは UI 側 (`EntryListFacade.Rper`) が保持
- FTS5 `MATCH` 検索を前提とし、大量データでも 500ms 以内の応答をKPIとする
- キャッシュ無効化APIは `invalidate_filter_cache()` に統一
- カウンタは廃止し、性能監視は `pytest-benchmark` で実施

    *   **キャッシュ管理:** `EntryCacheManager` は Complete/Filter の 2 層キャッシュを LRU + メモリ制限で管理します。
    *   **プリフェッチ:** UI (`EntryListFacade`) が可視範囲を通知し、バックグラウンドで先読みします。
    *   **無効化:** SQLite `update_hook` から呼ばれる `invalidate_entry()` と `invalidate_filter_cache()` で整合性を保ちます。

## 7. エラー処理戦略

SGPO Editorでは、以下のエラー処理戦略を採用しています：

1. **例外処理**: 適切なtry-except構文を使用して、予期せぬエラーを処理
2. **ユーザーフレンドリーなエラーメッセージ**: 技術的なエラーを一般ユーザーが理解できるメッセージに変換
3. **ロギング**: デバッグや問題解決のためのエラーログ記録
4. **グレースフルデグラデーション**: 機能の一部が失敗しても、アプリケーション全体はできるだけ動作を継続

## 8. スケーラビリティと拡張性

SGPO Editorは以下の方法で拡張性を確保しています：

1. **モジュラー設計**: 機能ごとに分離されたモジュール構成
2. **インターフェース分離**: 実装の詳細からインターフェースを分離
3. **設定可能なコンポーネント**: カスタマイズや拡張が可能な設計
4. **ファサードパターン**: UIとコア機能の分離による拡張容易性
5. **プラグインアーキテクチャ**: 将来的なプラグインシステムのための基盤
