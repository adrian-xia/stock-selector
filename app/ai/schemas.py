"""AI 分析数据模型。

定义 AI 响应的 Pydantic 校验模型。
"""

from typing import Literal

from pydantic import BaseModel, Field


class AIAnalysisItem(BaseModel):
    """单只股票的 AI 分析结果。"""

    ts_code: str
    score: int = Field(ge=0, le=100, description="AI 置信度评分 0-100")
    signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    reasoning: str = Field(description="分析理由（中文）")


class AIAnalysisResponse(BaseModel):
    """Gemini 返回的完整分析响应。"""

    analysis: list[AIAnalysisItem]
