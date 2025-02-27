#!/usr/bin/env python
"""
すべてのテストを実行するスクリプト

セグメンテーションフォルトを回避するために、各テストファイルを個別のプロセスで実行します。
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """メイン関数"""
    print("すべてのテストを実行します...")
    
    # run_tests.pyを実行
    result = subprocess.run(
        [sys.executable, "run_tests.py", "--verbose"],
        capture_output=False,
        text=True
    )
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main()) 