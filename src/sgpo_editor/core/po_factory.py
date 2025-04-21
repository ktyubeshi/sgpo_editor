"""POファイルファクトリを提供するモジュール

このモジュールは、設定に基づいてsgpoまたはpolibのファクトリを返す関数を提供します。
"""

import logging
from enum import Enum
from typing import Dict, Optional

from sgpo_editor.core.po_interface import POFileFactory
from sgpo_editor.core.polib_adapter import PolibFactory
from sgpo_editor.core.sgpo_adapter import SgpoFactory

logger = logging.getLogger(__name__)


class POLibraryType(str, Enum):
    """POライブラリの種類"""

    POLIB = "polib"
    SGPO = "sgpo"


# デフォルトのPOライブラリ
DEFAULT_PO_LIBRARY = POLibraryType.SGPO

# 現在使用中のPOライブラリ
_current_po_library = None

# ファクトリのインスタンス
_factory_instances: Dict[POLibraryType, Optional[POFileFactory]] = {
    POLibraryType.POLIB: None,
    POLibraryType.SGPO: None,
}


def get_po_factory(library_type: Optional[POLibraryType] = None) -> POFileFactory:
    """POファイルファクトリを取得する

    Args:
        library_type: POライブラリの種類。Noneの場合は現在のライブラリを使用

    Returns:
        POFileFactory: POファイルファクトリ
    """
    global _current_po_library

    # ライブラリタイプが指定されていない場合は現在のライブラリを使用
    if library_type is None:
        # 現在のライブラリが設定されていない場合は設定ファイルから取得
        if _current_po_library is None:
            _current_po_library = _get_default_library_from_config()
        library_type = _current_po_library
    else:
        # 現在のライブラリを更新
        _current_po_library = library_type

    # ファクトリのインスタンスがない場合は作成
    if _factory_instances[library_type] is None:
        if library_type == POLibraryType.POLIB:
            _factory_instances[library_type] = PolibFactory()
        elif library_type == POLibraryType.SGPO:
            _factory_instances[library_type] = SgpoFactory()
        else:
            raise ValueError(f"不明なPOライブラリタイプ: {library_type}")

        logger.info(f"POファイルファクトリを作成しました: {library_type}")

    factory = _factory_instances[library_type]
    if factory is None:
        raise RuntimeError(f"POファイルファクトリの作成に失敗しました: {library_type}")

    return factory


def _get_default_library_from_config() -> POLibraryType:
    """設定ファイルからデフォルトのPOライブラリを取得する

    Returns:
        POLibraryType: デフォルトのPOライブラリ
    """
    try:
        from sgpo_editor.config import get_config

        # 設定ファイルからPOライブラリを取得
        po_library = get_config().get("po_library", DEFAULT_PO_LIBRARY)

        # 文字列をPOLibraryType列挙型に変換
        if po_library == POLibraryType.POLIB:
            return POLibraryType.POLIB
        elif po_library == POLibraryType.SGPO:
            return POLibraryType.SGPO
        else:
            logger.warning(
                f"不明なPOライブラリタイプ: {po_library}、デフォルトを使用します"
            )
            return DEFAULT_PO_LIBRARY
    except Exception as e:
        logger.warning(
            f"設定ファイルからPOライブラリを取得できませんでした: {e}、デフォルトを使用します"
        )
        return DEFAULT_PO_LIBRARY


def set_po_library(library_type: POLibraryType) -> None:
    """使用するPOライブラリを設定する

    Args:
        library_type: POライブラリの種類
    """
    global _current_po_library

    if library_type not in POLibraryType:
        raise ValueError(f"不明なPOライブラリタイプ: {library_type}")

    _current_po_library = library_type

    # 設定ファイルに保存
    try:
        from sgpo_editor.config import get_config

        get_config().set("po_library", library_type)
        logger.info(f"POライブラリを設定しました: {library_type}")
    except Exception as e:
        logger.warning(f"設定ファイルにPOライブラリを保存できませんでした: {e}")


def get_current_po_library() -> POLibraryType:
    """現在使用中のPOライブラリを取得する

    Returns:
        POLibraryType: 現在使用中のPOライブラリ
    """
    global _current_po_library

    if _current_po_library is None:
        _current_po_library = _get_default_library_from_config()

    return _current_po_library
