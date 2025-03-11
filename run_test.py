"""テスト実行用スクリプト"""
import sys
import traceback

try:
    import pytest
    # テストを実行
    print("テストを実行します...")
    sys.argv = ["pytest", "tests/test_viewer_po_file.py", "-v"]
    pytest.main()
except Exception as e:
    print(f"エラーが発生しました: {e}")
    traceback.print_exc()
