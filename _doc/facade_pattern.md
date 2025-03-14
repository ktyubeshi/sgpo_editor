# SGPOエディタ ファサードパターン実装ガイド

## 1. 概要

SGPOエディタでは、GUIコンポーネントと内部データモデルの間の結合度を低減し、コードの保守性と拡張性を向上させるために、ファサードパターンを採用しています。このドキュメントでは、ファサードパターンの実装方法と利用ガイドラインについて説明します。

## 2. ファサードパターンとは

ファサードパターンは、複雑なサブシステムに対するシンプルなインターフェースを提供するデザインパターンです。このパターンにより、以下の利点が得られます：

- **結合度の低減**: GUIコンポーネントはファサードを通じてのみデータモデルにアクセスするため、直接的な依存関係が減少します
- **一貫性のある操作**: データ操作の共通ロジックをファサードに集約することで、一貫性のある動作を保証します
- **変更の局所化**: 内部実装が変更された場合でも、ファサードのインターフェースが維持されていれば、クライアントコードへの影響を最小限に抑えられます

## 3. SGPOエディタでのファサード実装

### 3.1 ファサードクラス構成

SGPOエディタでは、以下のファサードクラスを実装しています：

1. **EntryEditorFacade**: エントリ編集機能に関するファサード
   - エントリの編集操作（テキスト更新、メタデータ編集など）を提供
   - 編集状態の管理と変更通知を担当

2. **EntryListFacade**: エントリリスト管理機能に関するファサード
   - エントリの一覧表示、フィルタリング、ソート機能を提供
   - 選択状態の管理と変更通知を担当

### 3.2 ファイル構成

```
src/sgpo_editor/gui/facades/
├── __init__.py       # ファサードモジュールの初期化
├── entry_editor_facade.py   # EntryEditorFacadeの実装
└── entry_list_facade.py     # EntryListFacadeの実装
```

## 4. EntryModelクラスとの連携

### 4.1 EntryModelクラスの概要

`EntryModel`クラスは、翻訳エントリのデータモデルを表現するクラスで、以下の特徴があります：

- Pydanticの`BaseModel`を継承し、データバリデーション機能を提供
- POEntryオブジェクトとの相互変換機能を提供
- メタデータ、レビューコメント、品質スコアなどの拡張機能をサポート

### 4.2 ファサードからEntryModelへのアクセス

ファサードクラスは、`EntryModel`オブジェクトへのアクセスと操作を抽象化します：

```python
# 例: EntryEditorFacadeでのEntryModelの操作
def apply_changes(self) -> bool:
    """エントリの変更を適用する"""
    entry = self._entry_editor.current_entry
    if not entry:
        logger.debug("エントリが選択されていないため、適用できません")
        return False
        
    current_po = self._get_current_po()
    if not current_po:
        logger.debug("POファイルがロードされていないため、適用できません")
        return False
        
    try:
        # エントリの更新を実行
        result = current_po.update_entry(entry)
        
        if result:
            # 成功メッセージとシグナル発行
            self._show_status(f"エントリ {entry.position} を更新しました", 3000)
            self.entry_applied.emit(entry.position)
            return True
        else:
            self._show_status("エントリの更新に失敗しました", 3000)
            return False
            
    except Exception as e:
        logger.error(f"エントリを適用する際にエラーが発生しました: {e}")
        self._show_status(f"エラー: {e}", 3000)
        return False
```

## 5. シグナル・イベント機構

### 5.1 変更通知の実装

ファサードパターンでは、データモデルの変更をGUIコンポーネントに通知するために、シグナル・イベント機構を実装しています：

1. **PySide6のシグナル**: ファサードクラスはQObjectを継承し、カスタムシグナルを定義
2. **コールバック関数**: 変更通知用のコールバック関数を登録・呼び出し

### 5.2 シグナル定義例

```python
class EntryEditorFacade(QObject):
    # シグナル定義
    entry_applied = Signal(int)  # 引数はエントリ番号
    entry_changed = Signal()     # エントリ内容が変更された時に発行
    
    def _on_text_changed(self) -> None:
        """エントリのテキスト変更時の処理"""
        self._show_status(
            "変更が保留中です。適用するには [適用] ボタンをクリックしてください。", 0
        )
        self.entry_changed.emit()
```

## 6. 実装状況

### 6.1 完了した実装

- EntryModelクラスの実装
- EntryEditorFacadeとEntryListFacadeの実装
- TableManagerクラスのEntryModel対応
- ViewerPOFileクラスのEntryModel対応
- テストコードの更新

### 6.2 今後の課題

- 残りのコンポーネントのEntryModel対応
- 型アノテーションの完全な更新
- テストカバレッジの向上
- ドキュメントの継続的な更新

## 7. ファサードの利用ガイドライン

### 7.1 新機能の追加

新しい機能を追加する場合は、以下のガイドラインに従ってください：

1. **適切なファサードの選択**: 機能の性質に応じて、既存のファサードを選択するか、新しいファサードを作成
2. **インターフェースの設計**: 機能を表現する明確なメソッド名と引数を設計
3. **内部実装の隠蔽**: 実装の詳細はファサード内に隠蔽し、クライアントには必要最小限のインターフェースを公開

### 7.2 既存コードの移行

既存のコードをファサードパターンに移行する場合は、以下の手順に従ってください：

1. **直接アクセスの特定**: GUIコンポーネントからEntryModelへの直接アクセスを特定
2. **ファサードメソッドの作成**: 特定した操作に対応するファサードメソッドを作成
3. **コードの置き換え**: 直接アクセスをファサードメソッド呼び出しに置き換え
4. **テストの更新**: 変更に合わせてテストコードを更新

## 8. テスト戦略

### 8.1 ファサードのテスト

ファサードクラスのテストでは、以下の観点を考慮してください：

1. **機能テスト**: 各メソッドが期待通りの動作をするかテスト
2. **シグナルテスト**: 適切なタイミングで正しいシグナルが発行されるかテスト
3. **エラー処理テスト**: 異常系の入力に対して適切に処理されるかテスト

### 8.2 テスト例

```python
def test_update_translation_emits_signal():
    # テスト用のファサードとモックオブジェクトを作成
    facade = EntryEditorFacade()
    mock_callback = Mock()
    facade.entry_updated.connect(mock_callback)
    
    # 操作を実行
    entry_id = "test_id"
    new_text = "新しい翻訳"
    facade.update_translation(entry_id, new_text)
    
    # シグナルが発行されたことを確認
    mock_callback.assert_called_once()
    # 引数の検証
    args = mock_callback.call_args[0]
    assert args[0].msgstr == new_text
```

## 9. 今後の拡張計画

### 9.1 追加予定のファサード

今後、以下のファサードの追加を検討しています：

1. **FileOperationFacade**: ファイル操作（開く、保存、エクスポートなど）を抽象化
2. **ReviewFacade**: レビュー機能に関する操作を抽象化
3. **StatisticsFacade**: 統計情報の収集と表示を抽象化

### 9.2 リファクタリング計画

既存コードのファサードパターンへの完全移行に向けて、以下のリファクタリングを計画しています：

1. **TableManagerの再設計**: EntryListFacadeとの連携を強化
2. **MetadataPanelの改善**: EntryEditorFacadeを活用した実装に変更
3. **MainWindowの簡素化**: 各ファサードを活用し、直接的なデータ操作を削減

## 10. 参考資料

- [Design Patterns: Elements of Reusable Object-Oriented Software](https://www.amazon.co.jp/dp/0201633612) - GoF本でのファサードパターンの解説
- [PyQt6ドキュメント: シグナルとスロット](https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots.html)
- [Pydanticドキュメント](https://docs.pydantic.dev/)
