# コーディングエージェント向け ToDo リスト: 最新設計への移行

**目的:** コードとテストを最新の設計（ViewerPOFileコンポーネント分割、新しいキャッシュ戦略、EntryModel改善など）に合わせます。古い互換APIは残しません。

---

## Phase 1: ViewerPOFile API & キャッシュ連携

### `src/sgpo_editor/core/cache_manager.py`
- [ ] `invalidate_filter_cache(filter_key: Optional[str] = None)` メソッドを実装します。
    - `filter_key` が指定された場合は、該当するフィルターキャッシュのみを削除します。
    - `filter_key` が `None` の場合は、すべてのフィルターキャッシュを削除します。
    - （依存タスク）フィルタキーの生成ロジックを `ViewerPOFileFilter` から呼び出せるように、ヘルパーメソッドまたはクラス設計を検討・実装します。
- [ ] `EntryCacheManager` の基本実装（ファイルレビュー済）に、LRU（Least Recently Used）ロジックとサイズ制限の強制を実装します。
- [ ] `EntryCacheManager` にフィルター結果（`List[EntryId]`）をキャッシュする機能（`get_filtered_ids`, `cache_filtered_ids`）を実装します。

### `src/sgpo_editor/core/viewer_po_file_filter.py`
- [ ] `get_filtered_entries` メソッド（または関連メソッド）内で、引数として渡される `filter_keyword` と、クラスインスタンス変数（例: `self.search_text` など）に保持されているフィルタ条件をマージするロジックを実装します。
- [ ] フィルター条件が更新され、再フィルタリングが必要な場合（例: `update_filter=True` のような引数や状態変更時）に、`EntryCacheManager.invalidate_filter_cache()` を適切な `filter_key` で呼び出す処理を追加します。
    - （依存タスク）`cache_manager.py` で実装されたキー生成ロジックを利用します。

### `src/sgpo_editor/core/viewer_po_file_updater.py`
- [ ] `update_entry_model(self, entry_model: EntryModel, ...) ` メソッドの公開インターフェース（引数、戻り値）を最終確認し、仕様に沿っていることを確認します。
- [ ] `update_entry_model` メソッドの docstring を、最終的なインターフェースに合わせて更新します。
- [ ] エントリ更新時に、関連するキャッシュ（`EntryCacheManager` のエントリキャッシュやフィルターキャッシュ）を適切に無効化する処理を追加します（例: `cache_manager.invalidate(...)` の呼び出し）。

### `tests/integration/test_viewer_po_file_refactored.py`
- [ ] `viewer.update_entry_model(...)` の呼び出し箇所を、新しいインターフェース `viewer.updater.update_entry_model(...)` を使うように書き換えます。
- [ ] 不要になった旧 `viewer.update_entry_model` API へのモック設定があれば削除します。

### `tests/integration/test_viewer_po_file_filtered_entries.py`
- [ ] `db_accessor.get_filtered_entries` のモック設定で、期待される引数（フィルタ条件の形式など）を、`viewer_po_file_filter.py` で実装された最新の仕様に合わせます。
- [ ] `update_filter=True` （または同等の条件）でフィルターが実行されるテストケースにおいて、`EntryCacheManager.invalidate_filter_cache` が呼び出されることをモックで確認（`assert_called_once_with` など）するアサーションを追加します。

---

## Phase 2: EntryModel & データ変換

### `src/sgpo_editor/models/entry.py`
- [ ] `flags` 属性に値が設定される際、または初期化時に、すべてのフラグ文字列が小文字 (`lower()`) で保持されるように処理を追加します（例: `field_validator` 内や `__init__`）。
- [ ] `@property def fuzzy(self) -> bool:` を実装または修正し、`self.flags` 内に 'fuzzy' という文字列が大文字・小文字に関わらず存在するかどうかで判定するようにします (例: `any(flag.lower() == 'fuzzy' for flag in self.flags)`)。
- [ ] `validate_flags` という `field_validator` を `flags` フィールドに追加、または既存のものを強化し、不正なフラグ形式（例: 空白を含むなど）をチェックまたは整形するロジックを追加します。
- [ ] `comment` 属性の型ヒント `Optional[str]` と `occurrences` 属性の型ヒント `List[Tuple[str, Union[str, int]]]` が、実際の利用箇所と整合性が取れているか再確認し、必要であれば関連コード（値の設定箇所）を修正します。 `occurrences` のバリデータ (`parse_occurrences`) が期待通り動作することを確認します。

### `src/sgpo_editor/core/viewer_po_file_entry_retriever.py`
- [ ] データベース (`DatabaseAccessor`) からエントリデータを辞書形式で受け取る箇所で、その辞書を `EntryModel.model_validate()` メソッド（Pydantic v2）を使用して `EntryModel` インスタンスに変換・検証する処理を**必ず**行うようにします。

### `tests/models/entry/test_entry_model.py`
- [ ] `entry4` （または 'fuzzy' フラグを持つ他のテスト用エントリ）のテストケースで、`entry.fuzzy` プロパティの期待値を `True` に修正します（大文字・小文字非依存の判定ロジック変更に対応）。

### `tests/models/entry/test_entry_structure.py` および `tests/models/entry/test_entry_list_integration.py`
- [ ] テストデータとして辞書 (`dict`) を使用している箇所があれば、原則として `EntryModel` のインスタンスを使用するように期待データやモックの戻り値を差し替えます。

---

## Phase 3: Statistics Component

### `src/sgpo_editor/core/viewer_po_file_stats.py`
- [ ] `DatabaseAccessor` から統計関連のカウント数（例: `count_entries`, `get_translation_status_counts` など）を取得する箇所で、戻り値が `int` 型であることを確認する型チェック（`isinstance` など）またはアサーションを追加します。もし `int` でない場合に警告ログを出力するか、エラーハンドリングを行います。

### `tests/integration/test_viewer_po_file_stats.py`
- [ ] `db_accessor.count_entries` （および他のカウント系メソッド）のモック (`MagicMock` など) の `return_value` に、必ず `int` 型の値を設定するように修正します。これにより、テスト内で発生する可能性のある `MagicMock` オブジェクトと `int` の比較エラーを解消します。

---

## Phase 4: GUI & Recent-Files 周り

### `tests/gui/test_keyword_filter/test_main_window_filter.py`
- [ ] フィルター結果を取得する際のモックの戻り値設定のチェーン (`mock_xyz.return_value. ... .return_value = ...`) を、現在のファサードとコンポーネントの構造に合わせて修正します。具体的には、`main_window.entry_list_facade._get_current_po().get_filtered_entries.return_value` のような、実際の呼び出しパスに即した形にします。

### `src/sgpo_editor/gui/main_window.py`
- [ ] `_show_preview_dialog()` メソッド（または関連するプレビュー表示ロジック）内で、ダイアログ (`dialog`) を表示する前に、`dialog.set_entry(current_entry)` を呼び出す処理を追加します。
- [ ] `current_entry` が `None` の場合にはプレビューダイアログを表示しない、または適切にハンドルするガード節 (`if current_entry is None: return`) を追加します。

### `tests/gui/widgets/test_preview_widget.py`
- [ ] `PreviewWidget.set_entry` が呼び出されることのアサーションを、`PreviewWidget` のモックではなく、`PreviewDialog` のモック（`dialog_mock.set_entry.assert_called_with(...)` のような形）に対して行うように修正します（`main_window.py` の変更に合わせる）。

### `src/sgpo_editor/gui/table_manager.py` （または `src/sgpo_editor/gui/recent_files_manager.py` が存在する場合）
- [ ] 「最近使ったファイル」メニュー項目を生成するロジックで、表示されるテキスト形式を `&1. filename`, `&2. filename` のように、アンパサンド(&) + 番号 + ピリオド + スペース + ファイル名、という形式で統一します。

### `tests/utils/test_recent_files.py` および `tests/core/recent_files/test_recent_files.py` (該当する場合)
- [ ] 最近使ったファイル関連のテストで、期待されるメニュー項目の文字列を `"&<index>. <filename>"` 形式に更新します。
- [ ] メニューアクションの数に関するアサーションがあれば、現在の仕様（表示されるファイル数など）に合わせて修正します。

---

## Phase 5: ドキュメント & ロギング

### `_doc/updated_filtering_logic.md` (または関連ドキュメント)
- [ ] Phase 1 で実装・変更されたフィルタリング処理とキャッシュ戦略（キーワードとインスタンス変数のマージ、キャッシュキー生成、キャッシュ無効化フローなど）について、最新のコードの動作に合わせて説明を追記・更新します。

### `src/` ディレクトリ配下の各コンポーネントファイル
- [ ] 設計ガイドラインに従い、デバッグに有用な情報を `logger.debug()` を用いて出力するログ文を補完します。特に以下の箇所を重点的に行います。
    - `ViewerPOFileFilter`: フィルタリング条件がどのように生成・マージされたか。
    * `EntryCacheManager`: キャッシュのヒット/ミス判定、キャッシュの追加/削除/無効化イベント、キャッシュサイズ。
    - `ViewerPOFileUpdater`: どのエントリが更新され、どのキャッシュが無効化されたか。
    - `ViewerPOFileEntryRetriever`: DBからの取得件数、`EntryModel` への変換状況。

---