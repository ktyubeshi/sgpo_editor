"""テスト実行用デバッグスクリプト"""
import os
import sys
import traceback

# srcディレクトリをPYTHONPATHに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    # テストファイルを直接インポート
    print("テストファイルを直接インポートします...")
    from tests.test_viewer_po_file import test_po_file, test_load_po_file, test_get_entries
    print("インポート成功")
except Exception as e:
    print(f"インポートエラーが発生しました: {e}")
    traceback.print_exc()
