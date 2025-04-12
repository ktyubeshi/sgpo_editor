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
    
    複数種類のキャッシュを管理し、ViewerPOFileの責務を軽減します:
    1. complete_entry_cache: 完全なEntryModelオブジェクトのキャッシュ
    2. entry_basic_info_cache: 基本情報のみのキャッシュ
    3. filtered_entries_cache: フィルタリング結果のキャッシュ
    
    最適化機能:
    1. 使用頻度ベースのキャッシュ保持
    2. キャッシュサイズの自動調整
    3. 非同期プリフェッチ
    """
    
    def __init__(self):
        # キャッシュデータ構造
        self._complete_entry_cache = {}
        self._entry_basic_info_cache = {}
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

## 6. キャッシュ戦略

SGPO Editorでは、パフォーマンスを向上させるために多層的なキャッシュ戦略を採用しています。

### 6.1 キャッシュレイヤー

1. **完全なエントリキャッシュ** (EntryCacheManager._complete_entry_cache)
   - 詳細な編集操作に使用される完全なEntryModelオブジェクトを保持
   - ユースケース: エントリの詳細表示や編集時
   - キー: エントリID（通常は位置を表す文字列）
   - 値: すべてのフィールドを持つEntryModelオブジェクト

2. **基本情報キャッシュ** (EntryCacheManager._entry_basic_info_cache)
   - テーブル表示に必要な基本情報のみを持つEntryModelオブジェクトを保持
   - ユースケース: テーブル一覧表示など、基本情報のみ必要な場合
   - キー: エントリID
   - 値: 基本フィールド（msgid, msgstr, fuzzy, obsoleteなど）のみのEntryModelオブジェクト

3. **フィルタ結果キャッシュ** (EntryCacheManager._filtered_entries_cache)
   - 特定のフィルタ条件に対する結果リストを保持
   - ユースケース: 同じフィルタ条件で繰り返し検索する場合
   - キー: フィルタ条件のハッシュ
   - 値: フィルタリングされたEntryModelオブジェクトのリスト

4. **行インデックスマッピング** (EntryCacheManager._row_key_map)
   - テーブルの行インデックスとエントリキーのマッピングを保持
   - ユースケース: UI操作でのエントリ参照
   - キー: テーブルの行インデックス
   - 値: エントリのキー

### 6.2 キャッシュ最適化機能

1. **使用頻度ベースのキャッシュ保持**
   - アクセス回数をカウントし、頻繁に使用されるエントリを優先的に保持
   - 実装: `_access_counter`と`_last_access_time`を使用

2. **キャッシュサイズの自動調整**
   - メモリ使用量に応じてキャッシュサイズを動的に調整
   - 最大キャッシュサイズと最小必須サイズ（LRU）の設定

3. **非同期プリフェッチ**
   - バックグラウンドスレッドでの先読みにより、UI応答性を向上
   - ユーザーの表示エリアに基づいて、次に必要となるエントリを予測

4. **キャッシュ無効化メカニズム**
   - エントリ更新時に関連するキャッシュを無効化
   - フラグベースのシステムにより、キャッシュの一貫性を確保

### 6.3 キャッシュパフォーマンスの監視

1. **ヒット率計測**
   - 各キャッシュレイヤーでのヒット/ミスを計測
   - 実装: `_complete_cache_hits`, `_complete_cache_misses`などのカウンター

2. **定期的ログ出力**
   - 設定された間隔でキャッシュパフォーマンス指標をログに出力
   - 実装: `_check_and_log_performance`メソッド

3. **メモリ使用量監視**
   - キャッシュの合計サイズと潜在的なメモリリークを監視
   - 実装: キャッシュサイズの監視と調整機能

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
