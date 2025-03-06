# PySide6 GUIアプリケーションのテストガイドライン

## テスト時の主な課題と解決策

### 1. セグメンテーションフォールトの防止

**テスト中のGUIダイアログのブロックを防ぐには、実際のダイアログを開かずにユーザー操作をシミュレートするモック化が有効です。** PySide6アプリのテストでファイル選択ダイアログやエラーメッセージダイアログが表示されると、ユーザ入力待ちでテストが一時停止してしまいます。これを避けるため、テスト中はそれらのダイアログをモック（疑似的な振る舞いに置き換え）し、即座に想定結果を返すようにします。 ([python - Keeping a dialog from showing PySide for testing - Stack Overflow](https://stackoverflow.com/questions/26470305/keeping-a-dialog-from-showing-pyside-for-testing#:~:text=I%20decided%20to%20use%20the,is%20not%20optimal%20for%20testing)) こうすることでダイアログUIを実際に表示せずに**ユーザーが操作した結果**を再現でき、テストを自動化できます。以下に、それぞれのケースでのベストプラクティスを説明します。

### 2. メインウィンドウやウィジェットのライフサイクル管理

PySide6/QtのGUIアプリケーションのテストでは、ウィジェットやウィンドウのライフサイクル管理が非常に重要です。不適切な管理はセグメンテーションフォールトの原因となります。特に以下の点に注意が必要です：

- テスト終了時に全てのウィジェットが適切に破棄されていること
- `QApplication`のインスタンスが適切に管理されていること
- テスト間でウィジェットやリソースが共有されないこと

これらの問題に対処するには、モックオブジェクトを使用して実際のウィジェット作成を回避し、テスト終了時に適切なクリーンアップを行うことが効果的です。

## 実装テクニック

### MockMainWindowパターン

複雑なGUIアプリケーションのテストでは、実際のウィンドウクラスをモッククラスで置き換えることで、セグメンテーションフォールトを防止し、テストの信頼性を高めることができます。以下は`MockMainWindow`クラスを使用したパターンの例です：

```python
from unittest.mock import MagicMock, patch
import gc

class MockMainWindow:
    """MainWindowクラスのモック実装"""
    def __init__(self):
        # 必要なコンポーネントをモック化
        self.entry_editor = MagicMock()
        self.stats_widget = MagicMock()
        self.table = MagicMock()
        self.current_po = MagicMock()
        
        # 必要なメソッドをモック化
        self.get_current_entry = MagicMock(return_value=None)
        self.update_table = MagicMock()
        self.update_stats = MagicMock()
        
    def close(self):
        """明示的にリソースをクリーンアップ"""
        pass

class TestMainWindowFeatures(unittest.TestCase):
    def setUp(self):
        """各テスト前の準備"""
        self.main_window = MockMainWindow()
        
    def tearDown(self):
        """各テスト後のクリーンアップ"""
        self.main_window.close()
        self.main_window = None
        # 明示的なガベージコレクションを実行
        gc.collect()
        
    def test_feature(self):
        """特定の機能のテスト"""
        # テストコード
        result = self.main_window.some_method()
        self.assertEqual(result, expected_value)
```

このパターンを使用することで以下の利点があります：

1. 実際のQtウィジェットを作成せず、メモリ管理の問題を回避
2. テスト実行が高速化（実際のGUI描画が不要）
3. テスト間の独立性が向上
4. セグメンテーションフォールトのリスクが大幅に減少

### Enumメンバーのモック化における注意点

Pythonの`Enum`クラスのメンバーは直接置き換えることができないため、以下のようにモック化する必要があります：

```python
# ❌ 間違った方法（直接Enumメンバーをパッチ）
@patch('app.LayoutType.LAYOUT1', MagicMock())
def test_layout_switching(self):
    # テストコード

# ✅ 正しい方法（メソッドをパッチ）
def test_layout_switching(self):
    with patch.object(self.main_window.entry_editor, 'set_layout_type') as mock_set_layout:
        # レイアウト切り替えのアクション
        self.main_window.compact_layout_action.triggered.emit()
        # 正しい引数でメソッドが呼ばれたか確認
        mock_set_layout.assert_called_with(LayoutType.LAYOUT1)
```

## QFileDialogの表示をモックして一時停止を防ぐ方法
ファイル選択ダイアログ (`QFileDialog`) は通常、`getOpenFileName()`や`getSaveFileName()`といった静的関数で呼び出し、ユーザーがファイルを選択するまで処理をブロックします。テストではこれをモック化し、**常に決まったファイルパスを返す**ようにします。例えば、`QFileDialog.getOpenFileName` をモックして任意のファイルパスを返すラムダ関数に差し替えます ([python - Gui testing in PySide2 with qtbot - Stack Overflow](https://stackoverflow.com/questions/58731798/gui-testing-in-pyside2-with-qtbot#:~:text=qtbot.mouseClick%28main.button%2C%20QtCore.Qt.LeftButton%29%20,lambda%20%2Aargs%3A%20%28file_path%2C%20file_type))。コード例:

```python
def test_open_file(monkeypatch, qtbot):
    # QFileDialogの静的関数をモックして常にテスト用パスを返す
    monkeypatch.setattr(QtWidgets.QFileDialog, "getOpenFileName",
                        lambda *args, **kwargs: ("/path/to/test_file.txt", "All Files (*)"))
    # テスト対象のウィンドウを設定
    window = MyAppMainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.wait_for_window_shown(window)  # ウィンドウが表示されるのを待機
    # ボタンをクリック（この操作で内部で QFileDialog.getOpenFileName が呼ばれる）
    qtbot.mouseClick(window.openFileButton, QtCore.Qt.LeftButton)
    # ダイアログがモックされているので即座に戻り、後続処理が実行される
    assert window.selected_file_path == "/path/to/test_file.txt"
```

上記では、ボタンのクリックにより実行される`getOpenFileName`がモックによって即座に`("/path/to/test_file.txt", "All Files (*)")`を返すため、ダイアログ表示による待ち時間がなくなります。 ([python - Gui testing in PySide2 with qtbot - Stack Overflow](https://stackoverflow.com/questions/58731798/gui-testing-in-pyside2-with-qtbot#:~:text=qtbot.mouseClick%28main.button%2C%20QtCore.Qt.LeftButton%29%20,lambda%20%2Aargs%3A%20%28file_path%2C%20file_type))ユーザーがキャンセルした場合のシナリオもテストするには、同様にモックの戻り値を空文字にすることで再現できます（例えば `("", "")` を返すようにしてキャンセルをシミュレートします）。モックしたおかげでダイアログUIを出さずに処理を進められるため、テストがブロックされません。

## QMessageBoxのポップアップをモックして一時停止を防ぐ方法
エラーメッセージや確認ダイアログに使われる`QMessageBox`も、デフォルトではユーザーがボタンを押すまで処理をブロックします。テストではこれをモックし、**ユーザーがボタンを押した結果**を即座に返すようにします。例えば「はい/いいえ」の確認ダイアログを表示する`QMessageBox.question`をモックして、常に「Yes」が選択されたことにすることができます ([A note about Modal Dialogs — pytest-qt  documentation](https://pytest-qt.readthedocs.io/en/latest/note_dialogs.html#:~:text=def%20test_Qt,addWidget%28simple)) ([python - Keeping a dialog from showing PySide for testing - Stack Overflow](https://stackoverflow.com/questions/26470305/keeping-a-dialog-from-showing-pyside-for-testing#:~:text=can%20something%20like%20this%3A))。コード例:

```python
def test_confirm_dialog(monkeypatch, qtbot):
    # QMessageBox.question をモックして常に Yes を返す
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        lambda *args, **kwargs: QtWidgets.QMessageBox.Yes)
    result = MyDialog.show_confirm_dialog()  # テスト対象: 内部で QMessageBox.question を呼ぶ関数
    assert result is True  # 「Yes」が選択された想定で True が返ることを確認
```

上記では`QMessageBox.question`が常に`Yes`を返すため、実際にダイアログを表示せずともユーザーが「Yes」をクリックした状況を再現できます。同様に、エラーメッセージ表示用の`QMessageBox.critical`や`QMessageBox.information`もモック可能です。ユーザーのクリックを必要としない場合は、モック関数内で何もせず即座にリターンするようにしておけばテストが止まることはありません（必要なら`QMessageBox.Ok`等の値を返しておきます）。実際のStack Overflowの質問者も、自動でダイアログを閉じるQTimerを使う方法と比較して、**モックでダイアログ呼び出し自体を置き換える方法**を選択しています ([python - Keeping a dialog from showing PySide for testing - Stack Overflow](https://stackoverflow.com/questions/26470305/keeping-a-dialog-from-showing-pyside-for-testing#:~:text=You%20can%20set%20up%20a,still%20display%20for%20a%20while)) ([python - Keeping a dialog from showing PySide for testing - Stack Overflow](https://stackoverflow.com/questions/26470305/keeping-a-dialog-from-showing-pyside-for-testing#:~:text=I%20decided%20to%20use%20the,is%20not%20optimal%20for%20testing))。このようにモック化することでダイアログUIが描画されること自体を防ぎ、テストがスムーズに進むようになります。

## pytestでのモック設定方法
PySide6アプリのテストでは、pytestの**`monkeypatch`フィクスチャ**を使うと簡潔にモックを適用できます。テスト関数の引数に`monkeypatch`を含め、`monkeypatch.setattr()`で対象となるクラスのメソッドを置き換えます ([A note about Modal Dialogs — pytest-qt  documentation](https://pytest-qt.readthedocs.io/en/latest/note_dialogs.html#:~:text=def%20test_Qt,addWidget%28simple))。例えば先述のように`QFileDialog.getOpenFileName`や`QMessageBox.question`を置き換える場合、`monkeypatch.setattr(PySide6.QtWidgets.QFileDialog, "getOpenFileName", <代替関数>)`のように指定します。代替関数にはラムダやテスト用のスタブ関数を与え、期待する戻り値を返すようにします。`monkeypatch`フィクスチャを使う利点は、**テスト後に自動で元の状態に戻してくれる**点です ([How to monkeypatch/mock modules and environments - pytest documentation](https://docs.pytest.org/en/stable/how-to/monkeypatch.html#:~:text=))。各テストは独立してモックを適用でき、テスト間で副作用が残りません。また、pytest-qtを導入している場合は`qtbot`フィクスチャ（後述）と組み合わせて使うことで、GUIイベントとモックを連携してテストできます。

> **補足:** `unittest.mock.patch`を使ってモックする方法もありますが、pytestでは組み込みの`monkeypatch`フィクスチャを使う方が簡潔です。たとえば ([python - Keeping a dialog from showing PySide for testing - Stack Overflow](https://stackoverflow.com/questions/26470305/keeping-a-dialog-from-showing-pyside-for-testing#:~:text=can%20something%20like%20this%3A))にあるように、`patch.object(QMessageBox, "question", return_value=QMessageBox.Yes)`とするのと同様のことが、pytestでは上記の`monkeypatch.setattr`で実現できます。

## PySide6のイベントループとUI操作をエミュレートする手法
GUIのテストでは、Qtのイベントループを回しつつウィジェット操作をエミュレートする必要があります。**pytest-qt**プラグインの`qtbot`フィクスチャを使うと、バックグラウンドで`QApplication`（イベントループ）を起動し、GUI操作を再現できます。例えば、テスト内でウィンドウを生成した後に`qtbot.addWidget(window)`で登録し、`window.show()`してから`qtbot.wait_for_window_shown(window)`で表示が完了するまで待機できます ([python - Gui testing in PySide2 with qtbot - Stack Overflow](https://stackoverflow.com/questions/58731798/gui-testing-in-pyside2-with-qtbot#:~:text=%40pytest,wait_for_window_shown%28main%29%20return%20main))。その上で`qtbot.mouseClick(button, QtCore.Qt.LeftButton)`のようにボタンクリックをシミュレートすれば、実際にユーザーがクリックしたのと同じシグナル発行・スロット実行が行われます ([python - Gui testing in PySide2 with qtbot - Stack Overflow](https://stackoverflow.com/questions/58731798/gui-testing-in-pyside2-with-qtbot#:~:text=def%20test_open_file,lambda%20%2Aargs%3A%20%28file_path%2C%20file_type))。キー入力やマウス操作、ウィジェットの有効化/無効化もqtbot経由で操作可能です。内部で非同期処理やシグナルを待つ必要がある場合は、`qtbot.waitUntil()`や`qtbot.waitSignal()`を用いて一定時間内に処理が完了するのを待機できます。なお、**PySide6自体のQtTestモジュール（QTest）**もGUIテスト用の機能を提供していますが、公式ドキュメントでも通常の単体テストにはpytestの利用が推奨されています ([PySide6.QtTest - Qt for Python](https://doc.qt.io/qtforpython-6/PySide6/QtTest/index.html#:~:text=Not%20all%20macros%20in%20the,Python%20module))（pytest-qtはそのpytest上でQtのイベントループを扱うための定番ツールです）。総じて、`qtbot`を使うことで明示的に`QApplication.processEvents()`を呼ぶことなくイベントループを回せるため、モックしたダイアログの呼び出し後に続くUI更新処理も自然に実行されます。

## モック適用範囲のベストプラクティス
モックは**必要最小限の範囲**に留めるのが鉄則です。GUIテストでは、ユーザー入力待ちでテストをブロックする部分（ファイルダイアログやメッセージボックス表示）に対してのみモックを当て、それ以外のアプリケーション内部ロジックは通常通り実行させます。こうすることで、モックによって対話部分だけをスキップしつつ、ビジネスロジックやUI更新処理は検証できます。モック適用はテスト関数単位で行い、テストが終われば元に戻るようにします ([How to monkeypatch/mock modules and environments - pytest documentation](https://docs.pytest.org/en/stable/how-to/monkeypatch.html#:~:text=))。先述の`monkeypatch`フィクスチャを用いればテストごとに適用と解除が自動化されるため、**テスト間の干渉を防ぎ**つつ各ケースで異なる戻り値を設定できます（例えばあるテストではファイル選択ダイアログにファイルを選ばせ、別のテストではキャンセルさせる、といった振る舞いを個別にモック可能です）。また、モックする対象はQtのダイアログそのもの（例: `QFileDialog.getOpenFileName` や `QMessageBox.question`）に限定し、アプリケーションのロジック側には極力手を加えません。こうしたスコープの絞り込みにより、モック化による影響範囲を最小に保ちつつ、ユーザー操作待ちによるテスト停止を防ぐことができます。

## セグメンテーションフォールト対策のまとめ

PySide6/Qtアプリケーションのテスト中にセグメンテーションフォールトが発生する主な原因と対策は以下の通りです：

1. **原因：ウィジェットの不適切な破棄**
   - **対策：** テスト終了時に明示的に`close()`メソッドを呼び、`tearDown`メソッドで`None`に設定
   - **対策：** ガベージコレクションを明示的に実行（`gc.collect()`）

2. **原因：QApplication間の競合**
   - **対策：** テスト間で`QApplication`インスタンスを共有せず、モックを使用して実際のGUIを作成しない

3. **原因：リソースリーク**
   - **対策：** 全てのイベントループや非同期タスクを適切に終了
   - **対策：** 大きなウィジェット階層をモックオブジェクトで置き換え

4. **原因：ウィジェット間の不適切な参照**
   - **対策：** 循環参照を避け、明示的に参照を解除

## テスト実行におけるベストプラクティス

1. テストは独立して実行可能にする（他のテストの状態に依存しない）
2. 各テストの前後で適切なセットアップとクリーンアップを行う
3. テストの実行時間を短くするため、実際のGUIの表示を最小限にする
4. テスト失敗時にはログを詳細に確認し、特にセグメンテーションフォールトの場合は`tearDown`メソッドを確認

**まとめ:** PySide6のGUIテストでは、ファイルダイアログやメッセージボックスをモックで置き換えることでユーザー入力待ちのブロッキングを回避し、pytest-qtの`qtbot`を使ってイベントループとユーザー操作をエミュレートするのがベストプラクティスです。さらに、実際のウィジェット作成を避けるためにモッククラスを使用し、適切なリソース管理を行うことでセグメンテーションフォールトを防止できます。これらの手法を組み合わせることで、テストの信頼性と可読性を保ち、ユーザー操作のシナリオを自動テストで再現できるようになります。