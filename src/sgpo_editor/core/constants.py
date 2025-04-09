"""定数定義モジュール

このモジュールは、アプリケーション全体で使用される定数を定義します。
"""


# 翻訳ステータス定数
class TranslationStatus:
    """翻訳ステータスを表す定数クラス"""

    ALL = "all"
    TRANSLATED = "translated"
    UNTRANSLATED = "untranslated"
    FUZZY = "fuzzy"
    OBSOLETE = "obsolete"


# ステータスの表示順序
TRANSLATION_STATUS_ORDER = [
    TranslationStatus.ALL,
    TranslationStatus.TRANSLATED,
    TranslationStatus.UNTRANSLATED,
    TranslationStatus.FUZZY,
]
