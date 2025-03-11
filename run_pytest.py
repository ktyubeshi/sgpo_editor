"""Pythonパスを設定してテストを実行するスクリプト"""
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
    # テストを実行
    print(f"Pythonパス: {sys.path}")
    print("すべてのテストを実行します...")
    import pytest
    
    # すべてのテストを実行
    exit_code = pytest.main(["-v"])
    print(f"テスト実行結果: {exit_code}")
    
except Exception as e:
    print(f"エラーが発生しました: {e}")
    traceback.print_exc()
