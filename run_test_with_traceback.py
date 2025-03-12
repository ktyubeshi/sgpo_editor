"""詳細なエラー情報を出力するテスト実行スクリプト"""

import sys
import traceback

try:
    # テストを実行
    print("テストを実行します...")
    import pytest

    # テスト実行時に詳細なトレースバックを出力
    sys.argv = [
        "pytest",
        "tests/test_viewer_po_file.py",
        "-v",
        "--no-header",
        "--tb=native",
    ]

    # 標準出力と標準エラー出力をキャプチャ
    import io
    from contextlib import redirect_stderr, redirect_stdout

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        try:
            pytest.main()
        except Exception as e:
            print(f"pytest実行中にエラーが発生しました: {e}")
            traceback.print_exc()

    # キャプチャした出力を表示
    print("\n--- 標準出力 ---")
    print(stdout_capture.getvalue())

    print("\n--- 標準エラー出力 ---")
    print(stderr_capture.getvalue())

except Exception as e:
    print(f"エラーが発生しました: {e}")
    traceback.print_exc()
