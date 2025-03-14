"""エントリエディタのファサードモジュール

このモジュールは、エントリ編集に関連する操作をカプセル化するファサードクラスを提供する。
複雑なシグナルフローを単純化し、責務を明確にすることを目的としている。
"""

import logging
from typing import Any, Callable, Optional, Union

from PySide6.QtCore import QObject, Signal

from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class EntryEditorFacade(QObject):
    """エントリ編集に関連する操作をカプセル化するファサードクラス
    
    このクラスは、エントリの編集、適用、取得などの操作に関するシンプルなインターフェイスを提供する。
    内部的には EntryEditor と連携して動作する。
    """
    
    # シグナル定義
    entry_applied = Signal(int)  # エントリ適用時に発行。引数はエントリ番号
    entry_changed = Signal()     # エントリ内容が変更された時に発行
    
    def __init__(self, 
                 entry_editor: EntryEditor, 
                 get_current_po: Callable,
                 show_status: Callable[[str, int], None]) -> None:
        """初期化
        
        Args:
            entry_editor: エントリエディタコンポーネント
            get_current_po: 現在のPOファイルを取得する関数
            show_status: ステータスメッセージを表示する関数
        """
        super().__init__()
        self._entry_editor = entry_editor
        self._get_current_po = get_current_po
        self._show_status = show_status
        
        # エントリエディタのシグナルを接続
        self._entry_editor.text_changed.connect(self._on_text_changed)
        
    def set_entry(self, entry: Optional[EntryModel]) -> None:
        """エントリをエディタにセット
        
        Args:
            entry: セットするエントリ
        """
        self._entry_editor.set_entry(entry)
    
    def get_current_entry(self) -> Optional[EntryModel]:
        """現在エディタで編集中のエントリを取得
        
        Returns:
            現在のエントリ
        """
        return self._entry_editor.current_entry
    
    def apply_changes(self) -> bool:
        """エントリの変更を適用する
        
        Returns:
            適用が成功したかどうか
        """
        entry = self._entry_editor.current_entry
        if not entry:
            logger.debug("エントリが選択されていないため、適用できません")
            return False
            
        current_po = self._get_current_po()
        if not current_po:
            logger.debug("POファイルがロードされていないため、適用できません")
            return False
            
        try:
            # エントリの更新を実行
            result = current_po.update_entry(entry)
            
            if result:
                # 成功メッセージとシグナル発行
                self._show_status(f"エントリ {entry.position} を更新しました", 3000)
                self.entry_applied.emit(entry.position)
                return True
            else:
                self._show_status("エントリの更新に失敗しました", 3000)
                return False
                
        except Exception as e:
            logger.error(f"エントリを適用する際にエラーが発生しました: {e}")
            self._show_status(f"エラー: {e}", 3000)
            return False
    
    def _on_text_changed(self) -> None:
        """エントリのテキスト変更時の処理"""
        self._show_status(
            "変更が保留中です。適用するには [適用] ボタンをクリックしてください。", 0
        )
        self.entry_changed.emit()
