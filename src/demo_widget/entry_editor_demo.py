"""
エントリエディタスタンドアロンデモアプリケーション

EntryEditorウィジェットを単体でテスト・開発するためのデモアプリです。
メインアプリケーションとの互換性を維持しながら独立して動作します。
"""

import sys
import logging
from typing import Dict, List, Optional, Any
import random
from PySide6.QtCore import Qt, Signal
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
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QCheckBox,
    QPushButton,
)
from PySide6.QtGui import QColor

# モジュールのパスを確認するためのデバッグ
print(f"Python検索パス: {sys.path}")

# モジュールのインポートを試みる
try:
    print("モジュールのインポート開始")
    # 以下を試みて、成功すればモックは使用されない
    # 絶対パス形式でのインポートに変更
    from sgpo_editor.gui.widgets.entry_editor import EntryEditor, LayoutType
    from sgpo_editor.models.entry import EntryModel
    from sgpo_editor.core.constants import TranslationStatus

    print("モジュールのインポートに成功しました")

    USE_MOCK_IMPLEMENTATION = False
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    USE_MOCK_IMPLEMENTATION = True


class EntryEditor(QWidget):
    """エントリエディタのモック実装"""

    def __init__(self, parent=None):
        super().__init__(parent)
        logging.debug("EntryEditor.__init__: 初期化開始")
        self.apply_clicked = MockSignal()
        self.text_changed = MockSignal()
        self.entry_changed = MockSignal(int)
        self.database = None
        self.current_entry = None

        # UI要素の作成
        self._setup_ui()
        logging.debug("EntryEditor.__init__: 初期化完了")

    def _setup_ui(self):
        """UIセットアップ"""
        logging.debug("EntryEditor._setup_ui: UIセットアップ開始")
        layout = QVBoxLayout(self)

        # 原文ラベル
        self.msgid_label = QLabel("原文:")
        layout.addWidget(self.msgid_label)

        # 原文表示エリア
        self.msgid_display = QLabel()
        self.msgid_display.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        self.msgid_display.setWordWrap(True)
        layout.addWidget(self.msgid_display)

        # 訳文ラベル
        self.msgstr_label = QLabel("訳文:")
        layout.addWidget(self.msgstr_label)

        # 訳文編集エリア
        self.msgstr_edit = QTextEdit()
        self.msgstr_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.msgstr_edit)

        # ファジーチェックボックス
        self.fuzzy_checkbox = QCheckBox("ファジー")
        layout.addWidget(self.fuzzy_checkbox)

        # 適用ボタン
        self.apply_button = QPushButton("適用")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        layout.addWidget(self.apply_button)
        logging.debug("EntryEditor._setup_ui: UIセットアップ完了")

    def _on_apply_clicked(self):
        """適用ボタンがクリックされたときの処理"""
        if self.current_entry:
            self.current_entry.msgstr = self.msgstr_edit.toPlainText()
            self.current_entry.fuzzy = self.fuzzy_checkbox.isChecked()
            self.apply_clicked.emit()

    def _on_text_changed(self):
        """テキストが変更されたときの処理"""
        self.text_changed.emit()

    def set_entry(self, entry):
        """エントリを設定"""
        logging.debug(f"EntryEditor.set_entry: エントリ設定開始 entry={entry}")
        self.current_entry = entry
        if entry:
            logging.debug(
                f"EntryEditor.set_entry: エントリデータ設定 msgid={entry.msgid[:20]}..."
            )
            self.msgid_display.setText(entry.msgid)
            self.msgstr_edit.setPlainText(entry.msgstr)
            self.fuzzy_checkbox.setChecked(entry.fuzzy)
            self.setEnabled(True)
            self.entry_changed.emit(entry.position)
            logging.debug("EntryEditor.set_entry: エントリ変更シグナル発行")
        else:
            logging.debug("EntryEditor.set_entry: 空のエントリ設定")
            self.msgid_display.setText("")
            self.msgstr_edit.setPlainText("")
            self.fuzzy_checkbox.setChecked(False)
            self.setEnabled(False)

    def set_layout_type(self, layout_type):
        """レイアウトタイプを設定"""
        # モックなので実際には何もしない
        pass


class MockSignal:
    """シグナルをモックするクラス"""

    def __init__(self, *args):
        self.args = args
        self.connected_callbacks = []

    def connect(self, callback):
        """コールバックを接続"""
        self.connected_callbacks.append(callback)

    def emit(self, *args):
        """シグナル発火"""
        for callback in self.connected_callbacks:
            callback(*args)


class LayoutType:
    """レイアウトタイプの定数"""

    LAYOUT1 = 1
    LAYOUT2 = 2

    @staticmethod
    def get_name(layout_type):
        """レイアウトタイプの名前を取得"""
        if layout_type == LayoutType.LAYOUT1:
            return "LAYOUT1"
        else:
            return "LAYOUT2"


class EntryModel:
    """エントリモデルのモック実装"""

    def __init__(
        self,
        key="",
        msgid="",
        msgstr="",
        msgctxt=None,
        position=0,
        fuzzy=False,
        tcomment=None,
    ):
        self.key = key
        self.msgid = msgid
        self.msgstr = msgstr
        self.msgctxt = msgctxt
        self.position = position
        self.fuzzy = fuzzy
        self.tcomment = tcomment

    def get_status(self):
        if not self.msgstr:
            return TranslationStatus.UNTRANSLATED
        elif self.fuzzy:
            return TranslationStatus.FUZZY
        else:
            return TranslationStatus.TRANSLATED


class TranslationStatus:
    """翻訳ステータスの定数"""

    UNTRANSLATED = "untranslated"
    FUZZY = "fuzzy"
    TRANSLATED = "translated"
    OBSOLETE = "obsolete"


# モックデータベースクラス
class MockDatabase:
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


class EntryEditorDemo(QMainWindow):
    """エントリエディタデモアプリケーション"""

    def __init__(self):
        super().__init__()
        logging.debug("EntryEditorDemo.__init__: 初期化開始")
        self.setWindowTitle("エントリエディタデモ")
        self.resize(1000, 700)

        # メインアプリと互換性を持たせるための属性
        self._display_entries = []  # 表示中のエントリキーリスト
        self._current_po_file = MockViewerPOFile()

        # サンプルエントリを作成
        self.sample_entries = self.create_sample_entries()
        for entry in self.sample_entries:
            self._current_po_file.add_entry(entry)
            self._display_entries.append(entry.key)

        # モックデータベース
        self._database = MockDatabase()

        # UI初期化
        self._setup_ui()
        logging.debug("EntryEditorDemo.__init__: UIセットアップ完了")

        # エントリリストの初期化
        self._populate_entry_list()
        logging.debug("EntryEditorDemo.__init__: エントリリスト初期化完了")

        # 初期エントリの選択（あれば）
        if self.entry_list.count() > 0:
            self.entry_list.setCurrentRow(0)
            logging.debug("EntryEditorDemo.__init__: 初期エントリ選択完了")

        logging.debug("EntryEditorDemo.__init__: 初期化完了")

    def _setup_ui(self):
        """UIセットアップ"""
        # メインウィジェット
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)

        # メインスプリッター（リストとエディタ）
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左側: エントリリスト
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # レイアウト切替コンボボックス
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)

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
        splitter.addWidget(left_widget)
        splitter.addWidget(self.entry_editor)
        splitter.setSizes([300, 700])  # 初期サイズ比率

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
                item.setBackground(QColor(255, 0, 0, 50))  # 薄い赤
            elif entry.get_status() == TranslationStatus.FUZZY:
                item.setBackground(QColor(255, 255, 0, 50))  # 薄い黄色

            # カスタムデータとしてキーを保存
            item.setData(Qt.ItemDataRole.UserRole, entry.key)
            self.entry_list.addItem(item)

    def _on_entry_selected(self, current, previous):
        """エントリが選択されたときの処理"""
        logging.debug("EntryEditorDemo._on_entry_selected: エントリ選択イベント発生")
        if not current:
            logging.debug("EntryEditorDemo._on_entry_selected: 選択項目なし")
            self.entry_editor.set_entry(None)
            return

        # 選択されたエントリのキーを取得
        key = current.data(Qt.ItemDataRole.UserRole)
        logging.debug(
            f"EntryEditorDemo._on_entry_selected: キー '{key}' が選択されました"
        )

        # キーからエントリを取得
        selected_entry = next((e for e in self.sample_entries if e.key == key), None)

        if selected_entry:
            logging.debug(
                f"EntryEditorDemo._on_entry_selected: エントリを見つけました: {selected_entry.key}"
            )
            self.entry_editor.set_entry(selected_entry)
            self.statusBar().showMessage(f"エントリ '{key}' を選択しました")
        else:
            logging.error(
                f"EntryEditorDemo._on_entry_selected: キー '{key}' に対応するエントリが見つかりません"
            )
            self.entry_editor.set_entry(None)

    def _on_layout_changed(self, index):
        """レイアウト変更時の処理"""
        layout_type = self.layout_combo.currentData()
        self.entry_editor.set_layout_type(layout_type)
        self.statusBar().showMessage(
            f"レイアウトを変更しました: {LayoutType.get_name(layout_type)}"
        )

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
                    item.setBackground(QColor(255, 0, 0, 50))  # 薄い赤
                elif entry.get_status() == TranslationStatus.FUZZY:
                    item.setBackground(QColor(255, 255, 0, 50))  # 薄い黄色
                else:
                    item.setBackground(QColor(255, 255, 255))  # 白

                break

    def _on_text_changed(self):
        """テキストが変更されたときの処理"""
        self.statusBar().showMessage("テキストが変更されました")

    def _on_entry_changed(self, position):
        """エントリが変更されたときの処理"""
        self.statusBar().showMessage(f"エントリ位置 {position} が変更されました")

    def create_sample_entries(self):
        """サンプル翻訳エントリを作成"""
        entries = []
        for i in range(1, 101):
            fuzzy = random.choice([True, False, False])  # 約1/3の確率でファジー
            has_translation = random.choice(
                [True, True, False]
            )  # 約2/3の確率で翻訳あり

            # エントリーの生成
            entry = EntryModel(
                key=f"entry_{i}",
                msgid=f"This is source text {i}. Sample content for demonstration.",
                msgstr=f"これはサンプル訳文 {i}です。デモ用のコンテンツです。"
                if has_translation
                else "",
                position=i,
                fuzzy=fuzzy,
                tcomment=f"Translator comment for entry {i}"
                if random.choice([True, False])
                else None,
            )
            entries.append(entry)
        return entries

    def _on_entry_table_selected(self):
        """テーブルでエントリが選択されたときの処理"""
        # テーブルを削除したため、このメソッドは空にする
        pass

    def update_entry_list(self, filter_status=None):
        """エントリーリストを更新"""
        # テーブル関連の処理を削除して、リスト更新のみに変更
        self._populate_entry_list()


def main():
    """メイン関数"""
    # ログ設定
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logging.debug("デモアプリケーション開始")

    try:
        # QApplication作成
        app = QApplication(sys.argv)
        logging.debug("QApplication作成完了")

        # デモアプリケーション作成・表示
        demo = EntryEditorDemo()
        logging.debug("EntryEditorDemoインスタンス作成完了")
        demo.show()
        logging.debug("EntryEditorDemoウィンドウ表示")

        # イベントループ開始
        logging.debug("イベントループ開始")
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
