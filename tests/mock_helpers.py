"""GUI Mocking helpers for tests.

このモジュールはテスト実行時にGUIの操作待ちを防ぐために、
Qt UIコンポーネントをモック化するヘルパーを提供します。

テストガイドラインに基づき、Qtダイアログやウィンドウのモック化、ユーザー操作のシミュレーションなどの
機能を提供し、テストの信頼性と再現性を高めます。
"""

import gc
from unittest.mock import MagicMock

from PySide6 import QtCore, QtWidgets

# モッククラスの定義


class MockMainWindow(MagicMock):
    """テストガイドラインに基づく MainWindow のモック実装

    MainWindowクラスの振る舞いをシミュレートし、実際のQtウィジェットを作成せずに
    テストを実行できるようにします。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 主要なコンポーネントをモック化
        self.entry_editor = MagicMock()
        self.stats_widget = MagicMock()
        self.search_widget = MagicMock()
        self.table_manager = MagicMock()
        self.tableView = MagicMock()
        self.table = MagicMock()
        self.current_po = None  # 初期状態ではNone

        # ファイルハンドラーのモック化
        self.file_handler = MagicMock()
        self.file_handler.current_po = None
        self.file_handler.current_filepath = None

        # アクションのモック化
        self.open_action = MagicMock()
        self.save_action = MagicMock()
        self.save_as_action = MagicMock()
        self.exit_action = MagicMock()

        # 検索条件をセットアップ
        self.search_criteria = MagicMock()
        self.search_criteria.filter = ""
        self.search_criteria.search_text = ""
        self.search_criteria.match_mode = "部分一致"
        self.search_widget.get_search_criteria.return_value = self.search_criteria

        # 主要なメソッドをモック化してデフォルトのレスポンスを設定
        self.get_current_entry = MagicMock(return_value=None)
        self.update_table = MagicMock()
        self.update_stats = MagicMock()
        self.load_po_file = MagicMock(return_value=True)
        self.save_po_file = MagicMock(return_value=True)
        self._open_file = MagicMock()
        self._save_file = MagicMock()
        self._save_file_as = MagicMock()
        self.closeEvent = MagicMock()

        # テスト対象の追加メソッド
        self._update_table = MagicMock()
        self._on_selection_changed = MagicMock()
        self._on_entry_text_changed = MagicMock()
        self._on_apply_clicked = MagicMock()
        self._save_dock_states = MagicMock()
        self._restore_dock_states = MagicMock()

        # ドックウィジェット
        self.entry_editor_dock = MagicMock()

        # 表示エントリリスト
        self._display_entries = []

    def close(self):
        """明示的にリソースを解放する

        テスト実行後に呼び出して、全てのモックをクリーンアップします。
        """
        self.entry_editor = None
        self.stats_widget = None
        self.search_widget = None
        self.table_manager = None
        self.tableView = None
        self.current_po = None

        # ガベージコレクションを実行
        gc.collect()


class MockQApplication(MagicMock):
    """テスト用のQApplicationモック

    実際のQApplicationを作成せずに、テストに必要な機能を提供します。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.top_level_widgets = []

    @classmethod
    def instance(cls):
        return cls()

    @classmethod
    def topLevelWidgets(cls):
        return []


class MockTableView(MagicMock):
    """テスト用のQTableViewモック

    選択状態や表示状態をシミュレートします。
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selectionModel = MagicMock()
        self.model = MagicMock()

        # 選択モデルの振る舞いを設定
        self.selection_changed = QtCore.Signal()
        self.selectionModel().currentChanged = self.selection_changed


def mock_file_dialog_get_open_file_name(monkeypatch, file_path=None, file_type=None):
    """
    QFileDialog.getOpenFileNameをモック化する

    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
        file_path: 返すファイルパス（Noneの場合はキャンセル）
        file_type: 返すファイルタイプ
    """
    if file_path is None:
        # キャンセルされた場合
        return_value = ("", "")
    else:
        return_value = (file_path, file_type or "All Files (*)")

    def mock_get_open_file_name(*args, **kwargs):
        return return_value

    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", mock_get_open_file_name
    )


def mock_file_dialog_get_save_file_name(monkeypatch, file_path=None, file_type=None):
    """
    QFileDialog.getSaveFileNameをモック化する

    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
        file_path: 返すファイルパス（Noneの場合はキャンセル）
        file_type: 返すファイルタイプ
    """
    if file_path is None:
        # キャンセルされた場合
        return_value = ("", "")
    else:
        return_value = (file_path, file_type or "All Files (*)")

    def mock_get_save_file_name(*args, **kwargs):
        return return_value

    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", mock_get_save_file_name
    )


def mock_message_box_question(monkeypatch, return_value=None):
    """
    QMessageBox.questionをモック化する

    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
        return_value: 返す値（デフォルトはQMessageBox.Yes）
    """
    # デフォルト値を安全に設定
    if return_value is None:
        return_value = QtWidgets.QMessageBox.StandardButton.Yes

    def mock_question(*args, **kwargs):
        return return_value

    monkeypatch.setattr(QtWidgets.QMessageBox, "question", mock_question)


def mock_message_box_information(monkeypatch):
    """
    QMessageBox.informationをモック化する

    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
    """

    def mock_information(*args, **kwargs):
        # 安全なデフォルト値を返す
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", mock_information)


def mock_message_box_warning(monkeypatch):
    """
    QMessageBox.warningをモック化する

    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
    """

    def mock_warning(*args, **kwargs):
        # 安全なデフォルト値を返す
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", mock_warning)


def mock_message_box_critical(monkeypatch):
    """
    QMessageBox.criticalをモック化する

    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
    """

    def mock_critical(*args, **kwargs):
        # 安全なデフォルト値を返す
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", mock_critical)


def wait_for_window_shown(qtbot, window):
    """
    ウィンドウが表示されるのを待機する

    Args:
        qtbot: pytest-qtのqtbotフィクスチャ
        window: 待機対象のウィンドウ
    """
    # ウィンドウが有効であることを確認
    if window is None or not isinstance(window, QtWidgets.QWidget):
        return

    window.show()
    # waitForWindowShownは非推奨なので、代わりにwaitExposedを使用
    try:
        # pytest-qt 4.2.0以降
        with qtbot.waitExposed(window):
            pass
    except AttributeError:
        # 古いバージョンのpytest-qt
        qtbot.waitForWindowShown(window)


def click_button(qtbot, button):
    """
    ボタンをクリックする

    Args:
        qtbot: pytest-qtのqtbotフィクスチャ
        button: クリック対象のボタン
    """
    # ボタンが有効であることを確認
    if button is None or not isinstance(button, QtWidgets.QWidget):
        return

    qtbot.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)


def enter_text(qtbot, widget, text):
    """
    テキストを入力する

    Args:
        qtbot: pytest-qtのqtbotフィクスチャ
        widget: 入力対象のウィジェット
        text: 入力するテキスト
    """
    # ウィジェットが有効であることを確認
    if widget is None or not isinstance(widget, QtWidgets.QWidget):
        return

    widget.clear()
    qtbot.keyClicks(widget, text)


# 高レベルモックヘルパー関数


def setup_mock_main_window(monkeypatch):
    """テスト用にMainWindowをモック化する高レベルヘルパー

    テストガイドラインにMockMainWindowパターンに従って、実際のウィジェットを
    作成せずにテストできるようにMainWindowをモック化します。

    Args:
        monkeypatch: pytestのmonkeypatchフィクスチャ

    Returns:
        MockMainWindowのインスタンス
    """
    # 各種モックを設定
    mock_file_dialog_get_open_file_name(monkeypatch)
    mock_file_dialog_get_save_file_name(monkeypatch)
    mock_message_box_question(monkeypatch)
    mock_message_box_information(monkeypatch)
    mock_message_box_warning(monkeypatch)
    mock_message_box_critical(monkeypatch)

    # MainWindowクラスをモック化
    mock_main_window = MockMainWindow()
    monkeypatch.setattr(
        "sgpo_editor.gui.main_window.MainWindow",
        lambda *args, **kwargs: mock_main_window,
    )

    return mock_main_window


def setup_mock_entry_model(monkeypatch):
    """テスト用にEntryModelをモック化する

    Args:
        monkeypatch: pytestのmonkeypatchフィクスチャ

    Returns:
        モック化されたEntryModel
    """
    mock_entry_model = MagicMock()
    # 必要な属性とメソッドを設定
    mock_entry_model.msgid = ""
    mock_entry_model.msgstr = ""
    mock_entry_model.fuzzy = False
    mock_entry_model.is_translated = False

    monkeypatch.setattr(
        "sgpo_editor.models.entry_model.EntryModel",
        lambda *args, **kwargs: mock_entry_model,
    )

    return mock_entry_model


def setup_mock_po_file(monkeypatch):
    """テスト用にViewerPOFileをモック化する

    Args:
        monkeypatch: pytestのmonkeypatchフィクスチャ

    Returns:
        モック化されたViewerPOFile
    """
    mock_po_file = MagicMock()
    # 必要な属性とメソッドを設定
    mock_po_file.filename = "/mock/path/to/test.po"
    mock_po_file.entries = []
    mock_po_file.is_modified = False

    # entriesメソッドをモック化
    def get_entries():
        return []

    mock_po_file.get_entries = get_entries
    mock_po_file.load = MagicMock(return_value=True)
    mock_po_file.save = MagicMock(return_value=True)

    monkeypatch.setattr(
        "sgpo_editor.core.viewer_po_file_refactored.ViewerPOFileRefactored",
        lambda *args, **kwargs: mock_po_file,
    )

    return mock_po_file


def mock_entire_app(monkeypatch):
    """アプリケーション全体をモック化する

    テストガイドラインに従い、主要なコンポーネントを全てモック化して
    実際のグラフィカルコンポーネントが必要ない状態でテストを実行できるようにします。

    Args:
        monkeypatch: pytestのmonkeypatchフィクスチャ

    Returns:
        各種モックオブジェクトを含む辞書
    """
    # Qtダイアログをモック化
    mock_file_dialog_get_open_file_name(monkeypatch)
    mock_file_dialog_get_save_file_name(monkeypatch)
    mock_message_box_question(monkeypatch)
    mock_message_box_information(monkeypatch)
    mock_message_box_warning(monkeypatch)
    mock_message_box_critical(monkeypatch)

    # 主要コンポーネントをモック化
    mock_main_window = setup_mock_main_window(monkeypatch)
    mock_entry_model = setup_mock_entry_model(monkeypatch)
    mock_po_file = setup_mock_po_file(monkeypatch)

    # グローバル終了時のクリーンアップ処理を追加
    def cleanup():
        mock_main_window.close()
        gc.collect()

    # 全てのモックを返却
    return {
        "main_window": mock_main_window,
        "entry_model": mock_entry_model,
        "po_file": mock_po_file,
        "cleanup": cleanup,
    }
