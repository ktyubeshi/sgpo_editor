#!/usr/bin/env python3
"""
エントリエディタデモ実行ランチャー

このスクリプトは、Pythonのパスに必要なディレクトリを追加してからデモアプリを実行します。
"""

import os
import sys
import logging

def main():
    # 現在のファイルのディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # プロジェクトのルートディレクトリを計算（src/demo_widgetの親の親）
    project_root = os.path.dirname(os.path.dirname(current_dir))
    
    print(f"Python検索パス: {sys.path}")
    
    try:
        # 絶対インポートを使用
        from src.demo_widget import entry_editor_demo
        entry_editor_demo.main()
    except ImportError as e:
        logging.error(f"モジュールのインポートに失敗しました: {e}")
        
        # デバッグ情報の出力
        print(f"カレントディレクトリ: {os.getcwd()}")
        print(f"プロジェクトルート: {project_root}")
        print(f"ファイルパス: {__file__}")
        
        # エラーを再発生させる
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main() 