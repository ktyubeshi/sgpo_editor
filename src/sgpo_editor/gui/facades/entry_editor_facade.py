"""エントリエディタのファサードモジュール

このモジュールは、エントリ編集に関連する操作をカプセル化するファサードクラスを提供する。
複雑なシグナルフローを単純化し、責務を明確にすることを目的としている。
"""

import logging
from typing import Any, Callable, Optional, Union, Dict

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from sgpo_editor.gui.widgets.entry_editor import EntryEditor
from sgpo_editor.models.entry import EntryModel

logger = logging.getLogger(__name__)


class ReviewDialogFacade(QObject):
    """レビューダイアログに関連する操作をカプセル化するファサードクラス
    
    このクラスは、レビューコメント、品質スコア、チェック結果など、
    レビュー関連のダイアログとデータベース操作の間を抽象化します。
    
    責務:
        1. レビューダイアログとデータベースの間の仲介
        2. レビュー関連のデータアクセスを抽象化
        3. ウィジェットとデータベースの結合度を下げる
    
    パターン適用:
        - ファサードパターン: 複雑なレビューデータアクセスに対するシンプルなインターフェース提供
        - メディエーターパターン: ウィジェットとデータベースの間の仲介
    """
    
    # シグナル定義
    comment_added = Signal()
    comment_removed = Signal()
    score_updated = Signal()
    check_result_added = Signal()
    check_result_removed = Signal()
    
    def __init__(self, database=None) -> None:
        """初期化
        
        Args:
            database: データベースオブジェクト
        """
        super().__init__()
        self._database = database
        self._dialogs: Dict[str, QWidget] = {}
        
    def set_database(self, database) -> None:
        """データベース参照を設定
        
        Args:
            database: データベースオブジェクト
        """
        logger.debug(f"ReviewDialogFacade.set_database: 開始 database={database is not None}")
        self._database = database
        
        # 開いているダイアログがあれば、データベース参照を更新
        for dialog_type, dialog in self._dialogs.items():
            if hasattr(dialog, "widget") and hasattr(dialog.widget, "set_database"):
                logger.debug(f"ReviewDialogFacade.set_database: ダイアログ {dialog_type} のデータベース参照を更新")
                dialog.widget.set_database(self._database)
                
        logger.debug("ReviewDialogFacade.set_database: 完了")
        
    def get_database(self):
        """データベース参照を取得
        
        Returns:
            データベースオブジェクト
        """
        return self._database
        
    def register_dialog(self, dialog_type: str, dialog: QWidget) -> None:
        """ダイアログを登録
        
        Args:
            dialog_type: ダイアログの種類
            dialog: ダイアログウィジェット
        """
        logger.debug(f"ReviewDialogFacade.register_dialog: ダイアログ {dialog_type} を登録")
        self._dialogs[dialog_type] = dialog
        
        # ダイアログにデータベース参照を設定
        if hasattr(dialog, "widget") and hasattr(dialog.widget, "set_database") and self._database:
            logger.debug(f"ReviewDialogFacade.register_dialog: ダイアログ {dialog_type} にデータベース参照を設定")
            dialog.widget.set_database(self._database)
            
        # シグナル接続
        self._connect_signals(dialog_type, dialog)
        
    def _connect_signals(self, dialog_type: str, dialog: QWidget) -> None:
        """ダイアログのシグナルを接続
        
        Args:
            dialog_type: ダイアログの種類
            dialog: ダイアログウィジェット
        """
        if not hasattr(dialog, "widget"):
            return
            
        widget = dialog.widget
        
        # レビューコメントウィジェット
        if dialog_type == "review_comment":
            if hasattr(widget, "comment_added"):
                widget.comment_added.connect(self.comment_added)
            if hasattr(widget, "comment_removed"):
                widget.comment_removed.connect(self.comment_removed)
                
        # 品質スコアウィジェット
        elif dialog_type == "quality_score":
            if hasattr(widget, "score_updated"):
                widget.score_updated.connect(self.score_updated)
                
        # チェック結果ウィジェット
        elif dialog_type == "check_result":
            if hasattr(widget, "result_added"):
                widget.result_added.connect(self.check_result_added)
            if hasattr(widget, "result_removed"):
                widget.result_removed.connect(self.check_result_removed)
        
    def update_entry_field(self, entry: EntryModel, field_name: str, value: Any) -> bool:
        """エントリのフィールドを更新
        
        Args:
            entry: 更新対象のエントリ
            field_name: 更新するフィールド名
            value: 新しい値
            
        Returns:
            更新が成功したかどうか
        """
        if not self._database or not entry:
            logger.debug(f"ReviewDialogFacade.update_entry_field: データベースまたはエントリがない")
            return False
            
        try:
            logger.debug(f"ReviewDialogFacade.update_entry_field: フィールド {field_name} を更新")
            self._database.update_entry_field(entry.key, field_name, value)
            return True
        except Exception as e:
            logger.error(f"ReviewDialogFacade.update_entry_field: エラー発生 {e}", exc_info=True)
            return False


class EntryEditorFacade(QObject):
    """エントリ編集に関連する操作をカプセル化するファサードクラス
    
    このクラスは、エントリの編集、適用、取得などの操作に関するシンプルなインターフェイスを提供します。
    内部的には EntryEditor と連携して動作します。
    
    責務:
        1. エントリエディタコンポーネントへの操作のカプセル化
        2. エントリ更新ロジックの一元管理
        3. エントリ変更の検知と通知
        4. ステータスメッセージの管理
    
    パターン適用:
        - ファサードパターン: 複雑なサブシステム（エントリ編集機能）に対する
          シンプルなインターフェースを提供
        - メディエーターパターン: エントリエディタとPOファイル操作の仲介役として機能
    
    EventHandlerとの関係:
        - EventHandlerがフォーカスするUI操作のイベント処理に対し、
          このクラスはエントリ編集ロジックの抽象化に特化
        - 最終的にはEventHandlerの一部機能をこのクラスに移行することも検討
    
    改善可能点:
        - エディタの状態管理(dirty状態など)をより明示的に扱う
        - エントリ適用時の並行処理やバッチ更新のサポート
        - エディタUIコンポーネントのカスタマイズをサポートするインターフェースの提供
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
        self._review_dialog_facade = ReviewDialogFacade()
        
        # エントリエディタのシグナルを接続
        self._entry_editor.text_changed.connect(self._on_text_changed)
        self._entry_editor.apply_clicked.connect(self.apply_changes)
        
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
        
    def show_review_dialog(self, dialog_type: str) -> None:
        """レビュー関連ダイアログを表示
        
        Args:
            dialog_type: ダイアログの種類
                "translator_comment": 翻訳者コメント
                "review_comment": レビューコメント
                "quality_score": 品質スコア
                "check_result": チェック結果
                "debug": デバッグ情報
        """
        logger.debug(f"EntryEditorFacade.show_review_dialog: 開始 dialog_type={dialog_type}")
        
        # エントリエディタのメソッドを使用してダイアログを表示
        dialog = self._entry_editor._show_review_dialog(dialog_type)
        
        # ダイアログをReviewDialogFacadeに登録
        if dialog:
            self._review_dialog_facade.register_dialog(dialog_type, dialog)
        
        logger.debug(f"EntryEditorFacade.show_review_dialog: 完了")
        
    def set_database(self, db) -> None:
        """データベース参照を設定
        
        Args:
            db: データベースオブジェクト
        """
        logger.debug(f"EntryEditorFacade.set_database: 開始 db={db is not None}")
        
        # エディタのデータベース参照を更新
        self._entry_editor.database = db
        
        # ReviewDialogFacadeにもデータベース参照を設定
        self._review_dialog_facade.set_database(db)
        
        logger.debug(f"EntryEditorFacade.set_database: 完了")
        
    def get_database(self):
        """データベース参照を取得
        
        Returns:
            データベースオブジェクト
        """
        return self._entry_editor.database
        
    @property
    def review_dialog_facade(self) -> ReviewDialogFacade:
        """レビューダイアログファサードを取得
        
        Returns:
            ReviewDialogFacadeインスタンス
        """
        return self._review_dialog_facade
