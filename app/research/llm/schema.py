"""LLM 结构化输出 Pydantic Schema。

定义 LLM 返回的宏观信号结构化数据格式。
"""

from pydantic import BaseModel, Field


class SectorImpact(BaseModel):
    """行业影响条目。"""

    sector_name: str = Field(..., description="行业名称（原始 LLM 输出，需后续对齐）")
    reason: str = Field(..., description="影响原因", max_length=200)
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="置信度 0~1"
    )


class KeyDriver(BaseModel):
    """关键驱动因素。"""

    event: str = Field(..., description="事件描述", max_length=200)
    impact: str = Field(..., description="影响方向", pattern="^(positive|negative|neutral)$")
    magnitude: str = Field(
        ..., description="影响程度", pattern="^(high|medium|low)$"
    )


class MacroSignalOutput(BaseModel):
    """LLM 宏观信号结构化输出。

    与 macro_signal_daily 表对应，经 Pydantic 验证后写入。
    """

    risk_appetite: str = Field(
        ..., description="市场风险偏好", pattern="^(high|mid|low)$"
    )
    global_risk_score: float = Field(
        ..., ge=0.0, le=100.0, description="全球风险评分 0~100"
    )
    positive_sectors: list[SectorImpact] = Field(
        default_factory=list, description="利好行业列表"
    )
    negative_sectors: list[SectorImpact] = Field(
        default_factory=list, description="利空行业列表"
    )
    macro_summary: str = Field(
        ..., description="宏观摘要（1~3 句话）", max_length=500
    )
    key_drivers: list[KeyDriver] = Field(
        default_factory=list, description="关键驱动因素"
    )
