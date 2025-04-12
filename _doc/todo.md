# SGPO Editor 改善タスクリスト (更新版: コンポジション優先)

コードの保守性、拡張性、テスト容易性を向上させるためのリファクタリングタスクリストです。コンポジションを優先する方針に基づいています。

## 優先度: 高

1.  **タスク 1: `ViewerPOFile` のコンポジションによる再設計**
    *   **対象ファイル:** `src/sgpo_editor/core/viewer_po_file*.py`, `ViewerPOFile` 参照箇所
    *   **説明:**
        *   `ViewerPOFileRefactored` を `ViewerPOFile` にリネーム (またはエイリアス設定) し、古い `ViewerPOFile` を削除。
        *   新しい `ViewerPOFile` を、機能コンポーネント (`Base`, `Retriever`, `Filter`, `Updater`, `Stats` など) のインスタンスを**内部に保持するコンポジション構造**に再設計する。継承構造は廃止する。
        *   `ViewerPOFile` はこれらのコンポーネントを調整するファサード/コーディネーターとする。
        *   コンポーネント間の依存関係は `ViewerPOFile` が注入する（コンストラクタまたはメソッド引数）。直接依存は避ける。
        *   旧 `ViewerPOFile` への参照を修正する。
    *   **ゴール:** `ViewerPOFile` が調整役に徹し、各機能コンポーネントが独立してテスト可能になる。

2.  **タスク 2: キャッシュ管理の一元化**
    *   **対象ファイル:** `src/sgpo_editor/core/cache_manager.py`, `src/sgpo_editor/gui/table_manager.py`, `src/sgpo_editor/gui/event_handler.py`
    *   **説明:**
        *   `TableManager` 等のUI層の独自キャッシュ (`_entry_cache`, `_row_key_map` 等) を削除。
        *   UI層が必要とするマッピング機能 (`add_row_key_mapping`, `get_key_for_row`, `find_row_by_key` 等) を `EntryCacheManager` に実装し、UI層 (ファサード経由) から利用。
        *   キャッシュ無効化ロジックを `EntryCacheManager` に集約。
        *   `_force_filter_update` フラグの管理を `EntryCacheManager` にカプセル化。
    *   **ゴール:** キャッシュロジックが `EntryCacheManager` に集約され、UI層の責務が軽減される。

3.  **タスク 3: ファサードパターンの徹底**
    *   **対象ファイル:** `src/sgpo_editor/gui/event_handler.py`, `src/sgpo_editor/gui/facades/`, UIウィジェット, `src/sgpo_editor/gui/main_window.py`
    *   **説明:**
        *   `EventHandler` のデータ操作ロジックを適切なファサード (`EntryEditorFacade`, `EntryListFacade`) に移譲。
        *   UIウィジェットからコア層/モデル層への直接アクセスをファサード経由に修正。ファサードは内部でコンポジション化された `ViewerPOFile` や `EntryCacheManager` を利用。
    *   **ゴール:** UI層とコア層の依存関係がファサードに集約され、関心事が分離される。

4.  **タスク 4: インスペクションエラー修正 (クリティカル)**
    *   **対象ファイル:** `inspection/PyUnresolvedReferencesInspection.xml`, `inspection/PyTypeCheckerInspection.xml`, `inspection/PyTypedDictInspection.xml`, `inspection/PyArgumentListInspection.xml` 指摘ファイル
    *   **説明:** 未解決参照、型エラー、`TypedDict` エラー、不正な引数リストを修正。`.pyi` ファイルやファサード、ウィジェット間の依存関係に注意。
    *   **ゴール:** 潜在的なバグや型安全性の問題を解消する。

## 優先度: 中

5.  **タスク 5: `TableManager` の責務削減**
    *   **対象ファイル:** `src/sgpo_editor/gui/table_manager.py`, `src/sgpo_editor/gui/facades/entry_list_facade.py`
    *   **説明:** ソート等のロジックを削除し、`EntryListFacade` またはコア層 (`ViewerPOFileFilter` インスタンスなど) に委譲。表示責務に特化させる。
    *   **ゴール:** `TableManager` が表示ロジックに特化し、テストしやすくなる。

6.  **タスク 6: 重複コードの削減**
    *   **対象ファイル:** `inspection/DuplicatedCode_aggregate.xml` 指摘ファイル
    *   **説明:** 指摘された重複コードをリファクタリング。特にキャッシュ、DBアクセス、UI更新ロジックに注意。
    *   **ゴール:** コードの冗長性を減らし、保守性を向上させる。

7.  **タスク 7: クラス設計の改善**
    *   **対象ファイル:** `inspection/PyAttributeOutsideInitInspection.xml`, `inspection/PyNestedDecoratorsInspection.xml` 等の指摘ファイル
    *   **説明:** `__init__` 外の属性定義やデコレーターのネスト順序などを修正。
    *   **ゴール:** クラス設計を改善し、コードの堅牢性と可読性を高める。

## 優先度: 低

8.  **タスク 8: その他のインスペクション警告修正**
    *   **対象ファイル:** `inspection/*.xml` (上記以外)
    *   **説明:** 未使用変数/インポート削除、軽微なPEP8違反、typoなどを修正 (`PyUnusedLocalInspection`, `PyPep8NamingInspection`, `SpellCheckingInspection` など)。
    *   **ゴール:** コードのクリーンアップと品質向上。

## 注意事項

*   各タスクは可能な限り独立して実施しますが、依存関係がある場合は順番を考慮してください（例: タスク1の後にタスク3, 5を本格化）。
*   変更を加える際は、関連するユニットテスト・統合テストを作成・更新してください。
*   リファクタリングによってインターフェースが変更される場合は、影響範囲を特定し、関連箇所を修正してください。
*   不明点や設計上の判断が必要な場合は、追加の指示を仰いでください。