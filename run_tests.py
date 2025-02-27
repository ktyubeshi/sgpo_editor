#!/usr/bin/env python
"""
テストを個別に実行するスクリプト

セグメンテーションフォルトを回避するために、各テストファイルを個別のプロセスで実行します。
"""

import os
import subprocess
import sys
import argparse
from pathlib import Path


def run_test(test_file, verbose=True, coverage=False):
    """指定されたテストファイルを実行する"""
    print(f"\n{'='*80}")
    print(f"実行中: {test_file}")
    print(f"{'='*80}")
    
    # テストコマンドを構築
    cmd = [sys.executable, "-m", "pytest", test_file]
    if verbose:
        cmd.append("-v")
    if coverage:
        cmd.extend(["--cov=sgpo_editor", "--cov-report=term-missing"])
    
    # テストコマンドを実行
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    
    # 結果を表示
    print(result.stdout)
    if result.stderr:
        print("エラー出力:")
        print(result.stderr)
    
    return result.returncode == 0


def main():
    """メイン関数"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="テストを個別に実行するスクリプト")
    parser.add_argument("--file", "-f", help="実行する特定のテストファイル")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細な出力を表示")
    parser.add_argument("--coverage", "-c", action="store_true", help="カバレッジレポートを生成")
    parser.add_argument("--skip", "-s", nargs="+", help="スキップするテストファイル")
    args = parser.parse_args()
    
    # テストディレクトリのパス
    test_dir = Path("tests")
    
    # スキップするファイルのリスト
    skip_files = [
        "test_all_main_window.py", 
        "test_main_window.py",
        "test_main_window_table.py"
    ]
    
    if args.skip:
        skip_files.extend(args.skip)
    
    # テストファイルのリスト
    if args.file:
        # 特定のファイルのみ実行
        test_files = [args.file]
    else:
        # すべてのテストファイルを実行（スキップするファイルを除く）
        test_files = [
            str(f) for f in test_dir.glob("test_*.py")
            if f.name not in skip_files
        ]
    
    # 各テストファイルを実行
    success_count = 0
    failure_count = 0
    
    for test_file in test_files:
        if run_test(test_file, args.verbose, args.coverage):
            success_count += 1
        else:
            failure_count += 1
    
    # 結果のサマリーを表示
    print(f"\n{'='*80}")
    print(f"テスト結果サマリー")
    print(f"{'='*80}")
    print(f"成功: {success_count}")
    print(f"失敗: {failure_count}")
    print(f"合計: {success_count + failure_count}")
    
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main()) 