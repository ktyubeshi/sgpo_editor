"""エントリ選択時のパフォーマンス計測スクリプト"""
import cProfile
import pstats
import time
import sys
import os
from pathlib import Path

# srcディレクトリをPYTHONPATHに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# ロギングを無効化
import logging
logging.basicConfig(level=logging.CRITICAL)

# Qt設定
from PySide6.QtCore import QCoreApplication, QSettings
QCoreApplication.setOrganizationName("SGPO")
QCoreApplication.setApplicationName("POEditor")

from sgpo_editor.gui.event_handler import EventHandler
from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.core.viewer_po_file import ViewerPOFile
from sgpo_editor.models.entry import EntryModel
from PySide6.QtWidgets import QApplication, QTableWidget

# プロファイリング結果の出力ディレクトリ
profile_dir = Path(__file__).parent / "profile_results"
profile_dir.mkdir(exist_ok=True)

def dummy_get_current_po():
    """テスト用のPOファイル取得関数"""
    po_file = ViewerPOFile()
    # サンプルデータを読み込む（実際のPOファイルがある場合はそれを使用）
    sample_po_path = Path(__file__).parent / "sample_data" / "sample.po"
    if sample_po_path.exists():
        po_file.load(str(sample_po_path))
    else:
        # サンプルデータがない場合はダミーデータを作成
        for i in range(100):
            entry = EntryModel(
                key=f"key_{i}",
                position=i,
                msgid=f"Source text {i}",
                msgstr=f"翻訳テキスト {i}",
                flags=["fuzzy"] if i % 3 == 0 else [],
                references=[f"file.py:{i+10}"] if i % 2 == 0 else []
            )
            po_file._entries.append(entry)
    return po_file

def dummy_update_table():
    """テスト用のテーブル更新関数"""
    pass

def dummy_show_status(msg, duration=0):
    """テスト用のステータス表示関数"""
    print(f"Status: {msg}")

def profile_entry_selection():
    """エントリ選択時のパフォーマンスを計測"""
    app = QApplication([])
    
    # テスト用のコンポーネントを作成
    table = QTableWidget()
    entry_editor = EntryEditor()
    
    # イベントハンドラを作成
    event_handler = EventHandler(
        table, 
        entry_editor,
        dummy_get_current_po,
        dummy_update_table,
        dummy_show_status
    )
    
    # テーブルの準備
    po_file = dummy_get_current_po()
    entries = po_file.get_filtered_entries()
    
    table.setRowCount(len(entries))
    table.setColumnCount(3)
    
    for i, entry in enumerate(entries):
        from PySide6.QtWidgets import QTableWidgetItem
        from PySide6.QtCore import Qt
        
        # キー列
        key_item = QTableWidgetItem(entry.key)
        key_item.setData(Qt.ItemDataRole.UserRole, entry.key)
        table.setItem(i, 0, key_item)
        
        # 原文列
        msgid_item = QTableWidgetItem(entry.msgid)
        table.setItem(i, 1, msgid_item)
        
        # 訳文列
        msgstr_item = QTableWidgetItem(entry.msgstr)
        table.setItem(i, 2, msgstr_item)
    
    # プロファイリング開始
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 時間計測開始
    start_time = time.time()
    
    # キャッシュなしの状態で各行を選択（最初の5行）
    print("=== キャッシュなしの状態での計測 ===")
    total_rows = min(5, table.rowCount())
    for row in range(total_rows):
        row_start_time = time.time()
        event_handler._update_detail_view(row)
        row_end_time = time.time()
        print(f"Row {row} 初回選択時間: {(row_end_time - row_start_time) * 1000:.2f} ms")
    
    # 同じ行を再度選択してキャッシュの効果を確認
    print("\n=== キャッシュありの状態での計測 ===")
    for row in range(total_rows):
        row_start_time = time.time()
        event_handler._update_detail_view(row)
        row_end_time = time.time()
        print(f"Row {row} 再選択時間: {(row_end_time - row_start_time) * 1000:.2f} ms")
    
    # ランダムな順序で選択してキャッシュの効果を確認
    print("\n=== ランダムな順序での再選択 ===")
    import random
    random_rows = [random.randint(0, total_rows-1) for _ in range(10)]
    for i, row in enumerate(random_rows):
        row_start_time = time.time()
        event_handler._update_detail_view(row)
        row_end_time = time.time()
        print(f"ランダム選択 {i+1} (Row {row}): {(row_end_time - row_start_time) * 1000:.2f} ms")
    
    # 時間計測終了
    end_time = time.time()
    
    # プロファイリング終了
    profiler.disable()
    
    # 結果の出力
    total_time = end_time - start_time
    
    print(f"\n総計測時間: {total_time * 1000:.2f} ms")
    
    # プロファイリング結果の保存
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    
    # テキスト形式で保存
    stats_file = profile_dir / "entry_selection_profile_with_cache.txt"
    with open(stats_file, 'w') as f:
        stats.stream = f
        stats.print_stats(30)  # 上位30件の結果を表示
    
    print(f"\n詳細なプロファイリング結果は以下に保存されました: {stats_file}")
    
    # 最も時間がかかっている関数を表示
    print("\n時間を最も消費している関数トップ10:")
    stats.sort_stats('cumulative').print_stats(10)

if __name__ == "__main__":
    profile_entry_selection()
