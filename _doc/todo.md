# SGPO Editor 改善タスクリスト (更新版: コンポジション優先, インスペクション対応)

コードの保守性、拡張性、テスト容易性を向上させるためのリファクタリングタスクリストです。コンポジションを優先し、インスペクション結果を反映しています。

## 優先度: 高

1.  **[/] タスク 1: クリティカルなインスペクションエラー修正 (進行中)**
    *   **対象:** `inspection/PyUnresolvedReferencesInspection.xml`, `inspection/PyTypeCheckerInspection.xml`, `inspection/PyTypedDictInspection.xml`, `inspection/PyArgumentListInspection.xml` 指摘ファイル。
    *   **内容:** 未解決参照、型エラー、TypedDictエラー、不正な引数リストを修正。特に `.pyi` ファイル、ファサード、ウィジェット間のインターフェース、データベース/キャッシュアクセス部分を重点的に確認。
    *   **進捗:** `gui/metadata_dialog.py`の型エラーを修正し、`EntryModel`との連携を改善（`Union[EntryModel, QWidget]`型対応）。
    *   **備考:** 最優先で実施し、以降のリファクタリングの基盤を安定させる。

2.  **[/] タスク 2: キャッシュ管理の一元化完了 (進行中)**
    *   **対象:** `src/sgpo_editor/core/cache_manager.py`, `src/sgpo_editor/gui/table_manager.py`, `src/sgpo_editor/gui/event_handler.py` (確認), `src/sgpo_editor/gui/facades/entry_list_facade.py`
    *   **内容:**
        *   `TableManager` 等のUI層に残存するキャッシュ関連ロジック (`_entry_cache`, `_row_key_map` 利用箇所など) を削除し、`EntryCacheManager` の API (`add_row_key_mapping`, `get_key_for_row`, `find_row_by_key`) を使用するように `EntryListFacade` 経由で修正。
        *   キャッシュ無効化ロジックが `EntryCacheManager` に完全に集約されているか最終確認。
        *   `_force_filter_update` フラグの管理が `EntryCacheManager` にカプセル化されているか確認。
    *   **ゴール:** キャッシュロジックの完全な一元化。

3.  **[/] タスク 3: ファサードパターンの徹底 (進行中)**
    *   **対象:** `src/sgpo_editor/gui/event_handler.py`, `src/sgpo_editor/gui/facades/`, UIウィジェット (`TableManager`, `EntryEditor` を含む), `src/sgpo_editor/gui/main_window.py`
    *   **内容:**
        *   `EventHandler` に残っているロジック（コメントアウト含む）を完全に削除または適切なファサードに移譲。最終的に `EventHandler` を廃止する。
        *   `MainWindow` や他のUIウィジェットからコア層 (`ViewerPOFile`, `EntryCacheManager`, `DatabaseAccessor` 等) やモデル層 (`EntryModel`) への直接アクセスがないか確認し、あればファサード経由に修正。
    *   **ゴール:** UI層とコア/モデル層間の依存関係がファサードに集約される。

## 優先度: 中

4.  **[ ] タスク 4: `TableManager` の責務削減 (未着手)**
    *   **対象:** `src/sgpo_editor/gui/table_manager.py`, `src/sgpo_editor/gui/facades/entry_list_facade.py`
    *   **内容:**
        *   `TableManager` が表示ロジック (`_update_table_contents`, `_get_status_color` など) と列管理（表示/非表示、幅）に特化しているか確認。
        *   ソート要求の処理が `_sort_request_callback` に委譲されているか確認。データ操作（キャッシュ管理含む）ロジックがあれば削除し、`EntryListFacade` 経由で `EntryCacheManager` や `ViewerPOFile` に委譲する。
    *   **ゴール:** `TableManager` の責務が明確化され、テスト容易性が向上する。

5.  **[ ] タスク 5: 重複コードの削減 (未着手)**
    *   **対象:** `inspection/DuplicatedCode_aggregate.xml` 指摘ファイル (`cache_manager.py`, `database_accessor.py`, ファサード/MainWindowなど)
    *   **内容:** 指摘された重複コードをリファクタリング。共通関数の作成、ロジックの集約（特にキャッシュ、DBアクセス、ファサード内の共通処理）などを検討。
    *   **ゴール:** コードの冗長性を減らし、保守性を向上させる。

6.  **[ ] タスク 6: クラス設計の改善 (未着手)**
    *   **対象:** `inspection/PyAttributeOutsideInitInspection.xml`, `inspection/PyNestedDecoratorsInspection.xml`, `inspection/PyMethodMayBeStaticInspection.xml` など
    *   **内容:** インスペクション警告に基づき、`__init__`での属性初期化、デコレーター順序修正、staticメソッド化などを実施。
    *   **ゴール:** クラス設計を改善し、コードの堅牢性と可読性を高める。

## 優先度: 低

7.  **[ ] タスク 7: その他のインスペクション警告修正 (未着手)**
    *   **対象:** `inspection/*.xml` (上記以外)
    *   **内容:** 未使用変数/インポート削除 (`PyUnusedLocalInspection`), 命名規則修正 (`PyPep8NamingInspection`), 冗長な括弧 (`PyRedundantParenthesesInspection`) などを修正。
    *   **ゴール:** コードのクリーンアップと全体的な品質向上。

## 完了済み

*   **[x] `ViewerPOFile` のコンポジションによる再設計**
    *   **対象ファイル:** `src/sgpo_editor/core/viewer_po_file*.py`, `ViewerPOFile` 参照箇所
    *   **内容:** `ViewerPOFile` をコンポジション構造に再設計し、継承を廃止。各機能コンポーネントが独立してテスト可能になった。

*   **[x] `MetadataEditDialog` クラスの改良**
    *   **対象ファイル:** `src/sgpo_editor/gui/metadata_dialog.py`
    *   **内容:** `EntryModel`オブジェクトから直接メタデータを編集できるように、コンストラクタの引数を`Union[EntryModel, QWidget]`型に対応させ、型安全性とクラス間連携を改善。

## 次のアクション

以下の順序でタスクを進めることを推奨します：

1.  **最優先:** タスク1（クリティカルエラー修正）の継続。
2.  **高優先度:** タスク2（キャッシュ一元化完了）、タスク3（ファサード徹底）。これらは並行して進めることが可能。
3.  **中優先度:** タスク4（TableManager責務削減）はタスク2, 3と連携して実施。タスク5（重複コード）、タスク6（クラス設計）は適宜実施。
4.  **低優先度:** タスク7（その他警告）は最後に実施。

## 注意事項

*   変更を加える際は、関連するユニットテスト・統合テストを作成・更新してください。
*   リファクタリングによってインターフェースが変更される場合は、影響範囲を特定し、関連箇所を修正してください。
*   不明点や設計上の判断が必要な場合は、追加の指示を仰いでください。