# PO Viewer アーキテクチャと設計パターン

## 全体アーキテクチャ

PO Viewerは主にMVC（Model-View-Controller）パターンに基づいて設計されています。各レイヤーは以下のように分離されています：

### Model層

データとビジネスロジックを担当します。

- **`sgpo_editor.core.ViewerPOFile`**: POファイルの読み書きと管理
- **`sgpo.SGPOFile`**: POファイル処理の基盤
- **`sgpo_editor.models.Database`**: データの永続化
- **`sgpo_editor.gui.models.*`**: GUIとデータの橋渡し

### View層

ユーザーインターフェースを担当します。

- **`sgpo_editor.gui.widgets.*`**: 各種ウィジェット
  - `EntryEditor`: 翻訳エントリの編集
  - `SearchWidget`: 検索とフィルタリング
  - `StatsWidget`: 統計情報の表示

### Controller層

ModelとViewの間の調整を担当します。

- **`sgpo_editor.gui.main_window.MainWindow`**: アプリケーション全体の制御
- **`sgpo_editor.cli`**: コマンドラインインターフェース

## 設計パターン

### 1. プロトコル指向設計

Pythonの`Protocol`クラスを使用して、インターフェースを定義しています。これにより、実装の詳細から抽象化され、テストやモック化が容易になります。

```python
class POFileProtocol(Protocol):
    """POファイルのプロトコル定義"""
    def __iter__(self) -> Iterator[POEntry]: ...
    def __len__(self) -> int: ...
    # ...

class DatabaseProtocol(Protocol):
    """データベースのプロトコル定義"""
    def clear(self) -> None: ...
    def add_entries_bulk(self, entries: List[Dict[str, Any]]) -> None: ...
    # ...
```

### 2. ファクトリーメソッド

`SGPOFile`クラスでは、インスタンス生成をファクトリーメソッドに委譲しています。

```python
@classmethod
def from_file(cls, filename: str) -> SGPOFile:
    """ファイルからSGPOFileインスタンスを作成"""
    # ...

@classmethod
def from_text(cls, text: str) -> SGPOFile:
    """テキストからSGPOFileインスタンスを作成"""
    # ...
```

### 3. オブザーバーパターン

Qt Signalsを使用して、オブザーバーパターンを実装しています。

```python
class EntryEditor(QWidget):
    text_changed = Signal()
    apply_clicked = Signal()
    entry_changed = Signal(int)
    # ...
```

### 4. コマンドパターン

メニューアクションとツールバーアクションを使用して、コマンドパターンを実装しています。

```python
def _create_actions(self) -> None:
    """アクションを作成"""
    self.open_action = QAction("開く...", self)
    self.open_action.setShortcut(QKeySequence.Open)
    self.open_action.triggered.connect(self.open_file)
    # ...
```

### 5. ストラテジーパターン

レイアウトタイプの切り替えに、ストラテジーパターンを使用しています。

```python
class LayoutType(Enum):
    """レイアウトタイプ"""
    LAYOUT1 = auto()  # msgctxt上部、msgid/msgstr下部横並び
    LAYOUT2 = auto()  # 前のレイアウト（左右分割）

def set_layout_type(self, layout_type: LayoutType) -> None:
    """レイアウトタイプを設定"""
    # ...
```

## データフロー

### 1. POファイルの読み込み

```
MainWindow.open_file()
    ↓
ViewerPOFile.load()
    ↓
SGPOFile.from_file()
    ↓
Database.clear()
Database.add_entries_bulk()
    ↓
MainWindow._update_table()
```

### 2. エントリの編集

```
EntryEditor.set_entry()
    ↓
EntryEditor._on_apply_clicked()
    ↓
MainWindow._on_entry_updated()
    ↓
ViewerPOFile.update_entry()
    ↓
Database.update_entry()
```

### 3. POファイルの保存

```
MainWindow.save_file()
    ↓
ViewerPOFile.save()
    ↓
SGPOFile.save()
```

## データアーキテクチャ

SGPOエディタでは、POファイルの読み込み層と内部データモデル層を明確に分離し、拡張性と保守性を高めています。

### データレイヤーの構成

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  POファイル     │ ──→ │ データ変換レイヤー │ ──→ │ 内部データモデル │
│  (外部データ)   │ ←── │                  │ ←── │               │
└─────────────────┘      └──────────────────┘      └─────────────────┘
```

#### 1. POファイル操作層

外部データ（POファイル）の読み書きを担当します。

- **`sgpo_editor.po.PoFile`**: POファイルの基本的な読み書き機能を提供
- **`sgpo_editor.core.ViewerPOFile`**: POファイルの拡張読み書き機能とデータベース連携
- **`sgpo.SGPOFile`**: POファイル処理の基盤実装

#### 2. データ変換レイヤー

外部データから内部データモデルへの変換、およびその逆方向の変換を担当します。

- **`sgpo_editor.models.EntryModel.from_po_entry`**: POEntryからEntryModelへの変換
- **`sgpo_editor.models.EntryModel.update_po_entry`**: EntryModelからPOEntryへの反映
- **`sgpo_editor.types.po_entry.POEntry`**: POEntryのプロトコル定義（型安全性の確保）

#### 3. 内部データモデル層

アプリケーション内部で使用するデータモデルを定義します。

- **`sgpo_editor.models.EntryModel`**: POエントリの内部表現（Pydanticモデル）
- **`sgpo_editor.models.StatsModel`**: 統計情報の内部表現
- **`sgpo_editor.models.database.Database`**: データの永続化と検索機能

### データの独立性と拡張性

#### POファイルとデータモデルの分離

SGPOエディタでは、POファイルのデータ構造と内部データモデルを明確に分離しています。これにより以下の利点があります：

1. **拡張性の確保**
   - 内部データモデルには、POファイルに存在しない独自のフィールドや計算プロパティを追加可能
   - 例: `EntryModel.is_translated`, `EntryModel.is_untranslated`など

2. **型安全性の向上**
   - Pydanticを使用した型検証と変換
   - プロトコルによるインターフェース定義

3. **機能拡張の容易さ**
   - LLMを利用した翻訳レビューなど、POファイルに保存できない情報を内部で扱える
   - 独自のメタデータや状態管理が可能

#### データ変換メカニズム

データの双方向変換により、内部データと外部データの整合性を維持しています：

```python
# POエントリから内部モデルへの変換
entry_model = EntryModel.from_po_entry(po_entry)

# 内部モデルからPOエントリへの反映
entry_model.update_po_entry()
```

### 将来的な拡張性

このアーキテクチャにより、以下のような拡張が容易になります：

1. **LLM連携機能**
   - 翻訳候補の生成
   - 翻訳品質の評価
   - 翻訳レビューコメントの保存

2. **高度な検索・フィルタリング**
   - 内部データモデルに独自のインデックスやメタデータを追加
   - 複雑なクエリによる検索

3. **カスタムメタデータ**
   - 翻訳者情報
   - レビュー状態
   - 優先度や期限などのプロジェクト管理情報

4. **データ同期機能**
   - 外部サービスとの連携
   - バージョン管理システムとの統合

### 実装例

内部データモデルの例（EntryModel）：

```python
class EntryModel(BaseModel):
    """POエントリのPydanticモデル実装"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    _po_entry: Optional[POEntry] = None  # 元のPOEntryへの参照
    
    # POエントリの基本フィールド
    key: str = ""
    msgid: str = ""
    msgstr: str = ""
    msgctxt: Optional[str] = None
    flags: List[str] = Field(default_factory=list)
    
    # 計算プロパティ（POファイルには直接存在しない）
    @computed_field
    @property
    def is_fuzzy(self) -> bool:
        return "fuzzy" in self.flags
        
    @computed_field
    @property
    def is_translated(self) -> bool:
        return bool(self.msgstr) and not self.is_fuzzy
    
    # POファイルとの変換メソッド
    @classmethod
    def from_po_entry(cls, po_entry: POEntry, position: int = 0) -> 'EntryModel':
        """POEntryからEntryModelを作成"""
        # 変換ロジック
        
    def update_po_entry(self) -> None:
        """EntryModelの内容をPOEntryに反映"""
        # 反映ロジック
        
    # 将来的な拡張フィールド例
    # llm_review: Optional[str] = None
    # llm_suggestions: List[str] = Field(default_factory=list)
    # review_status: Optional[str] = None
```

## データモデル拡張仕様

#### POエントリの完全対応

内部データモデル（EntryModel）は、POファイルエントリの全ての情報を保持可能な設計になっています：

```
white-space
#  translator-comments       -> tcomment フィールド
#. extracted-comments        -> comment フィールド
#: reference...              -> occurrences/references フィールド
#, flag...                   -> flags フィールド
#| msgctxt previous-context  -> previous_msgctxt フィールド
#| msgid previous-untrans... -> previous_msgid フィールド
msgctxt context              -> msgctxt フィールド
msgid untranslated-string    -> msgid フィールド
msgstr translated-string     -> msgstr フィールド
```

これらのフィールドは、POファイルと完全な互換性を持ちながら、内部処理のための最適化された形式で保持されます。

#### 拡張レビュー機能

アプリケーション独自の機能として、以下のレビュー関連フィールドを内部データモデルに追加しています：

1. **レビューコメント**
   - 翻訳者や校正者が追加できるコメント
   - 複数の履歴を保持可能

2. **評価スコア**
   - 翻訳品質の評価（0-100のスコア）
   - カテゴリ別評価（正確性、自然さ、一貫性など）

3. **自動チェック結果**
   - ルールベースの検証結果
   - エラーコードとメッセージのリスト
   - 重要度レベル（エラー、警告、情報）

これらの拡張フィールドはPOファイルには保存されませんが、内部データベースに保存され、アプリケーション内で活用されます。将来的には、これらのデータをカスタムフォーマットで外部ファイルとしてエクスポート/インポートする機能も検討しています。

## 状態管理

### 1. アプリケーション設定

Qt の `QSettings` を使用して、アプリケーションの設定と状態を管理しています。

```python
def _restore_dock_states(self) -> None:
    """ドックウィジェットの状態を復元"""
    settings = QSettings()
    if settings.contains("dock_states"):
        self.restoreState(settings.value("dock_states"))

def _save_dock_states(self) -> None:
    """ドックウィジェットの状態を保存"""
    settings = QSettings()
    settings.setValue("dock_states", self.saveState())
```

### 2. POファイルの状態

`ViewerPOFile` クラスで、POファイルの状態（変更フラグなど）を管理しています。

```python
@property
def modified(self) -> bool:
    """変更フラグを取得"""
    return self._modified
```

## エラー処理

例外処理とロギングを組み合わせて、エラー処理を行っています。

```python
try:
    # 処理
except Exception as e:
    logger.error(f"エラーが発生しました: {e}")
    logger.debug(traceback.format_exc())
    QMessageBox.critical(self, "エラー", f"エラーが発生しました: {e}")
```

## 拡張性

### 1. 新しいウィジェットの追加

`sgpo_editor.gui.widgets` パッケージに新しいウィジェットを追加することで、UIを拡張できます。

### 2. POファイル処理の拡張

`sgpo.SGPOFile` クラスを拡張することで、POファイル処理機能を追加できます。

### 3. 新しいデータモデルの追加

`sgpo_editor.models` パッケージに新しいモデルを追加することで、データ処理を拡張できます。

## パフォーマンス最適化

### 1. データベースの使用

SQLiteデータベースを使用して、大量のPOエントリを効率的に管理しています。

### 2. 遅延読み込み

必要に応じてPOエントリを読み込むことで、メモリ使用量を最適化しています。

### 3. キャッシュ

フィルタリングや検索結果をキャッシュすることで、パフォーマンスを向上させています。

```python
self._filtered_entries: List[EntryModel] = []
```

## セキュリティ考慮事項

### 1. 入力検証

ユーザー入力を適切に検証し、不正な入力を防止しています。

### 2. ファイルパスの検証

ファイルパスを検証して、ディレクトリトラバーサル攻撃などを防止しています。

```python
@staticmethod
def _validate_filename(filename: str) -> bool:
    """ファイル名が有効かどうかを検証"""
    # ...
```

## テスト戦略

### 1. ユニットテスト

各コンポーネントの機能を個別にテストします。

### 2. 統合テスト

複数のコンポーネントの連携をテストします。

### 3. GUIテスト

GUIの動作をテストします。
