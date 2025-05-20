# SGPO Editor

POファイル編集のためのGUIアプリケーション

## 最近の更新

### コンポジションパターンの導入

- `ViewerPOFile` クラスが継承からコンポジションパターンによる実装に変更されました
- 以下のコンポーネントに分割されました：
  - `POFileBaseComponent`: POファイルの読み込みと基本操作
  - `EntryRetrieverComponent`: エントリの取得と検索
  - `FilterComponent`: エントリのフィルタリングとソート
  - `UpdaterComponent`: エントリの更新と変更管理
  - `StatsComponent`: 統計情報と保存機能
- 後方互換性のため `ViewerPOFileRefactored` は `ViewerPOFile` のエイリアスとして維持されています

## 使い方

POファイルを開き、編集、保存することができます。

詳細な使い方は準備中です。

## 開発

### 環境設定

依存関係は `uv` を用いて管理します。

```bash
git clone https://github.com/your-username/sgpo_editor.git
cd sgpo_editor
uv pip install -e .
```

### 実行

```bash
python -m sgpo_editor
```

### テスト・コードチェック

```bash
uv run pytest
uv run ruff check --fix
uv run ty check src --exit-zero
```

## ライセンス

MIT
