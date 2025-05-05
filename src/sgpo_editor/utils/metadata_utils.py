"""メタデータ処理ユーティリティ

POファイルのコメントとしてメタデータを保存・読み込みするためのユーティリティ関数
"""

import json
import logging
import re
from typing import Dict, Optional, Union, List, TypedDict

logger = logging.getLogger(__name__)

# メタデータ識別用のプレフィックス
METADATA_PREFIX = "#. metadata: "


class MetadataDict(TypedDict, total=False):
    """メタデータの型定義"""

    author: str
    date: str
    version: str
    status: str
    priority: int
    category: str
    tags: List[str]
    score: float
    comments: List[Dict[str, str]]
    custom: Dict[str, Union[str, int, float, bool, List[str]]]


def extract_metadata_from_comment(comment: str) -> Optional[MetadataDict]:
    """コメントからメタデータを抽出する

    Args:
        comment: POエントリのコメント

    Returns:
        抽出されたメタデータ辞書またはNone
    """
    if not comment:
        return None

    # メタデータ行を探す
    metadata_match = re.search(rf"{METADATA_PREFIX}(.*?)$", comment, re.MULTILINE)
    if not metadata_match:
        return None

    # メタデータ部分を抽出
    metadata_json = metadata_match.group(1).strip()
    try:
        return json.loads(metadata_json)
    except json.JSONDecodeError as e:
        logger.warning(f"メタデータのJSON解析に失敗しました: {e}")
        return None


def create_comment_with_metadata(
    original_comment: Optional[str], metadata: MetadataDict
) -> str:
    """メタデータを含むコメントを作成する

    Args:
        original_comment: 元のコメント（メタデータ行以外）
        metadata: 保存するメタデータ辞書

    Returns:
        メタデータを含む新しいコメント
    """
    if not metadata:
        return original_comment or ""

    # 元のコメントからメタデータ行を削除
    cleaned_comment = ""
    if original_comment:
        cleaned_comment = re.sub(
            rf"{METADATA_PREFIX}.*?$", "", original_comment, flags=re.MULTILINE
        ).strip()

    # メタデータをJSON形式に変換
    try:
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        metadata_line = f"{METADATA_PREFIX}{metadata_json}"

        # コメントとメタデータを結合
        if cleaned_comment:
            return f"{cleaned_comment}\n{metadata_line}"
        else:
            return metadata_line
    except Exception as e:
        logger.error(f"メタデータのJSON変換に失敗しました: {e}")
        return original_comment or ""
