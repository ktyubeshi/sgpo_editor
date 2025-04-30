"""フィルタリング用ウィジェット"""

from typing import Dict, Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)
from pydantic import BaseModel, ConfigDict

from sgpo_editor.core.constants import TranslationStatus, TRANSLATION_STATUS_ORDER
from sgpo_editor.i18n import translate


class SearchCriteria(BaseModel):
    model_config = ConfigDict()

    filter: str = TranslationStatus.ALL
    filter_keyword: Optional[str] = ""
    match_mode: str = "partial"  # 部分一致を'partial'に変更


class SearchWidget(QWidget):
    """フィルタリング用ウィジェット"""

    # シグナル定義
    filter_changed = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        # 内部状態
        self._display_to_status: Dict[str, str] = {}
        self._status_to_display: Dict[str, str] = {}

        # フィルタ用タイマー
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(100)  # 100ミリ秒のデバウンス時間
        self._filter_timer.timeout.connect(self.filter_changed.emit)

        # キーワードフィルタ用タイマー
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(100)  # 100ミリ秒のデバウンス時間
        self._search_timer.timeout.connect(self.filter_changed.emit)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UIの初期化"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # フィルタリング用のラベルとコンボボックス
        filter_label = QLabel(translate("filter") + ":")
        layout.addWidget(filter_label)

        self.filter_combo = QComboBox()

        # ステータスの表示名と内部値のマッピングを作成
        # 表示名と内部状態のマッピングを初期化
        self._init_status_mapping()

        # コンボボックスに翻訳されたステータス名を追加
        display_items = [
            self._status_to_display[status] for status in TRANSLATION_STATUS_ORDER
        ]
        self.filter_combo.addItems(display_items)

        # シグナル接続
        self.filter_combo.currentTextChanged.connect(self._start_filter_timer)
        layout.addWidget(self.filter_combo)

        # キーワード検索用のラベルとテキストボックス
        keyword_label = QLabel(translate("keyword") + ":")
        layout.addWidget(keyword_label)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(translate("keyword_placeholder"))
        self.search_edit.textChanged.connect(self._start_search_timer)
        layout.addWidget(self.search_edit)

        # クリアボタン
        clear_button = QPushButton(translate("clear"))
        clear_button.clicked.connect(self._clear_filter)
        layout.addWidget(clear_button)

    def _init_status_mapping(self) -> None:
        """ステータスの表示名と内部値のマッピングを初期化"""
        self._status_to_display = {}
        self._display_to_status = {}

        # 各ステータスの翻訳を取得して、双方向マッピングを作成
        for status in TRANSLATION_STATUS_ORDER:
            display_name = translate(status)
            self._status_to_display[status] = display_name
            self._display_to_status[display_name] = status

    def get_match_mode(self) -> str:
        """現在のマッチモードを取得（"partial"固定）"""
        return "partial"

    def get_search_criteria(self) -> SearchCriteria:
        """現在のフィルタ条件をSearchCriteriaの形で返す"""
        # 表示テキストから内部ステータス値に変換
        display_filter = self.filter_combo.currentText()
        internal_filter = self._display_to_status.get(
            display_filter, TranslationStatus.ALL
        )

        return SearchCriteria(
            filter=internal_filter,
            filter_keyword=self.search_edit.text(),
            match_mode=self.get_match_mode(),
        )

    def _start_filter_timer(self) -> None:
        """フィルタタイマーを開始"""
        self._filter_timer.start()

    def _start_search_timer(self) -> None:
        """キーワードフィルタタイマーを開始"""
        self._search_timer.start()

    def _clear_filter(self) -> None:
        """フィルタ条件をクリア"""
        self.search_edit.clear()
        # 「すべて」に対応する内部値を取得
        all_display = self._status_to_display[TranslationStatus.ALL]
        self.filter_combo.setCurrentText(all_display)

        # フィルタ変更シグナルを発行
        self.filter_changed.emit()

    def get_filter(self) -> str:
        """現在のフィルタ（内部値）を取得"""
        display_filter = self.filter_combo.currentText()
        return self._display_to_status.get(display_filter, TranslationStatus.ALL)

    def get_filter_keyword(self) -> str:
        """現在のフィルターキーワードを取得"""
        return self.search_edit.text()

    def set_filter(self, filter_value: str) -> None:
        """フィルタを設定（内部値から表示名に変換）"""
        if filter_value in self._status_to_display:
            display_name = self._status_to_display[filter_value]
            self.filter_combo.setCurrentText(display_name)
        else:
            # 未知のフィルタ値の場合はデフォルトに設定
            default_display = self._status_to_display[TranslationStatus.ALL]
            self.filter_combo.setCurrentText(default_display)
