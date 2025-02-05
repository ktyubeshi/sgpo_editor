"""コマンドラインインターフェース"""
import argparse
from pathlib import Path

from po_viewer.core.po_file import POFile


def main():
    """コマンドラインインターフェースのエントリポイント"""
    parser = argparse.ArgumentParser(description="POファイルビューワー")
    parser.add_argument("file", help="POファイルのパス")
    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"エラー: ファイルが見つかりません: {file_path}")
        return 1
    
    po_file = POFile(file_path)
    stats = po_file.get_stats()
    
    print(f"ファイル: {stats.file_name}")
    print(f"総数: {stats.total}")
    print(f"翻訳済み: {stats.translated}")
    print(f"未翻訳: {stats.untranslated}")
    print(f"ファジー: {stats.fuzzy}")
    print(f"進捗率: {stats.progress:.1f}%")
    
    return 0

if __name__ == "__main__":
    main()
