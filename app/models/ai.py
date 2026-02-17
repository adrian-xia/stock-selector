"""AI 分析结果数据模型。"""

from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON

from app.models.base import Base


class AIAnalysisResult(Base):
    """AI 分析结果表。

    存储盘后链路 AI 分析的评分、信号和摘要，支持按日期查询历史结果。
    主键为 (ts_code, trade_date)，每日 UPSERT 覆盖写入。
    """

    __tablename__ = "ai_analysis_results"

    ts_code = Column(String(20), nullable=False, comment="股票代码")
    trade_date = Column(Date, nullable=False, comment="分析日期")
    ai_score = Column(Integer, nullable=False, comment="AI 评分 1-100")
    ai_signal = Column(String(20), nullable=False, comment="信号：STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL")
    ai_summary = Column(Text, nullable=False, comment="分析摘要")
    prompt_version = Column(String(20), nullable=False, default="v1", comment="Prompt 模板版本")
    token_usage = Column(JSON, nullable=True, comment="Token 用量 {prompt_tokens, completion_tokens, total_tokens}")
    created_at = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")

    __table_args__ = (
        PrimaryKeyConstraint("ts_code", "trade_date"),
        {"comment": "AI 分析结果"},
    )
