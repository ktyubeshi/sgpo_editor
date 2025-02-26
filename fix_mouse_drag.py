#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
マウスドラッグ時の選択問題を修正するスクリプト
"""

import os

def fix_mouse_drag_issue():
    """マウスドラッグ時の選択問題を修正する"""
    file_path = os.path.join('sgpo_editor', 'gui', 'main_window.py')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # _on_cell_enteredメソッドを修正
    if 'def _on_cell_entered(' in content and 'mouseButtons()' in content:
        # mouseButtons()の呼び出しを修正
        content = content.replace(
            'if self.table.mouseButtons() & Qt.MouseButton.LeftButton:',
            'from PySide6.QtWidgets import QApplication\n        if QApplication.mouseButtons() & Qt.MouseButton.LeftButton:'
        )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("マウスドラッグ時の選択問題を修正しました。")

if __name__ == "__main__":
    fix_mouse_drag_issue()
