from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FinanceIndicator(Base):
    __tablename__ = "finance_indicator"
    __table_args__ = (
        Index("idx_finance_code_date", "ts_code", "end_date", postgresql_ops={"end_date": "DESC"}),
        Index("idx_finance_end_date", "end_date"),
        Index("idx_finance_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(8), primary_key=True, default="Q")
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Profitability
    eps: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    roe: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    roe_diluted: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    net_margin: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Growth
    revenue_yoy: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    profit_yoy: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Valuation
    pe_ttm: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pb: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    ps_ttm: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    circ_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)

    # Solvency
    current_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    quick_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    debt_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    # Cash flow
    ocf_per_share: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
