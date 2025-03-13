---
title: Nuitkaを使用したPython実行ファイルのビルドガイド
date: 2025-03-13
status: reviewed
author: 
description: Nuitkaを使用したPython/PySide6アプリケーションの実行ファイル化手順と最適化方法
---

# Nuitkaを使用したPython実行ファイルのビルドガイド

## 概要

このドキュメントでは、Nuitkaを使用してPythonアプリケーションを実行ファイルにコンパイルする方法について説明します。特に、PySide6（Qt for Python）を使用したGUIアプリケーションのビルドに焦点を当てています。なお、パッケージ管理は高速かつ再現性の高い**uv**を使用します。

## 前提条件

このガイドは以下の環境を前提としています：

1. **Python環境**
   - Python 3.9以上（PySide6のサポートを踏まえて推奨）
   - uv（パッケージマネージャー）を使用したプロジェクト管理  
     ※uvはプロジェクトディレクトリ内に仮想環境（`.venv`）を自動作成し、依存関係をロック可能です。
     
2. **使用するフレームワーク**
   - PySide6（Qt for Python）を使用したGUIアプリケーション
   - Nuitkaによる実行ファイルのビルド

3. **必要なパッケージ**

   ```bash
   # 基本パッケージの追加（uvは内部で仮想環境を管理）
   uv add pyside6

   # ビルド用パッケージの追加（オプショナル依存）
   uv add nuitka ordered-set zstandard --dev
   ```

## プロジェクト構成

### 推奨ディレクトリ構造

```
project_root/
├── src/
│   └── your_package/
│       ├── __init__.py
│       └── __main__.py  # Nuitkaプロジェクトオプションを含む
├── resources/       # アプリケーションリソース
│   ├── app.ico     # Windowsアイコン
│   ├── app.icns    # macOSアイコン
│   └── app.png     # Linuxアイコン
├── build/          # ビルド成果物
├── docs/           # ドキュメント
├── tests/          # テスト
├── build.py        # ビルドスクリプト（エントリポイントのソースにオプションを記述する場合は不要）
└── pyproject.toml  # プロジェクト設定
```

### 依存関係の管理

`pyproject.toml`での依存関係指定例は以下の通りです。  
（uvは`uv.lock`によりロックファイルを自動生成し、再現性のある環境を実現します。）

```toml
[project]
name = "your-package"
version = "0.1.0"
description = "Your application description"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "pyside6>=6.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/your_package"]

[project.optional-dependencies]
build = [
    "nuitka>=2.6",
    "ordered-set",  # Nuitkaの依存パッケージ
    "zstandard",    # Nuitkaの依存パッケージ
]

[project.scripts]
your-package = "your_package.__main__:main"

[tool.ruff]
line-length = 120
target-version = "py39"
```

## Nuitkaプロジェクトオプション

### 設定方法の選択

Nuitkaのビルド設定には主に2つのアプローチがあります：

1. **ソースコードでの設定（推奨）**
   - ソース内に`nuitka-project:`コメントを記述する方法  
     コードと設定を同一箇所で管理でき、バージョン管理もしやすいです。
     
2. **ビルドスクリプトでの設定**
   - Pythonスクリプト（`build.py`）でコマンドラインオプションを構築する方法  
     複雑なビルドロジックや、複数ターゲットの一括ビルドなどに有効です。

基本的なビルドではソースコード内での設定が推奨されますが、必要に応じてビルドスクリプトの利用も検討してください。

### 基本オプション

| オプション                     | 説明                                            | 推奨設定          |
|--------------------------------|-------------------------------------------------|-------------------|
| `--standalone`                 | 依存ライブラリを含めた単独実行可能なビルド        | 必須              |
| `--follow-imports`             | 依存関係を自動追跡                              | 推奨              |
| `--include-package-data`       | パッケージデータを含める                        | 必要に応じて      |
| `--enable-plugin=pyside6`      | PySide6サポートを有効化                         | PySide6使用時必須 |

### バージョン情報オプション

| オプション                 | 説明                                 | 値の例            |
|----------------------------|--------------------------------------|-------------------|
| `--product-name`           | 製品名                               | デフォルトはバイナリのベース名 |
| `--product-version`        | 製品バージョン                       | `1.0.0.0`         |
| `--file-version`           | ファイルバージョン（Windows）        | `1.0.0.0`         |
| `--file-description`       | ファイルの説明                       | 任意のテキスト    |
| `--copyright`              | 著作権情報                           | 著作権表示        |
| `--trademark`              | 商標情報                             | 商標表示          |

### プラットフォーム固有のオプション

#### Windows

| オプション                       | 説明                       | 値の例              |
|----------------------------------|----------------------------|---------------------|
| `--windows-icon-from-ico`        | アプリケーションアイコン   | `path/to/icon.ico`  |
| `--windows-company-name`         | 会社名                     | `"Your Company"`    |
| `--windows-product-version`      | 製品バージョン             | `1.0.0.0`           |
| `--windows-file-version`         | ファイルバージョン         | `1.0.0.0`           |
| `--windows-uac-admin`            | 管理者権限要求             | フラグ（値不要）    |
| `--windows-uac-uiaccess`         | UIアクセス権限             | フラグ（値不要）    |

#### macOS

| オプション                     | 説明                         | 値の例              |
|--------------------------------|------------------------------|---------------------|
| `--macos-create-app-bundle`    | .appバンドルを作成           | 必須                |
| `--macos-app-icon`             | アプリケーションアイコン     | `path/to/icon.icns` |
| `--macos-app-name`             | アプリケーション名           | `"App Name"`        |
| `--macos-signed-app`           | アプリケーション署名         | 配布時推奨          |
| `--macos-target-arch`          | ターゲットアーキテクチャ     | `x86_64,arm64`      |

#### Linux

| オプション               | 説明                       | 値の例            |
|--------------------------|----------------------------|-------------------|
| `--linux-icon`           | アプリケーションアイコン   | `path/to/icon.png`|

### デバッグ用オプション

| オプション         | 説明                   | 使用時の注意                     |
|--------------------|------------------------|----------------------------------|
| `--enable-console` | コンソール出力を有効化 | デバッグ時のみ                   |
| `--debug`          | デバッグ情報を含める   | ビルドサイズが増加する可能性あり |
| `--unstripped`     | シンボル情報を保持     | デバッグ時のみ                   |
| `--report`         | ビルドレポートを生成   | `compilation-report.xml`         |

## ベストプラクティス

### コンパイルモードの選択

1. **非デプロイメントモード（デフォルト）**
   - 開発時の使用に適しており、より詳細なエラー情報を提供するため、ユーザーエラーの検出を支援します。

2. **デプロイメントモード**
   - `--deployment`オプションで有効化し、本番環境向けのビルドに使用します。安全性チェックとヘルパーを無効化します。

### パフォーマンスの考慮事項

1. **Pythonのリンク方式**
   - 可能な場合は静的リンクを推奨します。DLL使用時はパフォーマンスが低下する可能性があるため注意してください。Anacondaを利用している場合は、`conda install libpython-static`が必要な場合があります。

2. **ビルド時の最適化**
   - Windows DefenderやIndexing Serviceなどをビルドディレクトリから除外し、不要なモジュールは含めないようにします。

### 実行時の検出

- `sys.frozen`は使用せず、モジュールや関数の`__compiled__`属性でコンパイル状態を確認します。

### LGPLライセンスコンプライアンス

PySide6（Qt）を使用する場合：

1. **one-fileモードは避ける**
   - 一つの実行ファイルに全てをまとめると、動的リンクライブラリの置き換えができなくなり、LGPLライセンスに抵触する恐れがあります。

2. **standaloneモードを使用**
   - 必要なライブラリが個別に同梱され、ユーザーがライブラリを置き換え可能な状態を維持できます。

### パフォーマンス最適化

1. **ビルド時間の短縮**
   - 不要なQt翻訳ファイルを除外するために`--noinclude-qt-translations`を使用し、アンチウイルスソフトウェアの除外設定も行います。

2. **成果物サイズの最適化**
   - 必要なパッケージのみを含め、デバッグ情報は必要な場合のみ含めるようにします。

### クロスプラットフォーム対応

1. **アイコンファイル**
   - Windowsは`.ico`、macOSは`.icns`、Linuxは`.png`形式のアイコンを使用します。

2. **出力ディレクトリ構造**

```
build/
├── windows-x86_64/
├── macos-universal2/
└── linux-x86_64/
```

## トラブルシューティング

### 一般的な問題と解決策

1. **依存関係の解決失敗**
   - `--follow-imports`の使用、明示的な依存パッケージの指定、ビルドレポートの確認を行います。

2. **リソースファイルの不足**
   - パッケージデータの明示的な同梱、アイコンファイルパスの確認、相対パスを絶対パスへ変換するなどの対策を検討します。

3. **プラットフォーム固有の問題**
   - Windows：UACオプションはフラグとして指定します。
   - macOS：Universal Binaryの対応を確認します。
   - Linux：適切な権限設定を行います。

### ビルドレポートの活用

`compilation-report.xml`で以下の点を確認してください：

1. **依存関係**
   - 必要なモジュールが含まれているか
   - 不要なモジュールが含まれていないか

2. **警告とエラー**
   - インポートエラー、未解決の依存関係、プラグインの問題を確認します。

3. **リソース**
   - 必要なファイルが含まれているか、パスが正しく解決されているかをチェックします。

## 設定例

### ソースコードでの設定例

`__main__.py`での設定例：

```python
"""アプリケーションのエントリーポイント"""
# 共通オプション
# nuitka-project: --standalone
# nuitka-project: --enable-plugin=pyside6
# nuitka-project: --follow-imports
# nuitka-project: --include-package-data=your_package
# nuitka-project: --noinclude-qt-translations

# プラットフォーム固有のオプション
# nuitka-project-if: {OS} == "Windows":
#    nuitka-project: --windows-icon-from-ico=resources/app.ico
#    nuitka-project: --product-name="App Name"
#    nuitka-project: --product-version=1.0.0.0

# デバッグビルド設定
# nuitka-project-if: os.getenv("DEBUG_COMPILATION", "no") == "yes":
#    nuitka-project: --enable-console
#    nuitka-project: --debug

import sys
from PySide6.QtWidgets import QApplication
# ... アプリケーションコード
```

### ビルドスクリプトでの設定例

`build.py`での設定例：

```python
"""Nuitkaを使用したビルドスクリプト"""
import os
import platform
import subprocess
import sys
from pathlib import Path

def get_arch():
    """システムアーキテクチャを取得"""
    return "x86_64" if platform.machine().endswith("64") else "x86"

def get_resource_path(filename):
    """リソースファイルの絶対パスを取得"""
    return str(Path(__file__).parent / "resources" / filename)

def get_build_options(debug=False):
    """ビルドオプションを生成

    Args:
        debug (bool): デバッグビルドフラグ

    Returns:
        list: Nuitkaコマンドラインオプション
    """
    # 共通オプション
    options = [
        "--standalone",
        "--enable-plugin=pyside6",
        "--follow-imports",
        "--include-package-data=your_package",
        "--noinclude-qt-translations",
        "--product-name=Your App",
        "--product-version=0.1.0",
        "--file-description=Your Application Description",
        "--copyright=Copyright (c) 2024",
    ]

    # プラットフォーム固有のオプション
    if sys.platform == "win32":
        options.extend([
            f"--windows-icon-from-ico={get_resource_path('app.ico')}",
            "--output-filename=app.exe",
            "--windows-company-name=Your Company",
            "--windows-product-version=0.1.0.0",
            "--windows-file-version=0.1.0.0",
            "--windows-uac-admin",
            "--windows-uac-uiaccess",
        ])
        build_dir = f"build/windows-{get_arch()}"
    elif sys.platform == "darwin":
        options.extend([
            "--macos-create-app-bundle",
            f"--macos-app-icon={get_resource_path('app.icns')}",
            "--macos-app-name=Your App",
            "--output-filename=app",
            "--macos-signed-app",
            "--macos-target-arch=x86_64,arm64",
        ])
        build_dir = "build/macos-universal2"
    else:  # Linux
        options.extend([
            f"--linux-icon={get_resource_path('app.png')}",
            "--output-filename=app",
        ])
        build_dir = f"build/linux-{get_arch()}"

    # デバッグビルド設定
    if debug:
        options.extend([
            "--enable-console",
            "--debug",
            "--unstripped",
        ])
        build_dir = f"build/debug-{sys.platform}-{get_arch()}"

    options.append(f"--output-dir={build_dir}")
    return options

def run_pre_build_tasks():
    """ビルド前の準備タスクを実行"""
    # 例: リソースファイルの生成、依存パッケージの確認など
    pass

def run_post_build_tasks(build_dir):
    """ビルド後の後処理タスクを実行

    Args:
        build_dir (str): ビルド出力ディレクトリ
    """
    # 例: 追加ファイルのコピー、パーミッションの設定など
    pass

def main():
    """ビルドプロセスを実行"""
    # コマンドライン引数の解析
    debug = "--debug" in sys.argv

    try:
        # ビルド前タスク
        run_pre_build_tasks()

        # ビルドオプションの生成
        options = get_build_options(debug)
        
        # ビルドコマンドの構築と実行
        cmd = [sys.executable, "-m", "nuitka"] + options + ["src/your_package/__main__.py"]
        print("Building with options:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        # ビルド後タスク
        build_dir = next(p for p in options if p.startswith("--output-dir=")).split("=")[1]
        run_post_build_tasks(build_dir)

    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```
