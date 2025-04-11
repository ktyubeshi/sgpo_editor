"""LLM関連のユーティリティ

このモジュールは、LLMサービスとの連携機能を提供します。
"""

import json
import logging
from enum import Enum, auto
from typing import Dict, List, Optional, Union, TypedDict, cast, TypeAlias

import anthropic
import openai
from pydantic import BaseModel, Field

LLMResponseMetricScores: TypeAlias = Dict[str, float]
LLMResponseComments: TypeAlias = Dict[str, str]

class LLMEvaluationResponse(TypedDict, total=False):
    """LLM評価レスポンスの型定義"""
    overall_score: int
    metric_scores: Dict[str, float]
    comments: Dict[str, str]

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLMプロバイダーの列挙型"""

    OPENAI = auto()
    ANTHROPIC = auto()


class EvaluationMetric(BaseModel):
    """評価指標モデル"""

    name: str
    description: str
    max_score: int = 100


class EvaluationResult(BaseModel):
    """評価結果モデル"""

    overall_score: int = Field(..., ge=0, le=100)
    metric_scores: Dict[str, float] = Field(default_factory=dict)
    comments: Dict[str, str] = Field(default_factory=dict)
    raw_response: str = ""


class LLMEvaluator:
    """LLMを使用した翻訳評価クラス"""

    def __init__(
        self,
        provider: LLMProvider,
        api_key: str,
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ):
        """初期化

        Args:
            provider: LLMプロバイダー
            api_key: APIキー
            model: モデル名（デフォルトはプロバイダーごとに設定）
            temperature: 温度パラメータ
            max_tokens: 最大トークン数
        """
        self.provider = provider
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens

        # プロバイダーごとのデフォルトモデル
        if model is None:
            if provider == LLMProvider.OPENAI:
                self.model = "gpt-4o"
            elif provider == LLMProvider.ANTHROPIC:
                self.model = "claude-3-opus-20240229"
            else:
                raise ValueError(f"不明なプロバイダー: {provider}")
        else:
            self.model = model

        # クライアントの初期化
        if provider == LLMProvider.OPENAI:
            self.client = openai.OpenAI(api_key=api_key)
        elif provider == LLMProvider.ANTHROPIC:
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            raise ValueError(f"不明なプロバイダー: {provider}")

    def evaluate_translation(
        self,
        source_text: str,
        translated_text: str,
        metrics: List[EvaluationMetric],
        language: str,
        context: Optional[str] = None,
    ) -> EvaluationResult:
        """翻訳を評価する

        Args:
            source_text: 原文テキスト
            translated_text: 翻訳テキスト
            metrics: 評価指標のリスト
            language: 翻訳言語
            context: 翻訳コンテキスト（オプション）

        Returns:
            EvaluationResult: 評価結果
        """
        logger.debug("LLMEvaluator.evaluate_translation 開始")
        # プロンプトを構築
        logger.debug("評価プロンプトを構築")
        prompt = self._build_evaluation_prompt(
            source_text, translated_text, metrics, language, context
        )
        logger.debug(f"プロンプト構築完了 (長さ: {len(prompt)}文字)")

        # LLMに送信
        logger.debug(f"LLMプロバイダー: {self.provider}")
        if self.provider == LLMProvider.OPENAI:
            logger.debug("OpenAI APIで評価を実行")
            return self._evaluate_with_openai(prompt, metrics)
        elif self.provider == LLMProvider.ANTHROPIC:
            logger.debug("Anthropic APIで評価を実行")
            return self._evaluate_with_anthropic(prompt, metrics)
        else:
            raise ValueError(f"不明なプロバイダー: {self.provider}")

    def _build_evaluation_prompt(
        self,
        source_text: str,
        translated_text: str,
        metrics: List[EvaluationMetric],
        language: str,
        context: Optional[str] = None,
    ) -> str:
        """評価プロンプトを構築する

        Args:
            source_text: 原文テキスト
            translated_text: 翻訳テキスト
            metrics: 評価指標のリスト
            language: 翻訳言語
            context: 翻訳コンテキスト（オプション）

        Returns:
            str: 構築されたプロンプト
        """
        metrics_text = "\n".join(
            [f"- {m.name}: {m.description} (0-{m.max_score}点)" for m in metrics]
        )

        context_text = f"\n\n翻訳コンテキスト: {context}" if context else ""

        prompt = f"""あなたは翻訳品質の専門評価者です。以下の原文とその{language}翻訳を評価してください。

原文:
{source_text}

{language}翻訳:
{translated_text}{context_text}

以下の評価指標に基づいて、翻訳の品質を0-100点で評価してください:
{metrics_text}

また、各評価指標について、具体的なコメントを日本語で提供してください。

回答は以下のJSON形式で提供してください:
```json
{{
  "overall_score": 総合評価点（0-100）,
  "metric_scores": {{
    "指標名1": 点数,
    "指標名2": 点数,
    ...
  }},
  "comments": {{
    "指標名1": "コメント",
    "指標名2": "コメント",
    ...
  }}
}}
```

評価は厳格かつ公平に行い、具体的な根拠に基づいてください。
"""
        return prompt

    def _evaluate_with_openai(
        self, prompt: str, metrics: List[EvaluationMetric]
    ) -> EvaluationResult:
        """OpenAI APIを使用して評価する

        Args:
            prompt: プロンプト
            metrics: 評価指標のリスト

        Returns:
            EvaluationResult: 評価結果
        """
        try:
            logger.debug(
                f"OpenAI API呼び出し開始: モデル={self.model}, max_tokens={self.max_tokens}"
            )
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
            )
            logger.debug("OpenAI API呼び出し完了")

            # レスポンスからJSONを抽出
            content = response.choices[0].message.content
            logger.debug(f"レスポンス取得 (長さ: {len(content)}文字)")

            try:
                result_json = cast(LLMEvaluationResponse, json.loads(content))
                logger.debug("JSONパース成功")
            except json.JSONDecodeError as e:
                logger.error(f"JSONパースエラー: {e}, コンテンツ: {content[:100]}...")
                raise

            # 評価結果を構築
            logger.debug(
                f"評価結果構築: overall_score={result_json.get('overall_score', 0)}"
            )
            result = EvaluationResult(
                overall_score=result_json.get("overall_score", 0),
                metric_scores=result_json.get("metric_scores", {}),
                comments=result_json.get("comments", {}),
                raw_response=content,
            )
            logger.debug("評価結果構築完了")

            return result

        except Exception as e:
            logger.error(f"OpenAI APIエラー: {e}", exc_info=True)
            # エラー時は空の結果を返す
            default_metric_scores: LLMResponseMetricScores = {
                m.name: 0.0 for m in metrics
            }
            default_comments: LLMResponseComments = {
                m.name: f"評価エラー: {str(e)}" for m in metrics
            }
            return EvaluationResult(
                overall_score=0,
                metric_scores=default_metric_scores,
                comments=default_comments,
                raw_response=str(e),
            )

    def _evaluate_with_anthropic(
        self, prompt: str, metrics: List[EvaluationMetric]
    ) -> EvaluationResult:
        """Anthropic APIを使用して評価する

        Args:
            prompt: プロンプト
            metrics: 評価指標のリスト

        Returns:
            EvaluationResult: 評価結果
        """
        try:
            logger.debug(
                f"Anthropic API呼び出し開始: モデル={self.model}, max_tokens={self.max_tokens}"
            )
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system="あなたは翻訳品質の専門評価者です。与えられた指示に従って、翻訳の品質を評価してください。回答は必ずJSON形式で提供してください。",
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            logger.debug("Anthropic API呼び出し完了")

            # レスポンスからJSONを抽出
            content = response.content[0].text
            logger.debug(f"レスポンス取得 (長さ: {len(content)}文字)")

            # JSONブロックを抽出
            json_start = content.find("```json")
            json_end = content.rfind("```")

            try:
                if json_start >= 0 and json_end > json_start:
                    logger.debug(f"JSONブロック検出: {json_start}～{json_end}")
                    json_text = content[json_start + 7 : json_end].strip()
                    result_json = cast(LLMEvaluationResponse, json.loads(json_text))
                else:
                    # JSONブロックがない場合は直接パース
                    logger.debug("JSONブロックなし、直接パース試行")
                    result_json = cast(LLMEvaluationResponse, json.loads(content))
                logger.debug("JSONパース成功")
            except json.JSONDecodeError as e:
                logger.error(f"JSONパースエラー: {e}, コンテンツ: {content[:100]}...")
                raise

            # 評価結果を構築
            logger.debug(
                f"評価結果構築: overall_score={result_json.get('overall_score', 0)}"
            )
            result = EvaluationResult(
                overall_score=result_json.get("overall_score", 0),
                metric_scores=result_json.get("metric_scores", {}),
                comments=result_json.get("comments", {}),
                raw_response=content,
            )
            logger.debug("評価結果構築完了")

            return result

        except Exception as e:
            logger.error(f"Anthropic APIエラー: {e}", exc_info=True)
            # エラー時は空の結果を返す
            default_metric_scores: LLMResponseMetricScores = {
                m.name: 0.0 for m in metrics
            }
            default_comments: LLMResponseComments = {
                m.name: f"評価エラー: {str(e)}" for m in metrics
            }
            return EvaluationResult(
                overall_score=0,
                metric_scores=default_metric_scores,
                comments=default_comments,
                raw_response=str(e),
            )


# デフォルトの評価指標
DEFAULT_METRICS = [
    EvaluationMetric(
        name="accuracy",
        description="原文の意味が正確に翻訳されているか",
    ),
    EvaluationMetric(
        name="fluency",
        description="翻訳文が自然で流暢か",
    ),
    EvaluationMetric(
        name="terminology",
        description="専門用語や固有名詞が適切に翻訳されているか",
    ),
    EvaluationMetric(
        name="style",
        description="原文のスタイルやトーンが適切に反映されているか",
    ),
]
