---
created: 2025-03-12T16:44
updated: 2025-04-15T11:00
---
# SGPO Editor データモデル設計

## 1. データモデル概要

SGPO Editorは主にPOファイル（gettext翻訳ファイル）のデータを扱います。このドキュメントでは、アプリケーション内のデータモデルの構造、関係、および操作方法について詳細に説明します。

## 2. 主要データモデル

### 2.1 POファイルモデル

POファイルは翻訳リソースのコンテナであり、複数の翻訳エントリを含みます。

```
┌───────────────────────────────────────┐
│              POファイル                │
├───────────────────────────────────────┤
│ - メタデータ（翻訳者情報、言語情報など） │
│ - 複数の翻訳エントリ                   │
└───────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│              翻訳エントリ              │
├───────────────────────────────────────┤
│ - msgid（原文）                        │
│ - msgstr（翻訳文）                     │
│ - msgctxt（コンテキスト）              │
│ - コメント                             │
│ - 翻訳状態                             │
└───────────────────────────────────────┘
```

### 2.2 EntryModel クラス

翻訳エントリを表現するための統一的なデータモデルです。Pydanticを使用した型安全なモデルとして実装されています。

```python
class EntryModel(BaseModel):
    """翻訳エントリのデータモデル
    
    POエントリのデータを表現するPydanticモデル。
    型安全性と検証機能を提供します。
    """
    
    key: str
    position: int
    msgid: str
    msgstr: str = ""
    msgctxt: Optional[str] = None
    fuzzy: bool = False
    obsolete: bool = False
    flags: List[str] = []
    comment: Optional[str] = None
    tcomment: Optional[str] = None
    references: List[Tuple[str, str]] = []
    
    # 複数形関連
    msgid_plural: Optional[str] = None
    msgstr_plural: Dict[int, str] = {}
    
    # LLM評価関連
    quality_score: Optional[float] = None
    review_comments: Dict[str, str] = {}
    check_results: Dict[str, Any] = {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntryModel":
        """辞書からEntryModelを作成する"""
        # 実装詳細...
    
    def to_dict(self) -> Dict[str, Any]:
        """EntryModelを辞書に変換する"""
        # 実装詳細...
```

### 2.3 クラス構造

#### POInterface と POEntry インターフェース
PO操作ライブラリ（sgpo, polib）の違いを抽象化するインターフェース層です。

```python
class POEntry(Protocol):
    """POエントリのインターフェース
    
    異なるPOライブラリのエントリを統一的に扱うためのプロトコル。
    """
    
    msgid: str
    msgstr: str
    msgctxt: Optional[str]
    flags: List[str]
    obsolete: bool
    comment: Optional[str]
    tcomment: Optional[str]
    occurrences: List[Tuple[str, str]]
    
    # 複数形サポート
    msgid_plural: Optional[str]
    msgstr_plural: Dict[int, str]
```

#### ViewerPOFile クラス階層
リファクタリングにより、責務ごとに分割された複数のクラスで構成されています。

```
┌─────────────────────────────────┐ 
│       ViewerPOFileRefactored     │ ← ViewerPOFileとしてエクスポート
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐ 
│        ViewerPOFileStats        │ ← 統計情報と保存機能を担当
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐ 
│       ViewerPOFileUpdater       │ ← エントリの更新管理
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐ 
│       ViewerPOFileFilter        │ ← フィルタリング機能
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐ 
│    ViewerPOFileEntryRetriever   │ ← エントリ取得機能
└─────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────┐ 
│       ViewerPOFileBase          │ ← 基本初期化とファイル読込
└─────────────────────────────────┘
```

```python
class ViewerPOFileBase:
    """POファイルを読み込み、表示するための基本クラス
    
    このクラスは、キャッシュ管理とデータベースアクセスの責務を分離し、
    EntryCacheManagerとDatabaseAccessorを利用して実装されています。
    
    主な機能:
    1. POファイルの非同期読み込み: asyncioを使用してUIの応答性を向上
    2. エントリの取得と管理: キャッシュとデータベースを連携してエントリを効率的に管理
    """
    
    def __init__(
        self,
        cager: Optional[EntryCacheManager] = None,
        db: Optional[DatabaseAccessor] = None,
    ):
        """初期化
        
        Args:
            cager: キャッシュマネージャ（Noneの場合は新規作成）
            db: データベースアクセサ（Noneの場合はDBなし）
        """
        self.path = None
        self.library_type = POLibraryType.SGPO
        
        # 依存性注入によるキャッシュとデータベースの連携
        self.cager = cager or EntryCacheManager()
        self.db = db
        
        # データベースがない場合は新規作成して接続
        if not self.db:
            db = InMemoryEntryStore()
            self.db = DatabaseAccessor(db)
```

### 2.4 データベースクラス構造

#### InMemoryEntryStore クラス

ViewerPOFileの内部キャッシュとして機能するインメモリSQLiteデータベースを提供します。

```python
class InMemoryEntryStore:
    """インメモリSQLiteデータベースを使用したデータストア
    
    このクラスはViewerPOFileの内部キャッシュとして機能し、
    POファイルのエントリをSQLiteのインメモリデータベースに格納します。
    フィルタリングやソートを高速に行うためのクエリ機能を提供します。
    """
    
    def __init__(self):
        """インメモリデータベースを初期化"""
        self.conn = sqlite3.connect(":memory:")
        self._create_tables()
    
    def add_entries(self, entries: list[EntryModel]) -> None:
        """エントリをデータベースに追加"""
        # 実装詳細...
    
    def get_entries(self, filter_expr: str, order_by: str) -> list[tuple]:
        """フィルタ条件に一致するエントリを取得"""
        # 実装詳細...
    
    def update_entry(self, entry: EntryModel) -> None:
        """エントリを更新"""
        # 実装詳細...
```

#### DatabaseAccessor クラス

インメモリデータベースとのインタラクションを抽象化し、より高レベルの操作を提供します。

```python
class DatabaseAccessor:
    """データベースアクセスを抽象化するクラス
    
    InMemoryEntryStoreへのアクセスを提供し、
    SQLクエリの構築や結果の変換などを担当します。
    """
    
    def __init__(self, database: InMemoryEntryStore):
        """初期化
        
        Args:
            database: データベースインスタンス
        """
        self.database = database
    
    def get_entries_by_filter(self, conditions: FilterConditions) -> List[Dict[str, Any]]:
        """フィルタ条件に一致するエントリを取得
        
        Args:
            conditions: フィルタ条件
            
        Returns:
            条件に一致するエントリのリスト（辞書形式）
        """
        # 検索条件からSQL式を構築
        # 実装詳細...
    
    def advanced_search(
        self, 
        search_text: str, 
        fields: List[str], 
        case_sensitive: bool = False,
        exact_match: bool = False
    ) -> List[Dict[str, Any]]:
        """高度な検索機能
        
        Args:
            search_text: 検索テキスト
            fields: 検索対象フィールド
            case_sensitive: 大文字/小文字を区別するか
            exact_match: 完全一致検索か
            
        Returns:
            検索結果のエントリリスト
        """
        # 実装詳細...
```

#### EvaluationDatabase クラス

LLM評価データを永続化するサイドカーデータベースとして機能します。

```python
class EvaluationDatabase:
    """LLM評価データを永続化するサイドカーデータベース
    
    このクラスは各POファイルに対応する評価データを永続化します。
    POファイルのパスに基づいて.evaldb拡張子のファイルを作成し、
    エントリのLLM評価結果（スコア、レビューコメント）を保存します。
    msgctxtとmsgidの組み合わせをキーとして、POエントリと評価データを関連付けます。
    """
    
    def __init__(self, po_file_path: str | Path):
        """評価データベースを初期化
        
        Args:
            po_file_path: 対応するPOファイルのパス
        """
        self.db_path = Path(str(po_file_path) + ".evaldb")
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
    
    def save_evaluation(self, entry_key: tuple, score: float, comments: dict) -> None:
        """評価データを保存"""
        # 実装詳細...
    
    def get_evaluation(self, entry_key: tuple) -> dict:
        """評価データを取得"""
        # 実装詳細...
```

## 3. キャッシュ管理システム

### 3.1 EntryCacheManager クラス

エントリデータのキャッシュを一元管理し、パフォーマンスを向上させるためのクラスです。

```python
class EntryCacheManager:
    """POエントリのキャッシュを管理するクラス
    
    このクラスは、POエントリの各種キャッシュを管理し、キャッシュの一貫性を保つための
    機能を提供します。主に以下の2種類のキャッシュを管理します：
    
    1. complete_entry_cache: 完全なEntryModelオブジェクトのキャッシュ
       - 用途: エントリの詳細情報が必要な場合（編集時など）に使用
       - キー: エントリのキー（通常は位置を表す文字列）
       - 値: 完全なEntryModelオブジェクト（すべてのフィールドを含む）
    
    2. filtered_entries_cache: フィルタリング結果のキャッシュ
       - 用途: 同じフィルタ条件での再検索を高速化
       - キー: フィルタ条件を表す文字列（filtered_entries_cache_key）
       - 値: フィルタ条件に一致するEntryModelオブジェクトのリスト

※ 行番号とキーのマッピングは UI 側（EntryListFacade）が管理します。
       
    最適化機能:
    - キャッシュサイズの自動調整: メモリ使用量に基づいてキャッシュサイズを動的に調整
    - 非同期プリフェッチ: バックグラウンドでの先読みによるUI応答性の向上
    """
    
    DEFAULT_MAX_CACHE_SIZE = 10000
    DEFAULT_LRU_SIZE = 1000
    PREFETCH_BATCH_SIZE = 50
    
    def __init__(self):
        """キャッシュマネージャの初期化"""
        # 完全なEntryModelオブジェクトのキャッシュ
        self.complete_entry_cache: EntryModelMap = {}
        
        # フィルタ結果のキャッシュ
        self.filtered_entries_cache: EntryModelList = []
        self.filtered_entries_cache_key: str = ""
        
        # キャッシュ制御フラグ
        self.cache_enabled: bool = True
        self.force_filter_update: bool = False
        
        # 非同期プリフェッチ関連
        self.prefetch_lock = threading.RLock()
        self.prefetch_queue: Set[str] = set()
        self.prefetch_in_progress: bool = False
        
    def get_complete_entry(self, key: str) -> Optional[EntryModel]:
        """完全なエントリをキャッシュから取得する"""
        if not self.cache_enabled:
            return None

        entry = self.complete_entry_cache.get(key)
        if entry:
            # キャッシュヒット
            return entry
        else:
            # キャッシュミス
            return None

    def cache_complete_entry(self, key: str, entry: EntryModel) -> None:
        """完全なエントリをキャッシュに保存する"""
        if not self.cache_enabled:
            return

        self.complete_entry_cache[key] = entry
        self.update_access_stats(key)
        self.check_cache_size()

    def update_entry_in_cache(self, key: str, entry: EntryModel) -> None:
        """エントリの更新をキャッシュに反映する"""
        if not self.cache_enabled:
            return

        # 完全なエントリキャッシュを更新
        self.complete_entry_cache[key] = entry

        # フィルタ結果キャッシュを無効化
        self.set_force_filter_update(True)
```

### 3.2 キャッシュ基本操作

```python
# EntryCacheManagerのメソッド
def prefetch_visible_entries(self, visible_keys: List[str], fetch_callback=None) -> None:
    """表示中のエントリをプリフェッチする
    
    テーブルに表示されている（または表示されそうな）エントリを
    事前にキャッシュに読み込みます。これにより、スクロール時の
    エントリ表示をスムーズにします。
    
    Args:
        visible_keys: 表示中または表示予定のエントリキーのリスト
        fetch_callback: キーのリストを受け取り、EntryModelのリストを返すコールバック関数
    """
    if not self.cache_enabled or not visible_keys:
        return
        
    # すでにキャッシュにあるキーを除外
    keys_to_fetch = [
        key for key in visible_keys if key not in self.complete_entry_cache
    ]
    
    if not keys_to_fetch:
        return
        
    with self.prefetch_lock:
        self.prefetch_queue.update(keys_to_fetch)
        
        if self.prefetch_in_progress:
            return
            
        self.prefetch_in_progress = True
        
    # 非同期でプリフェッチを実行
    threading.Thread(
        target=self.async_prefetch, 
        args=(fetch_callback,), 
        daemon=True
    ).start()
```

## 4. データフロー

### 4.1 POファイル読み込み

1. FileHandlerがPOファイルのパスを取得
2. ViewerPOFileクラスのloadメソッドが呼び出される
3. POLibraryTypeに応じたPOファイルアダプタが選択される
4. POエントリがEntryModelオブジェクトに変換される
5. DatabaseAccessorを通じてエントリがインメモリデータベースに格納される
6. EntryCacheManagerのキャッシュがクリアされる
7. TableManagerがViewerPOFileからエントリリストを取得し、テーブルを構築

```
ファイルパス → ViewerPOFile.load → POAdapter → EntryModel変換 → DatabaseAccessor → InMemoryEntryStore
                                             ↓
                                  EntryCacheManager(キャッシュクリア)
```

### 4.2 フィルタリングと検索

1. ユーザーがSearchWidgetでフィルタや検索条件を入力
2. ViewerPOFileのget_filtered_entriesメソッドが呼び出される
3. EntryCacheManagerのフィルタキャッシュが確認される
4. キャッシュミスまたは強制更新の場合、DatabaseAccessorを通じてクエリが実行される
5. 取得されたエントリデータがEntryModelオブジェクトに変換される
6. 変換されたオブジェクトがキャッシュに保存され、結果として返される
7. TableManagerが結果を受け取り、テーブルを更新

```
ユーザー入力 → ViewerPOFile.get_filtered_entries → EntryCacheManager(キャッシュ確認)
                                                    ↓ (キャッシュミス/強制更新)
                                      ager(キャッシュ保存)
                                                    ↓
                                                  結果返却 → TableManagerによる表示
```

### 4.3 エントリ編集
{{ ... }}
1. ユーザーがテーブルでエントリを選択
2. EntryListFacadeがViewerPOFileからEntryModelを取得（完全キャッシュ優先）
3. EntryEditorFacadeを通じてEntryEditorにEntryModelが設定される
4. ユーザーがエントリを編集し、Applyボタンをクリック
5. EntryEditorFacadeのapply_changesメソッドが呼び出される
6. ViewerPOFile.update_entryメソッドが呼び出される
7. DatabaseAccessorを通じてインメモリDBが更新される
8. EntryCacheManagerの各キャッシュが更新/無効化される
9. TableManagerが更新され、変更が画面に反映される

```
ユーザー選択 → EntryListFacade → ViewerPOFile.y → EntryCacheManager(キャッシュ取得) → EntryModel → EntryEditorFacade → EntryEditor
                                                                                                ↑
ユーザー編集 → EntryEditor → EntryEditorFacade → ViewerPOFile.update_entry → DatabaseAccessor → InMemoryEntryStore（DB更新）
                                                                             → EntryCacheManager(キャッシュ更新)
```

## 5. データ関連の最適化戦略

### 5.1 メモリ最適化

1. **遅延ロード**: 詳細情報は必要になったときのみロード
2. **キャッシュ制限**: 最大キャッシュサイズと優先度ベースの排出戦略
3. **参照型オブジェクト**: 共通情報の複製を避け、参照共有

### 5.2 DB最適化

1. **インデックス**: 頻繁に検索される列にインデックスを設定
2. **最適なクエリ**: EXPLAIN句を使用した効率的なクエリ設計
3. **一括操作**: 複数更新を単一トランザクションでバッチ処理

## 6. データモデルの拡張ポイント

### 6.1 LLM評価拡張

EntryModelクラスは、LLM評価情報を格納するフィールドを備えています：

```python
class EntryModel(BaseModel):
    # 基本フィールド
    key: str
    position: int
    msgid: str
    tr: str = ""
    
    # LLM評価関連フィールド
    quality_score: Optional[float] = None  # 0.0～1.0の品質スコア
    review_comments: Dict[str, str] = {}   # カテゴリごとのレビューコメント
    check_results: Dict[str, Any] = {}     # 自動チェック結果
```

### 6.2 複数形サポート

EntryModelクラスは、複数形翻訳をサポートするフィールドを持っています：

```python
class EntryModel(BaseModel):
    # 基本フィールド
    msgid: str
    tr: str = ""
    
    # 複数形関連フィールド
    msgid_plural: Optional[str] = None    # 複数形の原文
    tr_plural: Dict[int, str] = {}    # インデックスごとの複数形訳文
```

### 6.3 カスタムメタデータ

翻訳プロジェクト固有のメタデータ保存用の拡張モデル：

```python
class ProjectMetadata(BaseModel):
    """プロジェクト固有のメタデータモデル"""
    
    project_id: str
    terminology_db: Optional[str] = None  # 用語集DBへの参照
    client_name: Optional[str] = None
    priority: int = 0
    custom_fields: Dict[str, Any] = {}    # プロジェクト固有の追加フィールド
```