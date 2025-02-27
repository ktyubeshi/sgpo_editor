"""GUI Mocking helpers for tests.

このモジュールはテスト実行時にGUIの操作待ちを防ぐために、
Qt UIコンポーネントをモック化するヘルパーを提供します。
"""

from PySide6 import QtWidgets, QtCore


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
    
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName", mock_get_open_file_name)


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
    
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", mock_get_save_file_name)


def mock_message_box_question(monkeypatch, return_value=QtWidgets.QMessageBox.Yes):
    """
    QMessageBox.questionをモック化する
    
    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
        return_value: 返す値（デフォルトはQMessageBox.Yes）
    """
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
        pass
    
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", mock_information)


def mock_message_box_warning(monkeypatch):
    """
    QMessageBox.warningをモック化する
    
    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
    """
    def mock_warning(*args, **kwargs):
        pass
    
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", mock_warning)


def mock_message_box_critical(monkeypatch):
    """
    QMessageBox.criticalをモック化する
    
    Args:
        monkeypatch: pytestのmonkepatchフィクスチャ
    """
    def mock_critical(*args, **kwargs):
        pass
    
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", mock_critical)


def wait_for_window_shown(qtbot, window):
    """
    ウィンドウが表示されるのを待機する
    
    Args:
        qtbot: pytest-qtのqtbotフィクスチャ
        window: 待機対象のウィンドウ
    """
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
    qtbot.mouseClick(button, QtCore.Qt.LeftButton)


def enter_text(qtbot, widget, text):
    """
    テキストを入力する
    
    Args:
        qtbot: pytest-qtのqtbotフィクスチャ
        widget: 入力対象のウィジェット
        text: 入力するテキスト
    """
    widget.clear()
    qtbot.keyClicks(widget, text)
