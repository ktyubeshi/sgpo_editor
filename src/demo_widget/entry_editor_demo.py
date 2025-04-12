"""
エントリエディタスタンドアロンデモアプリケーション

EntryEditorウィジェットを単体でテスト・開発するためのデモアプリです。
メインアプリケーションとの互換性を維持しながら独立して動作します。
"""

import sys
import logging
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)

# モジュールのパスを確認するためのデバッグ
print(f"Python検索パス: {sys.path}")

try:
    # sgpo_editor内の必要なモジュールをインポート
    from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
    from sgpo_editor.models.entry import EntryModel
    from sgpo_editor.core.constants import TranslationStatus

    print("モジュールのインポートに成功しました")
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    sys.exit(1)


# モックデータベースクラス
class MockDatabase:
    """モックデータベースクラス"""

    def __init__(self):
        self.entries: Dict[str, Dict] = {}
        self.entry_fields: Dict[str, Dict[str, Any]] = {}

    def update_entry(self, key: str, data: Dict) -> None:
        """エントリを更新"""
        logging.debug(f"MockDatabase.update_entry: key={key}")
        self.entries[key] = data

    def update_entry_field(self, key: str, field: str, value: Any) -> None:
        """エントリの特定フィールドを更新"""
        logging.debug(
            f"MockDatabase.update_entry_field: key={key}, field={field}, value={value}"
        )
        if key not in self.entry_fields:
            self.entry_fields[key] = {}
        self.entry_fields[key][field] = value

    def get_entry(self, key: str) -> Optional[Dict]:
        """エントリを取得"""
        return self.entries.get(key)


# モックViewerPOFileクラス
class MockViewerPOFile:
    """モックViewerPOFileクラス"""

    def __init__(self):
        self._force_filter_update = False
        self.entries = {}

    def get_filtered_entries(self) -> List[str]:
        """フィルター適用済みのエントリキーリストを取得"""
        return list(self.entries.keys())

    def add_entry(self, entry: EntryModel) -> None:
        """エントリを追加"""
        self.entries[entry.key] = entry


# サンプルエントリデータを作成する関数
def create_sample_entries() -> List[EntryModel]:
    """サンプルエントリを作成"""
    entries = []

    # サンプルエントリ1
    entry1 = EntryModel(
        key="entry1",
        msgid="This is a sample text",
        msgstr="これはサンプルテキストです",
        msgctxt="sample context",
        position=1,
        fuzzy=False,
    )
    entries.append(entry1)

    # サンプルエントリ2（未翻訳）
    entry2 = EntryModel(
        key="entry2",
        msgid="This is an untranslated text",
        msgstr="",
        msgctxt=None,
        position=2,
        fuzzy=False,
    )
    entries.append(entry2)

    # サンプルエントリ3（ファジー）
    entry3 = EntryModel(
        key="entry3",
        msgid="This is a fuzzy translation",
        msgstr="これはファジー翻訳です",
        msgctxt="fuzzy context",
        position=3,
        fuzzy=True,
    )
    entries.append(entry3)

    # サンプルエントリ4（複数行）
    entry4 = EntryModel(
        key="entry4",
        msgid="This is a multi-line\nsample text\nwith three lines",
        msgstr="これは複数行の\nサンプルテキストで\n3行あります",
        msgctxt="multiline context",
        position=4,
        fuzzy=False,
    )
    entries.append(entry4)

    # コメント付きエントリ
    entry5 = EntryModel(
        key="entry5",
        msgid="Entry with comments",
        msgstr="コメント付きエントリ",
        msgctxt="comment context",
        position=5,
        fuzzy=False,
        tcomment="翻訳者コメント: これは翻訳者コメント付きのエントリです",
    )
    entries.append(entry5)

    return entries


class EntryEditorDemo(QMainWindow):
    """エントリエディタデモアプリケーション"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("エントリエディタデモ")
        self.resize(1000, 700)

        # メインアプリと互換性を持たせるための属性
        self._display_entries = []  # 表示中のエントリキーリスト
        self._current_po_file = MockViewerPOFile()

        # サンプルエントリを作成
        self.sample_entries = create_sample_entries()
        for entry in self.sample_entries:
            self._current_po_file.add_entry(entry)
            self._display_entries.append(entry.key)

        # モックデータベース
        self._database = MockDatabase()

        # UI初期化
        self._setup_ui()

        # エントリリストの初期化
        self._populate_entry_list()

    def _setup_ui(self):
        """UIセットアップ"""
        # メインウィジェット
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # スプリッター（エントリリストとエディタを分割）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左側: コントロールパネルとエントリリスト
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # コントロールパネル
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        # レイアウト切替コンボボックス
        layout_label = QLabel("レイアウト:")
        self.layout_combo = QComboBox()
        self.layout_combo.addItem("標準レイアウト", LayoutType.LAYOUT1)
        self.layout_combo.addItem("左右分割レイアウト", LayoutType.LAYOUT2)
        self.layout_combo.currentIndexChanged.connect(self._on_layout_changed)

        control_layout.addWidget(layout_label)
        control_layout.addWidget(self.layout_combo)
        control_layout.addStretch()

        left_layout.addWidget(control_panel)

        # エントリリスト
        self.entry_list = QListWidget()
        self.entry_list.currentItemChanged.connect(self._on_entry_selected)
        left_layout.addWidget(self.entry_list)

        # 右側: エントリエディタ
        self.entry_editor = EntryEditor()
        self.entry_editor.database = self._database

        # エディタのシグナル接続
        self.entry_editor.apply_clicked.connect(self._on_apply_clicked)
        self.entry_editor.text_changed.connect(self._on_text_changed)
        self.entry_editor.entry_changed.connect(self._on_entry_changed)

        # スプリッターに追加
        splitter.addWidget(left_panel)
        splitter.addWidget(self.entry_editor)
        splitter.setSizes([200, 800])  # 初期サイズ比率

        self.setCentralWidget(main_widget)

        # ステータスバー
        self.statusBar().showMessage("エントリエディタデモ準備完了")

    def _get_current_po(self):
        """現在のPOファイルを取得するメソッド（互換性のため）"""
        return self._current_po_file

    def _populate_entry_list(self):
        """エントリリストを作成"""
        self.entry_list.clear()

        for entry in self.sample_entries:
            item = QListWidgetItem(f"{entry.key}: {entry.msgid[:20]}...")

            # 状態に応じた背景色を設定
            if entry.get_status() == TranslationStatus.UNTRANSLATED:
                item.setBackground(Qt.GlobalColor.red)
            elif entry.get_status() == TranslationStatus.FUZZY:
                item.setBackground(Qt.GlobalColor.yellow)

            # カスタムデータとしてキーを保存
            item.setData(Qt.ItemDataRole.UserRole, entry.key)
            self.entry_list.addItem(item)

    def _on_entry_selected(self, current, previous):
        """エントリが選択されたときの処理"""
        if not current:
            self.entry_editor.set_entry(None)
            return

        # 選択されたエントリのキーを取得
        key = current.data(Qt.ItemDataRole.UserRole)

        # キーからエントリを取得
        selected_entry = next((e for e in self.sample_entries if e.key == key), None)

        if selected_entry:
            self.entry_editor.set_entry(selected_entry)
            self.statusBar().showMessage(f"エントリ '{key}' を選択しました")

    def _on_layout_changed(self, index):
        """レイアウト変更時の処理"""
        layout_type = self.layout_combo.currentData()
        self.entry_editor.set_layout_type(layout_type)
        self.statusBar().showMessage(f"レイアウトを変更しました: {layout_type.name}")

    def _on_apply_clicked(self):
        """Apply ボタンクリック時の処理"""
        self.statusBar().showMessage("変更が適用されました")

        # 現在のエントリがある場合はリスト表示を更新
        current_entry = self.entry_editor.current_entry
        if current_entry:
            self._update_entry_list_item(current_entry)

    def _update_entry_list_item(self, entry):
        """エントリリストの項目を更新"""
        # エントリキーに対応するアイテムを探す
        for i in range(self.entry_list.count()):
            item = self.entry_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == entry.key:
                # 項目のテキストを更新
                item.setText(f"{entry.key}: {entry.msgid[:20]}...")

                # 状態に応じた背景色を更新
                if entry.get_status() == TranslationStatus.UNTRANSLATED:
                    item.setBackground(Qt.GlobalColor.red)
                elif entry.get_status() == TranslationStatus.FUZZY:
                    item.setBackground(Qt.GlobalColor.yellow)
                else:
                    item.setBackground(Qt.GlobalColor.white)

                break

    def _on_text_changed(self):
        """テキストが変更されたときの処理"""
        self.statusBar().showMessage("テキストが変更されました")

    def _on_entry_changed(self, position):
        """エントリが変更されたときの処理"""
        self.statusBar().showMessage(f"エントリ位置 {position} が変更されました")


def main():
    """メイン関数"""
    # ログ設定
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # QApplication作成
    app = QApplication(sys.argv)

    # スタイルシートなどがある場合は適用
    # app.setStyleSheet(...)

    # デモアプリケーション作成・表示
    demo = EntryEditorDemo()
    demo.show()

    # イベントループ開始
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
