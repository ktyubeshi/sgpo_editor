# PO Viewer モジュール詳細

## 1. sgpo

### 概要
POファイル（gettext翻訳ファイル）を安全に処理するための独自実装モジュール。polibをベースに拡張機能を提供しています。

### 主要クラス

#### SGPOFile (`core.py`)
POファイルを処理する中核クラス。

```python
class SGPOFile:
    """SmartGit用のPOファイル操作クラス"""
    
    # POファイルのメタデータのベース辞書
    META_DATA_BASE_DICT: Dict[str, str] = {
        "Project-Id-Version": "SmartGit",
        "Report-Msgid-Bugs-To": "https://github.com/syntevo/smartgit-translations",
        # ...
    }
    
    @classmethod
    def from_file(cls, filename: str) -> SGPOFile:
        """ファイルからSGPOFileインスタンスを作成"""
        
    @classmethod
    def from_text(cls, text: str) -> SGPOFile:
        """テキストからSGPOFileインスタンスを作成"""
        
    def import_unknown(self, unknown: SGPOFile) -> None:
        """未知のエントリをインポート"""
        
    def import_mismatch(self, mismatch: SGPOFile) -> None:
        """不一致のエントリをインポート"""
        
    def import_pot(self, pot: SGPOFile) -> None:
        """POTファイルからエントリをインポート"""
        
    def delete_extracted_comments(self) -> None:
        """抽出されたコメントを削除"""
        
    def find_by_key(self, msgctxt: str, msgid: str) -> Optional[polib.POEntry]:
        """キーに一致するエントリを検索"""
        
    def sort(self, *, key: Optional[Any] = None, reverse: bool = False) -> None:
        """エントリをソート"""
        
    def format(self) -> None:
        """POファイルをフォーマット"""
        
    def save(self, fpath: Optional[str] = None, repr_method: str = "__unicode__", newline: Optional[str] = "\n") -> None:
        """POファイルを保存"""
        
    def get_key_list(self) -> List[KeyTuple]:
        """全エントリのキーのリストを返す"""
        
    def check_duplicates(self) -> List[DuplicateEntry]:
        """重複エントリをチェック"""
        
    def diff(self, other: SGPOFile) -> DiffResult:
        """2つのPOファイル間の差分を比較"""
```

#### DiffStatus (`core.py`)
差分の状態を表す列挙型。

```python
class DiffStatus(str, Enum):
    """差分の状態を表すEnum"""
    NEW = "new"
    REMOVED = "removed"
    MODIFIED = "modified"
```

#### KeyTuple (`core.py`)
POファイルのエントリを一意に識別するためのキークラス。

```python
class KeyTuple(BaseModel):
    """POファイルのエントリを一意に識別するためのキー"""
    model_config = ConfigDict(frozen=True)  # イミュータブルにする（NamedTupleと同様）

    msgctxt: str
    msgid: str
```

#### DiffEntry, DiffResult (`core.py`)
POファイルの差分情報を表すクラス。

```python
class DiffEntry(BaseModel):
    """POファイルのエントリの差分情報"""
    key: KeyTuple
    status: DiffStatus
    old_value: Optional[str] = None
    new_value: Optional[str] = None

class DiffResult(BaseModel):
    """POファイル間の差分結果"""
    new_entries: list[DiffEntry] = []
    removed_entries: list[DiffEntry] = []
    modified_entries: list[DiffEntry] = []
```

### ヘルパー関数

```python
def pofile(filename: str) -> SGPOFile:
    """ファイルからSGPOFileインスタンスを作成するヘルパー関数"""
    return SGPOFile.from_file(filename)

def pofile_from_text(text: str) -> SGPOFile:
    """テキストからSGPOFileインスタンスを作成するヘルパー関数"""
    return SGPOFile.from_text(text)
```

## 2. sgpo_editor.core

### 概要
POファイルの読み書きや管理を行うコア機能を提供するモジュール。

### 主要クラス

#### ViewerPOFile (`viewer_po_file.py`)
POファイルの読み書きを担当する中核クラス。

```python
class ViewerPOFile:
    """POファイルを読み書きするクラス"""
    
    def __init__(self, path: Optional[Union[str, Path]] = None):
        """初期化"""
        self._po_file: Optional[POFileProtocol] = None
        self._db: DatabaseProtocol = Database()
        self._modified = False
        self._path: Optional[Path] = None
        self._entries: List[EntryModel] = []
        self._filtered_entries: List[EntryModel] = []
        self._filter_text: str = ""
        self._show_translated: bool = True
        self._show_untranslated: bool = True
        self._show_fuzzy: bool = True
        
        if path:
            self.load(path)
    
    @property
    def file_path(self) -> Optional[Path]:
        """ファイルパスを取得"""
        return self._path
    
    @property
    def modified(self) -> bool:
        """変更フラグを取得"""
        return self._modified
    
    def load(self, path: Union[str, Path]) -> None:
        """POファイルを読み込む"""
        
    def save(self, path: Optional[Union[str, Path]] = None) -> None:
        """POファイルを保存する"""
        
    def get_entries(self, filter_text: Optional[str] = None, search_text: Optional[str] = None,
                   sort_column: Optional[str] = None, sort_order: Optional[str] = None,
                   flags: Optional[List[str]] = None, exclude_flags: Optional[List[str]] = None,
                   only_fuzzy: bool = False, only_translated: bool = False,
                   only_untranslated: bool = False) -> List[EntryModel]:
        """エントリの一覧を取得"""
        
    def get_entry(self, entry_id: int) -> Optional[EntryModel]:
        """エントリを取得"""
        
    def get_entry_by_key(self, key: str) -> Optional[EntryModel]:
        """キーでエントリを取得"""
        
    def update_entry(self, entry: EntryModel) -> None:
        """エントリを更新する"""
        
    def reorder_entries(self, entry_ids: List[int]) -> None:
        """エントリの表示順序を変更"""
        
    def get_stats(self) -> StatsModel:
        """統計情報を取得する"""
        
    def search_entries(self, search_text: str) -> List[EntryModel]:
        """エントリを検索する"""
        
    def save_po_file(self) -> None:
        """現在のパスにPOファイルを保存する"""
        
    def get_filtered_entries(self, filter_text: Optional[str] = None,
                            show_translated: Optional[bool] = None,
                            show_untranslated: Optional[bool] = None,
                            show_fuzzy: Optional[bool] = None,
                            search_text: Optional[str] = None,
                            sort_column: Optional[str] = None,
                            sort_order: Optional[str] = None) -> List[EntryModel]:
        """フィルタリングされたエントリの一覧を取得する"""
```

#### プロトコル定義

```python
class SequenceProtocol(Protocol[T_co]):
    """シーケンスのプロトコル定義"""
    
    def __iter__(self) -> Iterator[T_co]: ...
    def __len__(self) -> int: ...
    def __contains__(self, item: object) -> bool: ...
    def __getitem__(self, index: int) -> T_co: ...

@runtime_checkable
class POFileProtocol(Protocol):
    """POファイルのプロトコル定義"""
    
    def __iter__(self) -> Iterator[POEntry]: ...
    def __len__(self) -> int: ...
    # ...

class DatabaseProtocol(Protocol):
    """データベースのプロトコル定義"""
    
    def clear(self) -> None: ...
    def add_entries_bulk(self, entries: List[Dict[str, Any]]) -> None: ...
    def update_entry(self, key: str, entry: Dict[str, Any]) -> None: ...
    # ...
```

## 3. sgpo_editor.gui

### 概要
GUIコンポーネントを提供するモジュール。PySide6（Qt for Python）を使用しています。

### 主要クラス

#### MainWindow (`main_window.py`)
GUIアプリケーションのメインウィンドウ。

```python
class MainWindow(QMainWindow):
    """メインウィンドウ"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self.setWindowTitle("PO Editor")
        self.resize(800, 600)

        # POファイル
        self.current_po: Optional[ViewerPOFile] = None
        self.current_entry_index: int = 0
        self.total_entries: int = 0
        self._display_entries: List[str] = []

        # ウィジェット
        self.entry_editor = EntryEditor()
        self.stats_widget = StatsWidget()
        self.search_widget = SearchWidget(
            on_filter_changed=self._update_table,
            on_search_changed=self._on_search_changed,
        )
        
        # ...
    
    def _create_actions(self) -> None:
        """アクションを作成"""
        
    def _create_menus(self) -> None:
        """メニューを作成"""
        
    def _create_toolbars(self) -> None:
        """ツールバーを作成"""
        
    def _create_dock_widgets(self) -> None:
        """ドックウィジェットを作成"""
        
    def _restore_dock_states(self) -> None:
        """ドックウィジェットの状態を復元"""
        
    def _save_dock_states(self) -> None:
        """ドックウィジェットの状態を保存"""
        
    def open_file(self, file_path: Optional[str] = None) -> None:
        """POファイルを開く"""
        
    def save_file(self) -> None:
        """現在のPOファイルを保存"""
        
    def save_file_as(self) -> None:
        """別名で保存"""
        
    def _update_table(self) -> None:
        """テーブル表示を更新"""
        
    def _on_entry_selected(self, current: QModelIndex, previous: QModelIndex) -> None:
        """エントリ選択時の処理"""
        
    def _on_entry_updated(self, entry_id: int) -> None:
        """エントリ更新時の処理"""
```

#### EntryEditor (`widgets/entry_editor.py`)
翻訳エントリを編集するためのウィジェット。

```python
class LayoutType(Enum):
    """レイアウトタイプ"""
    LAYOUT1 = auto()  # msgctxt上部、msgid/msgstr下部横並び
    LAYOUT2 = auto()  # 前のレイアウト（左右分割）

class EntryEditor(QWidget):
    """POエントリ編集用ウィジェット"""
    
    text_changed = Signal()
    apply_clicked = Signal()
    entry_changed = Signal(int)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初期化"""
        super().__init__(parent)
        self._current_entry = None
        self._current_layout = LayoutType.LAYOUT1
        
        # ...
    
    @property
    def current_entry(self) -> Optional[EntryModel]:
        """現在のエントリを取得"""
        return self._current_entry
    
    @property
    def current_entry_number(self) -> Optional[int]:
        """現在のエントリ番号を取得"""
        if self._current_entry:
            return self._current_entry.id
        return None
    
    def _on_apply_clicked(self) -> None:
        """適用ボタンクリック時の処理"""
        
    def _on_text_changed(self) -> None:
        """テキストが変更されたときの処理"""
        
    def _on_fuzzy_changed(self, state: int) -> None:
        """Fuzzyチェックボックスの状態が変更されたときの処理"""
        
    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリを設定"""
        
    def get_layout_type(self) -> LayoutType:
        """現在のレイアウトタイプを取得"""
        return self._current_layout
    
    def set_layout_type(self, layout_type: LayoutType) -> None:
        """レイアウトタイプを設定"""
```

#### SearchWidget (`widgets/search.py`)
検索機能を提供するウィジェット。

#### StatsWidget (`widgets/stats.py`)
統計情報を表示するウィジェット。

## 4. sgpo_editor.models

### 概要
データモデルを提供するモジュール。

### 主要クラス

#### Database (`database.py`)
POエントリを管理するデータベース。

#### EntryModel (`gui/models/entry.py`)
POエントリのデータモデル。

```python
class EntryModel:
    """POエントリのデータモデル"""
    
    def __init__(self, id: int, key: str, msgctxt: str, msgid: str, msgstr: str, flags: List[str], comments: List[str]) -> None:
        """初期化"""
        self.id = id
        self.key = key
        self.msgctxt = msgctxt
        self.msgid = msgid
        self.msgstr = msgstr
        self.flags = flags
        self.comments = comments
    
    @property
    def is_fuzzy(self) -> bool:
        """fuzzyフラグがあるかどうか"""
        return "fuzzy" in self.flags
    
    @property
    def is_translated(self) -> bool:
        """翻訳済みかどうか"""
        return bool(self.msgstr)
    
    @property
    def is_untranslated(self) -> bool:
        """未翻訳かどうか"""
        return not self.is_translated
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書に変換"""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntryModel":
        """辞書からインスタンスを作成"""
```

#### StatsModel (`gui/models/stats.py`)
統計情報のデータモデル。

```python
class StatsModel:
    """統計情報のデータモデル"""
    
    def __init__(self, total: int = 0, translated: int = 0, untranslated: int = 0, fuzzy: int = 0) -> None:
        """初期化"""
        self.total = total
        self.translated = translated
        self.untranslated = untranslated
        self.fuzzy = fuzzy
    
    @property
    def translated_percent(self) -> float:
        """翻訳済みの割合"""
        if self.total == 0:
            return 0.0
        return (self.translated / self.total) * 100
    
    @property
    def untranslated_percent(self) -> float:
        """未翻訳の割合"""
        if self.total == 0:
            return 0.0
        return (self.untranslated / self.total) * 100
    
    @property
    def fuzzy_percent(self) -> float:
        """fuzzyの割合"""
        if self.total == 0:
            return 0.0
        return (self.fuzzy / self.total) * 100
```

## 5. sgpo_editor.types

### 概要
型定義を提供するモジュール。

### 主要クラス

#### POEntry (`po_entry.py`)
POエントリの型定義。

```python
class POEntry(Protocol):
    """POエントリのプロトコル定義"""
    
    msgid: str
    msgstr: str
    msgctxt: Optional[str]
    flags: List[str]
    comment: Optional[str]
    tcomment: Optional[str]
    occurrences: List[Tuple[str, str]]
    
    # ...
```
