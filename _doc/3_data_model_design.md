---
created: 2025-03-12T16:44
updated: 2025-03-12T16:44
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

### 2.2 クラス構造

#### PoFile クラス

基本的なPOファイル操作を提供するクラスです。

```python
class PoFile:
    """POファイルを扱うクラス"""
    
    def __init__(self, file_path: str | Path):
        """
        POファイルを読み込む
        
        Args:
            file_path: POファイルのパス
        """
        self.file_path = Path(file_path)
        self.po = sgpo.pofile(str(self.file_path))
        self._modified = False
    
    @property
    def modified(self) -> bool:
        """変更されているかどうか"""
        return self._modified
    
    def save(self, file_path: str | Path | None = None) -> None:
        """POファイルを保存する"""
        # 実装詳細...
    
    def set_msgstr(self, entry, msgstr: str) -> None:
        """翻訳文を設定する"""
        # 実装詳細...
```

#### ViewerPOFile クラス

UIと連携するためのPOファイル表示モデル。エントリのフィルタリングや検索機能を提供します。

```python
class ViewerPOFile:
    """UI表示用のPOファイルモデル"""
    
    def __init__(self, po_file: PoFile):
        """初期化"""
        self.po_file = po_file
        self.entries = self._prepare_entries()
    
    def get_entries(self):
        """すべてのエントリを取得"""
        return self.entries
    
    def get_filtered_entries(self, filter_text: str, search_text: str, match_mode: str):
        """フィルタと検索条件に基づいてエントリをフィルタリング"""
        # 実装詳細...
    
    def get_stats(self):
        """翻訳の統計情報を取得"""
        # 実装詳細...
```

**注: ViewerPOFileはファイル読み込み、データベース操作（キャッシュ）、フィルタリング、ソート、統計計算など多くの責務を持っており、単一責任の原則から考えると機能が肥大化しています。今後の改善として、キャッシュ管理を`EntryCacheManager`クラスに、データベースアクセスを`DatabaseAccessor`クラスに分割することを検討すべきです。**

#### POEntry クラス

個々の翻訳エントリを表すクラス（sgpoライブラリで提供）。

主な属性:
- `msgid`: 翻訳元の文字列
- `msgstr`: 翻訳後の文字列
- `msgctxt`: 翻訳コンテキスト
- `obsolete`: 廃止されたエントリかどうか
- `flags`: 特殊フラグ（fuzzy等）

### 2.3 データベースクラス構造

#### Database クラス

**重要: このクラスはインメモリデータストアとして機能し、ViewerPOFileの内部キャッシュ層として使用されます。アプリケーション終了時にデータは消失します。永続化はPOファイルへの保存で行われます。**

```python
class Database:
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

#### EvaluationDatabase クラス

**重要: このクラスはLLM評価データをSQLiteファイルに永続化するサイドカーデータベースとして機能します。POファイルと同じディレクトリに.evaldb拡張子で保存され、アプリケーション再起動後も評価データを保持します。**

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

## 3. データフロー

### 3.1 POファイル読み込み

1. FileHandlerがPOファイルのパスを取得
2. PoFileクラスのインスタンスを作成し、ファイルを読み込む
3. ViewerPOFileクラスがPoFileを受け取り、UI表示用データに変換
4. ViewerPOFileがデータをインメモリのDatabaseに格納
5. TableManagerがViewerPOFileからエントリリストを取得し、テーブルを構築

```
ファイルパス → PoFile → ViewerPOFile → Database(インメモリ) → TableManager → UI表示
```

### 3.2 POエントリ編集

1. ユーザーがテーブルでエントリを選択
2. MainWindowがViewerPOFileから選択されたエントリ情報を取得
3. EntryEditorにエントリデータを表示
4. ユーザーが編集を実行
5. EntryEditorが変更内容をMainWindowに通知
6. MainWindowがViewerPOFileを通じてエントリを更新
7. ViewerPOFileはインメモリDatabaseとPoFileの両方を更新
8. TableManagerがテーブルを更新

```
ユーザー操作 → EntryEditor → MainWindow → ViewerPOFile → Database(インメモリ)/PoFile → 保存
```

### 3.3 検索・フィルタリング

1. ユーザーがSearchWidgetで検索条件を入力
2. SearchWidgetが変更を通知
3. MainWindowが新しい検索条件をViewerPOFileに渡す
4. ViewerPOFileがインメモリDatabaseにフィルタリング条件を渡す
5. Databaseがフィルタリングしたエントリリストを返す
6. ViewerPOFileがエントリオブジェクトをキャッシュからロードまたは新規作成
7. TableManagerがテーブルを更新

```
検索条件 → ViewerPOFile → Database(フィルタリング) → キャッシュ → TableManager → UI表示
```

### 3.4 LLM評価と永続化

1. ユーザーがLLM評価を実行
2. EvaluationDialogがLLM APIを呼び出し
3. 評価結果をEntryModelに設定
4. ViewerPOFileを通じてEntryModelを更新
5. EvaluationDatabaseに評価データを永続化

```
ユーザー操作 → EvaluationDialog → LLM API → EntryModel → ViewerPOFile → EvaluationDatabase(永続化)
```

## 4. 状態管理

### 4.1 翻訳エントリの状態

エントリ状態は以下のように定義されています：

- **未翻訳**: `msgstr`が空
- **翻訳済み**: `msgstr`に値が設定済み
- **要確認 (fuzzy)**: `fuzzy`フラグが設定されている
- **廃止 (obsolete)**: `obsolete`属性が`True`

### 4.2 ファイル状態の管理

`PoFile`クラスは内部的に`_modified`フラグを管理し、ファイルが変更されたかどうかを追跡します。これにより、未保存の変更がある場合に適切な警告を表示できます。

## 5. データバリデーション

エントリ編集時に以下のバリデーションが実行されます：

1. プレースホルダーの一致チェック（`%s`、`{0}`などのフォーマット指定子）
2. 末尾の空白や改行などの一致
3. HTMLタグの整合性（存在する場合）

## 6. データ永続化

### 6.1 ファイル保存

PoFileクラスのsaveメソッドを使用して、POファイルへの変更を永続化します：

```python
def save(self, file_path: str | Path | None = None) -> None:
    """POファイルを保存する
    
    Args:
        file_path: 保存先のパス。Noneの場合は元のファイルに上書き保存
    """
    save_path = Path(file_path) if file_path else self.file_path
    self.po.save(str(save_path))
    self._modified = False
    
    # 別名で保存した場合は、そのファイルを新しい作業ファイルとする
    if file_path:
        self.file_path = save_path
```

### 6.2 バックアップ戦略

変更を保存する前に、自動的にバックアップファイル（元のファイル名 + `.bak`）を作成します。これにより、保存操作が失敗した場合でもデータ損失を防ぎます。

## 7. データアクセスパターン

### 7.1 ファクトリパターン

ViewerPOFileはPoFileインスタンスを受け取り、UI表示に最適化されたデータ構造を提供します。これはファクトリパターンの一種として機能します。

### 7.2 イテレータパターン

エントリコレクションは反復処理が可能で、TableManagerなどでの表示処理に使用されます。

### 7.3 オブザーバーパターン

データ変更時の通知にはシグナル/スロットメカニズム（PySide6）を使用し、オブザーバーパターンを実装しています。
