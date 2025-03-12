"""テスト実行用デバッグスクリプト"""

import os
import sys
import traceback

# srcディレクトリをPYTHONPATHに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    # テストファイルを直接インポート
    print("テストファイルを直接インポートします...")
    print("インポート成功")
except Exception as e:
    print(f"インポートエラーが発生しました: {e}")
    traceback.print_exc()
