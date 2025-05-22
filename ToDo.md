## 現在の失敗テスト（4件）

### 1. フィルター機能の型不整合問題
- **テスト**: `tests/core/filter/test_filter_reset_advanced.py::test_filter_reset_after_complex_filter`
- **テスト**: `tests/gui/keyword_filter/test_keyword_filter.py::TestKeywordFilter::test_filter_text_and_keyword_together`
- **問題**: `translation_status`パラメータの型不整合
  - **期待値**: 文字列 `"all"` または `"translated"`
  - **実際の値**: セット `{'translated', 'untranslated'}`
- **根本原因**: `SearchCriteria`と`DatabaseAccessor.advanced_search`間の型変換処理に不整合がある

### 2. POファイル保存機能の問題
- **テスト**: `tests/integration/test_viewer_po_file.py::test_save_po_file`
- **エラー**: `'EntryModel' object has no attribute 'msgid_plural'`
- **根本原因**: `POFileBaseComponent._convert_entry_model_to_po_entry`メソッドで、`EntryModel`に存在しない属性（`msgid_plural`, `msgstr_plural`）にアクセスしている
- **場所**: `src/sgpo_editor/core/po_components/base.py:295-296`

### 3. EntryModelの生成問題
- **テスト**: `tests/models/test_models.py::test_entry_model`
- **エラー**: `'NoneType' object has no attribute 'msgid'`
- **根本原因**: `EntryModel.from_po_entry`メソッドが例外をキャッチして`None`を返している
- **詳細**: `flags`属性の取得時に例外が発生し、メソッドが`None`を返すケースがある

## 修正の優先順位

1. **緊急**: POファイル保存機能の修正（`msgid_plural`/`msgstr_plural`属性の追加または条件分岐）
2. **重要**: `translation_status`型不整合の修正（SearchCriteriaとDatabaseAccessor間の型変換）
3. **重要**: `EntryModel.from_po_entry`の例外処理改善（より具体的なエラーハンドリング）

## 技術的詳細

### translation_status型不整合の詳細
```python
# 期待される呼び出し
advanced_search(translation_status="all")

# 実際の呼び出し
advanced_search(translation_status={'translated', 'untranslated'})
```

### 保存機能エラーの詳細
```python
# 問題のあるコード（base.py:295-296）
po_entry.msgid_plural = entry_model.msgid_plural  # AttributeError
po_entry.msgstr_plural = entry_model.msgstr_plural or {}  # AttributeError
```

### EntryModel生成エラーの詳細
```python
# from_po_entryメソッドで例外をキャッチしてNoneを返している
try:
    flags = getattr(po_entry, "flags", [])
except Exception as e:
    logger.debug("Exception when getting flags: %r", e)
    return None  # これが問題
```
