"""トランスレーターモジュール

このモジュールは、アプリケーションの翻訳機能を提供します。
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QCoreApplication, QLocale, QTranslator

logger = logging.getLogger(__name__)

# グローバル翻訳マッピング（英語キーから各言語への翻訳）
_translations: Dict[str, Dict[str, str]] = {
    "ja_JP": {
        # 翻訳ステータス
        "all": "すべて",
        "translated": "翻訳済み",
        "untranslated": "未翻訳",
        "fuzzy": "ファジー",
        "obsolete": "廃止",
        
        # その他のUI要素
        "filter": "表示",
        "keyword": "キーワード",
        "clear": "クリア",
        "keyword_placeholder": "キーワードを入力...",
    }
}

# アクティブなロケール
_current_locale = "ja_JP"

# トランスレーターオブジェクト
_translator: Optional[QTranslator] = None


def setup_translator(locale_name: str = None) -> None:
    """トランスレーターを設定する
    
    Args:
        locale_name: 使用するロケール名（例: "ja_JP"）。Noneの場合はシステム設定を使用。
    """
    global _current_locale, _translator
    
    if locale_name is None:
        # システムロケールを取得
        system_locale = QLocale.system().name()
        # サポートされているロケールかチェック
        if system_locale in _translations:
            _current_locale = system_locale
        else:
            # サポートされていない場合はデフォルトとして日本語を使用
            _current_locale = "ja_JP"
    else:
        _current_locale = locale_name
    
    logger.debug(f"ロケールを設定します: {_current_locale}")
    
    # トランスレーターを設定
    _translator = QTranslator()
    
    # 将来的にQtの翻訳ファイル (.qm) を使用する場合に対応
    translations_dir = Path(__file__).parent / "translations"
    if translations_dir.exists():
        translation_file = f"sgpo_editor_{_current_locale}.qm"
        if _translator.load(str(translations_dir / translation_file)):
            QCoreApplication.installTranslator(_translator)
            logger.debug(f"翻訳ファイルを読み込みました: {translation_file}")
        else:
            logger.warning(f"翻訳ファイルの読み込みに失敗しました: {translation_file}")


def translate(text: str) -> str:
    """テキストを現在のロケールに翻訳する
    
    Args:
        text: 翻訳する英語テキスト
    
    Returns:
        翻訳されたテキスト（翻訳が見つからない場合は元のテキスト）
    """
    # インメモリの翻訳マッピングから取得
    if _current_locale in _translations and text in _translations[_current_locale]:
        return _translations[_current_locale][text]
    
    # Qtの翻訳システムを使用（将来的な拡張用）
    if _translator:
        translation = QCoreApplication.translate("SGPOEditor", text)
        if translation != text:
            return translation
    
    # 翻訳が見つからない場合は元のテキストを返す
    return text 