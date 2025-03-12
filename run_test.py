"""テスト実行用スクリプト"""

import os
import sys
import traceback

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# srcディレクトリをPythonパスに追加
src_dir = os.path.join(project_root, "src")
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

try:
    import pytest

    # テストを実行
    print("テストを実行します...")
    print(f"Pythonパス: {sys.path}")

    # コマンドライン引数を処理
    args = sys.argv[1:] if len(sys.argv) > 1 else ["tests"]
    pytest_args = ["pytest"] + args

    print(f"実行コマンド: {' '.join(pytest_args)}")
    pytest.main(args)
except Exception as e:
    print(f"エラーが発生しました: {e}")
    traceback.print_exc()
