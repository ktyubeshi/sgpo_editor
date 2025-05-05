Title: SGPO Editor キャッシュ戦略ドキュメント
Updated: 2025-04-18
---

# SGPO Editor キャッシュ戦略ドキュメント

## 1. 背景 (Context)

SGPO Editorは、gettext POファイルの効率的な編集・管理を目的としたデスクトップGUIアプリケーションです。特に大規模なPOファイル（数千〜数万エントリ）を扱う場合でも、UIの応答性（リスト表示、スクロール、フィルタリング、ソート）を高く保つことが求められます。

初期の設計およびパフォーマンステストを通じて、以下の点が明らかになりました。

*   **Pydantic V2の性能:** Pydantic V2の標準的な検証付きモデル生成 (`EntryModel(**data)` や `model_validate`) は、大量データに対しても十分に高速であり、`model_construct()` による検証スキップは特定のケースでむしろオーバーヘッドとなることが判明しました。
*   **検索I/Oのボトルネック:** 従来のキーワード検索（SQLiteのLIKE演算やPythonでの文字列検索）は、大量データにおいて主要なパフォーマンスボトルネックとなっていました。
*   **キャッシュの必要性:** データベースからのデータ取得とPydanticモデルへの変換コストを削減し、UIの応答性を向上させるためには、効果的なキャッシュ戦略が不可欠です。
*   **責務分離の重要性:** キャッシュロジック、データベースアクセス、UI表示の責務を明確に分離することが、保守性とテスト容易性の鍵となります。

これらの背景を踏まえ、パフォーマンス、メモリ効率、データ一貫性、保守性のバランスを取るためのキャッシュ戦略を策定しました。

## 2. キャッシュ戦略の目的 (Objectives)

*   **パフォーマンス向上:** UI応答性を最大化し、大量エントリ下でもスムーズな操作（スクロール、フィルタ、ソート）を実現する。
*   **DBアクセス削減:** データベースへのクエリ発行回数と、取得・変換するデータ量を最小限に抑える。
*   **メモリ効率:** キャッシュによる過剰なメモリ消費を防ぎ、設定された上限内で効率的にメモリを使用する。
*   **データ一貫性:** エントリ編集時に、データベースとキャッシュ間のデータの整合性を確実に保ち、古い情報が表示されないようにする。
*   **保守性とテスト容易性:** キャッシュ関連のロジックを `EntryCacheManager` に集約し、他のコンポーネントとの依存性を低減する。

## 3. キャッシュアーキテクチャ (Architecture)

SGPO Editorは、インメモリSQLiteデータベースを一次データストアとし、その上にPythonオブジェクトキャッシュ層 (`EntryCacheManager`) を設けるハイブリッド構成を採用します。

```mermaid
graph TD
    subgraph UI層
        UI_Widget[UI Widgets (QTableWidget, EntryEditor etc.)]
        Facade[Facades (EntryListFacade, EntryEditorFacade)]
        Mapper[Row/Key Mapper (in EntryListFacade)]
    end

    subgraph キャッシュ層
        CacheManager[EntryCacheManager]
        CompleteCache[(CompleteEntryCache<br/>key → EntryModel<br/>LRU + Mem Limit)]
        FilterCache[(Filter Result Cache<br/>hash → List[EntryModel]<br/>LRU + Mem Limit)]
        Prefetch[Prefetch Mechanism]
    end

    subgraph データアクセス層
        DBAccessor[DatabaseAccessor]
        SQLite[InMemory SQLite<br/>(FTS5 Enabled)]
        UpdateHook[SQLite Update Hook]
    end

    UI_Widget -- ユーザー操作 --> Facade
    Facade -- データ要求/キャッシュ確認 --> CacheManager
    Facade -- (キャッシュミス時) データ要求 --> DBAccessor
    Facade -- 行/キー変換 --> Mapper
    Facade -- モデル更新/表示 --> UI_Widget
    Mapper -- 情報を利用 --> Facade

    CacheManager -- キャッシュミス --> DBAccessor
    CacheManager -- キャッシュヒット/データ --> Facade
    CacheManager -- 管理 --> CompleteCache
    CacheManager -- 管理 --> FilterCache
    CacheManager -- 制御 --> Prefetch

    DBAccessor -- SQL (FTS5 MATCH) --> SQLite
    SQLite -- Query Result (Dict/Tuple) --> DBAccessor
    SQLite -- 更新通知 --> UpdateHook
    UpdateHook -- キャッシュ無効化指示 --> CacheManager

    DBAccessor -- List[Dict/Tuple] --> CacheManager
    CacheManager -- EntryModel生成/キャッシュ --> CacheManager
    CacheManager -- EntryModel --> Facade

    UI_Widget -- スクロールイベント --> Facade
    Facade -- プリフェッチ要求 --> CacheManager
    Prefetch -- データ取得要求 --> DBAccessor
```

**各層の役割:**

1.  **UI層 (sgpo_editor.gui):**
    *   ユーザーインターフェースの表示とユーザー操作の受付。
    *   Facadeを通じてデータの取得や更新を要求。
    *   **`EntryListFacade`** がテーブル行番号とエントリキーのマッピングを保持・管理。
    *   `QTableWidget` (または将来的に `QAbstractTableModel` + `fetchMore`) を使用して大量データを効率的に表示。
2.  **ファサード層 (sgpo_editor.gui.facades):**
    *   UI層とコア層（キャッシュ/DB）間のインターフェース。
    *   UIからの要求を解釈し、`EntryCacheManager` や `DatabaseAccessor` に適切なデータ要求を行う。
    *   `EntryCacheManager` から受け取った `EntryModel` オブジェクトをUIウィジェットに渡す。
3.  **キャッシュ層 (sgpo_editor.core.cache_manager):**
    *   **`EntryCacheManager`:** キャッシュ管理の責任を持つ中心クラス。
        *   **キャッシュ対象:** **`EntryModel` オブジェクト**。
        *   **キャッシュ種類:**
            *   **完全エントリキャッシュ:** キー (`str`) → `EntryModel`。単一取得用。
            *   **フィルタ結果キャッシュ:** フィルタ条件ハッシュ (`str`) → `List[EntryModel]`。フィルタ結果保持用。
        *   **管理:** カスタムLRUアルゴリズムに基づき、エントリ数と推定メモリサイズ上限の両方を考慮してキャッシュサイズを制御。
        *   **プリフェッチ:** UIからの要求に基づき、バックグラウンドでDBから`EntryModel`を先読みし、キャッシュを準備。
        *   **無効化:** SQLite の `update_hook` からの通知や、明示的な呼び出しにより、関連するキャッシュエントリやフィルタ結果を無効化/削除。
4.  **データアクセス層 (sgpo_editor.core.database_accessor, sgpo_editor.models.database):**
    *   **`DatabaseAccessor`:** SQLite DBへのアクセスを抽象化。
        *   **クエリ実行:** フィルタリング、ソート、検索（特に **FTS5 `MATCH`** を活用）をSQLレベルで実行。
        *   **結果返却:** クエリ結果を **`EntryDict` (または辞書/タプル)** 形式で `EntryCacheManager` または Facade に返す。
    *   **`InMemoryEntryStore`:** インメモリSQLiteデータベースの実装。FTS5仮想テーブルを含む。
    *   **`Update Hook`:** DBの変更（INSERT, UPDATE, DELETE）を検知し、`EntryCacheManager` にキャッシュ無効化を通知。

## 4. 主要コンポーネント詳細

*   **`EntryModel`:**
    *   Pydantic V2 ベース。データ検証機能は維持。
    *   DBから取得した辞書データからのインスタンス生成は、標準の `EntryModel(**data)` または `model_validate()` を使用する（高速性が確認されたため）。`model_construct()` は使用しない。
*   **`EntryCacheManager`:**
    *   **カスタムLRU:** `OrderedDict` や `cachetools` ライブラリなどを利用し、エントリ数と `sys.getsizeof()` を使った推定バイト数に基づいたメモリ上限を考慮したLRUキャッシュを実装する。
    *   **プリフェッチ:** `fetchMore` 機構 (UI層) と連携し、表示に必要な範囲の `EntryModel` をバックグラウンドでDBから取得し、キャッシュに追加する。
    *   **自動無効化:** SQLite の `update_hook` を利用し、DBの更新 (`UPDATE`, `DELETE`, `INSERT`) が発生した行に対応するキャッシュキーを特定し、`invalidate_entry()` を呼び出す。関連するフィルタキャッシュも適切に無効化する (`invalidate_filter_cache()` またはより高度な部分無効化)。
*   **`DatabaseAccessor`:**
    *   **FTS5検索:** キーワード検索には `MATCH` 演算子を使用するクエリを生成・実行する。
    *   **SQL最適化:** WHERE, ORDER BY, LIMIT, OFFSET を最大限活用し、Python側でのデータ処理を最小限にする。
*   **`InMemoryEntryStore`:**
    *   `entries` テーブルに対応する FTS5 仮想テーブル (`entries_fts`) を作成。
    *   `entries` テーブルへの更新をトリガーとして `entries_fts` を自動更新するように設定。
    *   適切なインデックスを作成。

## 5. データフロー例

### フィルタリング/検索

1.  UI層 (`SearchWidget`) でユーザーが条件（キーワード、状態）を入力。
2.  `EntryListFacade` が `update_table()` を呼び出す。
3.  `EntryListFacade` がフィルタ条件からキャッシュキーを生成。
4.  `EntryListFacade` が `EntryCacheManager.get_filter_cache(key)` を呼び出す。
5.  **(キャッシュヒット)** `EntryCacheManager` がキャッシュされた `List[EntryModel]` を返す。Facade は `TableManager` に渡す。
6.  **(キャッシュミス)**
    a.  `EntryCacheManager` が `None` を返す。
    b.  `EntryListFacade` が `DatabaseAccessor.advanced_search()` を呼び出す (FTS5 `MATCH` 使用)。
    c.  `DatabaseAccessor` が SQLite にクエリ実行し、`List[Dict]` を取得。
    d.  `EntryListFacade` が `List[Dict]` を受け取り、各辞書を `EntryModel(**d)` で `EntryModel` に変換。
    e.  `EntryListFacade` が変換後の `List[EntryModel]` を `EntryCacheManager.cache_filtered_entries(key, models)` でキャッシュ。
    f.  `EntryListFacade` が `List[EntryModel]` を `TableManager` に渡す。
7.  `TableManager` (または `QAbstractTableModel`) が `EntryModel` リストを使ってテーブル表示を更新 (`fetchMore` を利用する場合あり)。

### 単一エントリ取得 (例: 編集用)

1.  UI層 (`TableManager` または `EntryListFacade`) が選択された行からエントリキーを取得。
2.  `EntryEditorFacade` が `EntryCacheManager.get_complete_entry(key)` を呼び出す。
3.  **(キャッシュヒット)** `EntryCacheManager` がキャッシュされた `EntryModel` を返す。
4.  **(キャッシュミス)**
    a.  `EntryCacheManager` が `None` を返す。
    b.  `EntryEditorFacade` が `DatabaseAccessor.get_entry_by_key(key)` を呼び出す。
    c.  `DatabaseAccessor` が SQLite から `Dict` を取得。
    d.  `EntryEditorFacade` が `EntryModel(**data)` で `EntryModel` に変換。
    e.  `EntryEditorFacade` が `EntryCacheManager.cache_complete_entry(key, model)` でキャッシュ。
    f.  `EntryEditorFacade` が `EntryModel` を返す。
5.  `EntryEditorFacade` が取得した `EntryModel` を `EntryEditor` ウィジェットに渡して表示。

### エントリ更新

1.  UI層 (`EntryEditor`) でユーザーが編集し、適用 (`apply_clicked`)。
2.  `EntryEditorFacade` が `updater.update_entry_model(entry)` を呼び出す。
3.  `UpdaterComponent` が `DatabaseAccessor.update_entry(entry.to_dict())` を呼び出す。
4.  `DatabaseAccessor` が SQLite DB を更新。
5.  SQLite の `update_hook` が発火。
6.  フックコールバックが `EntryCacheManager.invalidate_entry(key)` と `invalidate_filter_cache()` を呼び出す。
7.  `EntryEditorFacade` が `entry_applied` シグナルを発行。
8.  `EntryListFacade` がシグナルを受け取り、`update_table_and_reselect(key)` を呼び出す。
9.  `update_table_and_reselect` 内で `update_table` が呼ばれ、無効化されたフィルタキャッシュによりDBから再取得・再表示される。

## 6. 最適化とメンテナンス

*   **LRUパラメータ:** キャッシュの最大エントリ数と推定メモリ上限は、実際の使用状況とプロファイリング結果に基づいて調整する。
*   **FTS5:** 大量のエントリを追加・更新した後は、`INSERT INTO entries_fts(entries_fts) VALUES('optimize');` を実行してインデックスを最適化する。アイドル時に `PRAGMA optimize;` を定期実行することも検討する。
*   **パフォーマンス計測:** `pytest-benchmark` を使用して主要な操作のKPIを設定し、CIで継続的に監視する。

## 7. 将来的な検討事項

*   **UI仮想化:** `QTableWidget` でのパフォーマンスがKPIを満たさない場合、`QAbstractTableModel` と `fetchMore` を実装し、データオンデマンドロードを実現する。

