"""Nuitkaビルドスクリプト"""
import os
import platform
import subprocess
import sys
from pathlib import Path


def get_arch() -> str:
    """システムアーキテクチャを取得"""
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64"):
        return "x86_64"
    elif machine in ("arm64", "aarch64"):
        return "arm64"
    else:
        return machine


def main():
    """Nuitkaビルドを実行"""
    try:
        # ビルドディレクトリの作成
        build_dir = Path("build")
        build_dir.mkdir(exist_ok=True)

        # Nuitkaコマンドの実行
        cmd = [sys.executable, "-m", "nuitka", "sgpo_editor/__main__.py"]
        print("Building with Nuitka:", " ".join(cmd))
        subprocess.run(cmd, check=True)

        print("Build completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 