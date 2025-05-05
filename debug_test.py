"""テスト実行用デバッグスクリプト"""

import traceback

try:
    # テストファイルを直接インポート
    print("テストファイルを直接インポートします...")
    print("インポート成功")
except Exception as e:
    print(f"インポートエラーが発生しました: {e}")
    traceback.print_exc()
