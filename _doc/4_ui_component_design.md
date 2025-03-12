# SGPO Editor UIコンポーネント設計

## 1. UI設計の基本方針

SGPO Editorは、翻訳者やローカライゼーションエンジニアがPOファイルを効率的に編集できるよう、以下の設計方針に基づいてUIを構築しています：

- **シンプルさ**: 必要最小限のコントロールと明確なレイアウト
- **効率性**: 頻繁に使用する機能へのクイックアクセス
- **柔軟性**: ユーザーの作業スタイルに合わせたカスタマイズ可能なレイアウト
- **視認性**: 翻訳状態の視覚的な表現と統計情報の明確な表示

## 2. メインウィンドウレイアウト

メインウィンドウは以下の主要コンポーネントで構成されています：

```
┌─────────────────────────────────────────────────────────┐
│ メニューバー                                            │
├─────────────────────────────────────────────────────────┤
│ ツールバー                                              │
├───────────────────┬─────────────────────────────────────┤
│                   │                                     │
│                   │                                     │
│  エントリテーブル   │          エントリエディタ           │
│                   │                                     │
│                   │                                     │
├───────────────────┼─────────────────────────────────────┤
│   検索・フィルタ    │           統計情報                 │
├───────────────────┴─────────────────────────────────────┤
│ ステータスバー                                          │
└─────────────────────────────────────────────────────────┘
```

### 2.1 レイアウトタイプ

SGPO Editorは複数のレイアウトタイプを提供し、ユーザーの好みや作業内容に応じて切り替えることができます：

#### 標準レイアウト
デフォルトのレイアウトで、エントリテーブルとエントリエディタを横に配置します。

#### コンパクトレイアウト
小さい画面に最適化されたレイアウトで、エントリテーブルとエントリエディタを縦に配置します。

#### 拡張レイアウト
大きい画面に最適化されたレイアウトで、エントリテーブル、エントリエディタ、および統計情報を並べて表示します。

## 3. UIコンポーネント詳細

### 3.1 メニューバー

メニューバーには以下の主要メニューが含まれています：

#### ファイルメニュー
- 開く（Ctrl+O）
- 最近使ったファイル
- 保存（Ctrl+S）
- 名前を付けて保存（Ctrl+Shift+S）
- 終了（Alt+F4）

#### 編集メニュー
- 元に戻す（Ctrl+Z）
- やり直し（Ctrl+Y）
- コピー（Ctrl+C）
- 貼り付け（Ctrl+V）
- 検索（Ctrl+F）

#### 表示メニュー
- レイアウト切り替え
  - 標準レイアウト
  - コンパクトレイアウト
  - 拡張レイアウト
- 統計表示の切り替え
- ツールバー表示の切り替え
- ステータスバー表示の切り替え

#### ツールメニュー
- 検証
- 一括変換
- 設定

#### ヘルプメニュー
- ヘルプ
- バージョン情報

### 3.2 エントリテーブル

エントリテーブルは、POファイル内のすべての翻訳エントリを表形式で表示します。

#### 列構成
- **状態**: 翻訳状態を示すアイコン（未翻訳、翻訳済み、要確認など）
- **ID**: エントリの一意識別子
- **原文**: 翻訳元のテキスト（msgid）
- **訳文**: 翻訳後のテキスト（msgstr）
- **コンテキスト**: 翻訳コンテキスト（msgctxt）
- **コメント**: エントリに関連するコメント

#### 機能
- ソート: 各列ヘッダーをクリックすることで、その列でソート
- フィルタリング: 状態やキーワードによるフィルタリング
- コンテキストメニュー: 右クリックで追加操作を表示

#### 実装クラス
```python
class TableManager:
    """エントリテーブルの管理クラス"""
    
    def __init__(self, table: QTableWidget, get_current_po):
        """初期化"""
        self.table = table
        self.get_current_po = get_current_po
        self._setup_table()
    
    def update_table(self, filter_text="", search_text="", match_mode="部分一致"):
        """テーブルを更新する"""
        # 実装詳細...
    
    def _setup_table(self):
        """テーブルの初期設定"""
        # 実装詳細...
```

### 3.3 エントリエディタ

エントリエディタは、選択されたエントリの詳細な表示と編集を行います。

#### コンポーネント
- **原文表示エリア**: 翻訳元のテキスト（読み取り専用）
- **訳文編集エリア**: 翻訳テキストの編集
- **コンテキスト表示**: 翻訳コンテキスト情報
- **コメント表示**: エントリに関連するコメント
- **状態切り替え**: fuzzyフラグなどの状態切り替えボタン
- **ナビゲーションボタン**: 前/次のエントリへの移動ボタン

#### レイアウトタイプ
EntryEditorクラスは複数のレイアウトタイプをサポートし、表示方法をカスタマイズできます：
```python
class LayoutType(Enum):
    """レイアウトタイプの列挙型"""
    STANDARD = auto()  # 標準レイアウト
    COMPACT = auto()   # コンパクトレイアウト
    EXTENDED = auto()  # 拡張レイアウト
```

#### 実装クラス
```python
class EntryEditor(QWidget):
    """POエントリの編集ウィジェット"""
    
    text_changed = Signal()  # テキスト変更シグナル
    entry_applied = Signal(object, str)  # エントリ適用シグナル
    
    def __init__(self, parent=None):
        """初期化"""
        super().__init__(parent)
        self._setup_ui()
        self.current_entry = None
    
    def update_entry(self, entry):
        """エントリを更新する"""
        # 実装詳細...
    
    def apply_changes(self):
        """変更を適用する"""
        # 実装詳細...
```

### 3.4 検索・フィルタウィジェット

検索とフィルタリング機能を提供するコンポーネントです。

#### コンポーネント
- **フィルタドロップダウン**: 状態によるフィルタリング（すべて、未翻訳のみ、fuzzyのみなど）
- **検索テキストボックス**: キーワード検索入力フィールド
- **検索オプション**: 完全一致、部分一致などの検索モード選択
- **検索ボタン**: 検索実行ボタン

#### 実装クラス
```python
class SearchWidget(QWidget):
    """検索とフィルタリングのウィジェット"""
    
    filter_changed = Signal()  # フィルタ変更シグナル
    search_changed = Signal()  # 検索条件変更シグナル
    
    def __init__(self, on_filter_changed=None, on_search_changed=None, parent=None):
        """初期化"""
        super().__init__(parent)
        self._setup_ui()
        
        # コールバック設定
        if on_filter_changed:
            self.filter_changed.connect(on_filter_changed)
        if on_search_changed:
            self.search_changed.connect(on_search_changed)
    
    def get_search_criteria(self):
        """検索条件を取得する"""
        # 実装詳細...
```

### 3.5 統計情報ウィジェット

翻訳の進捗状況や統計情報を表示するコンポーネントです。

#### 表示情報
- **総エントリ数**: POファイル内の全エントリ数
- **翻訳済み**: 翻訳済みエントリ数と割合
- **未翻訳**: 未翻訳エントリ数と割合
- **要確認**: fuzzyフラグ付きエントリ数と割合
- **進捗バー**: 翻訳の進捗を視覚的に表示

#### 実装クラス
```python
class StatsWidget(QWidget):
    """翻訳統計情報ウィジェット"""
    
    def __init__(self, parent=None):
        """初期化"""
        super().__init__(parent)
        self._setup_ui()
    
    def update_stats(self, stats_data):
        """統計情報を更新する"""
        # 実装詳細...
```

## 4. UIイベント処理

SGPO Editorでは、PySide6のシグナル/スロットメカニズムを使用してUIイベントを処理します。

### 4.1 主要イベントフロー

#### ファイルを開く
1. `ファイルを開く`メニュー/ボタンがクリックされる
2. FileHandlerの`open_file`メソッドが呼び出される
3. ファイル選択ダイアログが表示される
4. 選択されたファイルが読み込まれ、`file_opened`シグナルが発行される
5. MainWindowが`file_opened`シグナルを受け取り、UIを更新する

#### エントリの編集
1. エントリテーブルでエントリが選択される
2. MainWindowの`_on_entry_selected`メソッドが呼び出される
3. EntryEditorが選択されたエントリで更新される
4. ユーザーがエントリを編集し、`適用`ボタンをクリックする
5. EntryEditorの`entry_applied`シグナルが発行される
6. MainWindowが変更を処理し、モデルとUIを更新する

### 4.2 イベントハンドラ

EventHandlerクラスは、主要なイベント処理ロジックを一元管理します：

```python
class EventHandler:
    """イベント処理を担当するハンドラクラス"""
    
    def __init__(self, parent):
        """初期化"""
        self.parent = parent
        # イベントハンドラの設定
    
    def on_entry_selected(self, row):
        """エントリ選択時の処理"""
        # 実装詳細...
    
    def on_entry_applied(self, entry, new_text):
        """エントリ適用時の処理"""
        # 実装詳細...
    
    def on_filter_changed(self):
        """フィルタ変更時の処理"""
        # 実装詳細...
```

## 5. UI設定と状態管理

### 5.1 設定の保存と復元

アプリケーションはQt設定機能を使用して、ウィンドウサイズ、位置、レイアウト設定などのUI状態を保存・復元します：

```python
def save_settings(self):
    """アプリケーション設定を保存する"""
    settings = QSettings("SGPO", "Editor")
    settings.setValue("geometry", self.saveGeometry())
    settings.setValue("windowState", self.saveState())
    settings.setValue("layout_type", self.current_layout_type.value)
    # その他の設定...

def restore_settings(self):
    """アプリケーション設定を復元する"""
    settings = QSettings("SGPO", "Editor")
    geometry = settings.value("geometry")
    if geometry:
        self.restoreGeometry(geometry)
    # その他の設定復元...
```

### 5.2 ドック状態の管理

UIManagerクラスは、ドックウィジェットの状態とレイアウトを管理します：

```python
class UIManager:
    """UI管理クラス"""
    
    def __init__(self, parent, components):
        """初期化"""
        self.parent = parent
        self.components = components
        self.current_layout = LayoutType.STANDARD
    
    def setup_ui(self):
        """UIのセットアップ"""
        # 実装詳細...
    
    def switch_layout(self, layout_type):
        """レイアウトを切り替える"""
        # 実装詳細...
```

## 6. アクセシビリティとユーザビリティ

SGPO Editorは以下のアクセシビリティ機能を提供します：

### 6.1 キーボードショートカット

- ファイル操作: Ctrl+O（開く）、Ctrl+S（保存）、Ctrl+Shift+S（名前を付けて保存）
- 編集操作: Ctrl+Z（元に戻す）、Ctrl+Y（やり直し）
- ナビゲーション: Alt+左右矢印（前/次のエントリ）
- 検索: Ctrl+F（検索）、F3（次を検索）

### 6.2 ステータスバー情報

ステータスバーには以下の情報が表示されます：
- 現在のファイルパス
- 保存状態（変更あり/なし）
- 現在選択中のエントリ情報
- フィルタ/検索状態

### 6.3 ツールチップ

すべての主要UIコントロールには説明的なツールチップが提供され、機能の理解を助けます。

## 7. エラー表示とフィードバック

### 7.1 エラーダイアログ

エラーが発生した場合、適切なエラーメッセージを含むダイアログを表示します：

```python
def show_error(self, title, message):
    """エラーダイアログを表示する"""
    QMessageBox.critical(self, title, message)
```

### 7.2 進捗表示

長時間の操作（大きなファイルの読み込みなど）では、進捗状況を示すプログレスバーを表示します：

```python
def show_progress(self, title, message, maximum=100):
    """進捗ダイアログを表示する"""
    progress = QProgressDialog(message, "キャンセル", 0, maximum, self)
    progress.setWindowTitle(title)
    progress.setWindowModality(Qt.WindowModal)
    return progress
```

## 8. 国際化対応

SGPO Editorは翻訳アプリケーションとして、自身も国際化（i18n）に対応しています：

- Qtの翻訳機能を使用してUIテキストを翻訳
- 日本語と英語のUI
- 右から左へ（RTL）の言語のサポート
- 日付と時刻の適切な書式設定

```python
def setup_translation(self):
    """翻訳の設定"""
    locale = QLocale.system().name()
    translator = QTranslator()
    if translator.load(f"sgpo_editor_{locale}", ":/translations"):
        QApplication.installTranslator(translator)
```
