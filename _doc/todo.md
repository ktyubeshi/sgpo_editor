# SGPO Editor 改善タスクリスト (更新版: コンポジション優先)

コードの保守性、拡張性、テスト容易性を向上させるためのリファクタリングタスクリストです。コンポジションを優先する方針に基づいています。

## 優先度: 高

1.  **タスク 1: `ViewerPOFile` のコンポジションによる再設計** - **完了**
    *   **対象ファイル:** `src/sgpo_editor/core/viewer_po_file*.py`, `ViewerPOFile` 参照箇所
    *   **説明:**
        *   ~~`ViewerPOFileRefactored` を `ViewerPOFile` にリネーム (またはエイリアス設定) し、古い `ViewerPOFile` を削除。~~ **完了**
        *   ~~新しい `ViewerPOFile` を、機能コンポーネント (`Base`, `Retriever`, `Filter`, `Updater`, `Stats` など) のインスタンスを**内部に保持するコンポジション構造**に再設計する。継承構造は廃止する。~~ **完了**
        *   ~~`ViewerPOFile` はこれらのコンポーネントを調整するファサード/コーディネーターとする。~~ **完了**
        *   ~~コンポーネント間の依存関係は `ViewerPOFile` が注入する（コンストラクタまたはメソッド引数）。直接依存は避ける。~~ **完了**
        *   ~~旧 `ViewerPOFile` への参照を修正する。~~ **完了**
    *   **ゴール:** `ViewerPOFile` が調整役に徹し、各機能コンポーネントが独立してテスト可能になる。

2.  **タスク 2: キャッシュ管理の一元化** - **部分的に完了**
    *   **対象ファイル:** `src/sgpo_editor/core/cache_manager.py`, `src/sgpo_editor/gui/table_manager.py`, `src/sgpo_editor/gui/event_handler.py`
    *   **説明:**
        *   ~~`TableManager` 等のUI層の独自キャッシュ (`_entry_cache`, `_row_key_map` 等) を削除。~~ **一部完了**（TableManagerのキャッシュは残っている可能性あり）
        *   ~~UI層が必要とするマッピング機能 (`add_row_key_mapping`, `get_key_for_row`, `find_row_by_key` 等) を `EntryCacheManager` に実装し、UI層 (ファサード経由) から利用。~~ **完了**
        *   ~~キャッシュ無効化ロジックを `EntryCacheManager` に集約。~~ **完了**
        *   ~~`_force_filter_update` フラグの管理を `EntryCacheManager` にカプセル化。~~ **完了**
    *   **残りのタスク:**
        * `TableManager`の残りのキャッシュ管理コードを`EntryCacheManager`に移譲
        * `TableManager`の`update_table`メソッド内の行マッピング機能が`EntryCacheManager`を使用するよう確認
    *   **ゴール:** キャッシュロジックが `EntryCacheManager` に集約され、UI層の責務が軽減される。

3.  **タスク 3: ファサードパターンの徹底** - **部分的に完了**
    *   **対象ファイル:** `src/sgpo_editor/gui/event_handler.py`, `src/sgpo_editor/gui/facades/`, UIウィジェット, `src/sgpo_editor/gui/main_window.py`
    *   **説明:**
        *   ~~`EventHandler` のデータ操作ロジックを適切なファサード (`EntryEditorFacade`, `EntryListFacade`) に移譲。~~ **進行中**（ほとんどのメソッドがコメントアウトまたはパス処理に変更されている）
        *   ~~UIウィジェットからコア層/モデル層への直接アクセスをファサード経由に修正。ファサードは内部でコンポジション化された `ViewerPOFile` や `EntryCacheManager` を利用。~~ **進行中**
    *   **残りのタスク:**
        * `EventHandler`の残りのメソッドをファサードに移譲またはイベント連携のみに限定
        * ファサードパターンの使用を確実にするために`MainWindow`の関連コードを確認
        * 不要になった`EventHandler`の機能を完全に削除（または将来的に完全廃止を検討）
    *   **ゴール:** UI層とコア層の依存関係がファサードに集約され、関心事が分離される。

4.  **タスク 4: インスペクションエラー修正 (クリティカル)**
    *   **対象ファイル:** `inspection/PyUnresolvedReferencesInspection.xml`, `inspection/PyTypeCheckerInspection.xml`, `inspection/PyTypedDictInspection.xml`, `inspection/PyArgumentListInspection.xml` 指摘ファイル
    *   **説明:** 未解決参照、型エラー、`TypedDict` エラー、不正な引数リストを修正。`.pyi` ファイルやファサード、ウィジェット間の依存関係に注意。
    *   **状態の確認が必要:** インスペクションエラーの現状を確認し、既に解決されているものとまだ残っているものを特定
    *   **ゴール:** 潜在的なバグや型安全性の問題を解消する。

## 優先度: 中

5.  **タスク 5: `TableManager` の責務削減** - **進行中**
    *   **対象ファイル:** `src/sgpo_editor/gui/table_manager.py`, `src/sgpo_editor/gui/facades/entry_list_facade.py`
    *   **説明:** 
        * ~~ソート等のロジックを削除し、`EntryListFacade` またはコア層 (`ViewerPOFileFilter` インスタンスなど) に委譲。表示責務に特化させる。~~ **部分的に完了**（ソート要求の処理はコールバックに委譲）
    *   **残りのタスク:**
        * 表示以外のロジックがまだ残っていないか確認
        * キャッシュ関連のコードを完全にEntryCacheManagerに移行
    *   **ゴール:** `TableManager` が表示ロジックに特化し、テストしやすくなる。

6.  **タスク 6: 重複コードの削減**
    *   **対象ファイル:** `inspection/DuplicatedCode_aggregate.xml` 指摘ファイル
    *   **説明:** 指摘された重複コードをリファクタリング。特にキャッシュ、DBアクセス、UI更新ロジックに注意。
    *   **状態の確認が必要:** 現在の重複コードの状況を確認
    *   **ゴール:** コードの冗長性を減らし、保守性を向上させる。

7.  **タスク 7: クラス設計の改善**
    *   **対象ファイル:** `inspection/PyAttributeOutsideInitInspection.xml`, `inspection/PyNestedDecoratorsInspection.xml` 等の指摘ファイル
    *   **説明:** `__init__` 外の属性定義やデコレーターのネスト順序などを修正。
    *   **状態の確認が必要:** 現在のインスペクション警告を確認
    *   **ゴール:** クラス設計を改善し、コードの堅牢性と可読性を高める。

## 優先度: 低

8.  **タスク 8: その他のインスペクション警告修正**
    *   **対象ファイル:** `inspection/*.xml` (上記以外)
    *   **説明:** 未使用変数/インポート削除、軽微なPEP8違反、typoなどを修正 (`PyUnusedLocalInspection`, `PyPep8NamingInspection`, `SpellCheckingInspection` など)。
    *   **状態の確認が必要:** 残っている軽微な警告を確認
    *   **ゴール:** コードのクリーンアップと品質向上。

## 次のアクション

以下の順序でタスクを進めることを推奨します：

1. **完了確認**: すでに完了しているタスクの最終チェック
   - タスク1（ViewerPOFileのコンポジション化）の各参照箇所が正しく更新されているか確認
   - タスク2（キャッシュ管理の一元化）の残りの部分がTableManagerなどにないか確認

2. **今すぐ着手すべきタスク**:
   - タスク3（ファサードパターンの徹底）の続き：EventHandlerの役割をさらに整理
   - タスク5（TableManagerの責務削減）の続き：表示以外のロジックを完全に移行

3. **検証が必要なタスク**:
   - タスク4（インスペクションエラー修正）：現在のエラー状況を確認して対応

## 注意事項

*   各タスクは可能な限り独立して実施しますが、依存関係がある場合は順番を考慮してください（例: タスク1の後にタスク3, 5を本格化）。
*   変更を加える際は、関連するユニットテスト・統合テストを作成・更新してください。
*   リファクタリングによってインターフェースが変更される場合は、影響範囲を特定し、関連箇所を修正してください。
*   不明点や設計上の判断が必要な場合は、追加の指示を仰いでください。