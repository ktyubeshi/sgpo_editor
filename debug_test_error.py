"""テストエラーのデバッグ用スクリプト"""

import os
import sys
import traceback

# srcディレクトリをPYTHONPATHに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    # テストファイルをインポート
    print("テストファイルをインポートします...")
    from tests.test_viewer_po_file import test_po_file

    print("インポート成功！")

    # pytestを実行して詳細なエラー情報を取得
    print("\npytestを実行します...")
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # test_po_file関数を直接実行
        print("test_po_file関数を実行中...")
        try:
            po_file = test_po_file(tmp_path)
            print("test_po_file関数の実行成功！")
        except Exception as e:
            print(f"test_po_file関数の実行エラー: {e}")
            traceback.print_exc()

except Exception as e:
    print(f"エラーが発生しました: {e}")
    traceback.print_exc()
