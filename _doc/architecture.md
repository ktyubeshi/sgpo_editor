# PO Viewer アーキテクチャと設計パターン

## 全体アーキテクチャ

PO Viewerは主にMVC（Model-View-Controller）パターンに基づいて設計されています。各レイヤーは以下のように分離されています：

### Model層

データとビジネスロジックを担当します。

- **`sgpo_editor.core.ViewerPOFile`**: POファイルの読み書きと管理
- **`sgpo_editor.sgpo.SGPOFile`**: POファイル処理の基盤
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

`sgpo_editor.sgpo.SGPOFile` クラスを拡張することで、POファイル処理機能を追加できます。

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
