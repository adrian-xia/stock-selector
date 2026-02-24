"""重写 idx_factor_pro raw 表字段 + 扩展 index_technical_daily 业务表

Raw 表：删除旧字段，新增 idx_factor_pro API 的 80+ 字段。
业务表：新增 DMI/MTM/ROC/PSY/TRIX/EMV/VR/BRAR/CR/MFI 等指标，删除 donchian。

Revision ID: a1b2c3d4e5f6
Revises: f3a4b5c6d7e8
Create Date: 2026-02-24
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f3a4b5c6d7e8"

# raw 表旧字段（需删除）
RAW_OLD_COLUMNS = [
    "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
    "macd_dif", "macd_dea", "macd",
    "kdj_k", "kdj_d", "kdj_j",
    "rsi6", "rsi12", "rsi24",
    "boll_upper", "boll_mid", "boll_lower",
    "atr", "cci", "wr",
]

# raw 表新字段（全部 Numeric(20,4)）
RAW_NEW_COLUMNS = [
    # OHLCV
    "open", "high", "low", "close", "pre_close", "change", "pct_change", "vol", "amount",
    # ASI
    "asi_bfq", "asit_bfq",
    # ATR
    "atr_bfq",
    # BBI
    "bbi_bfq",
    # BIAS
    "bias1_bfq", "bias2_bfq", "bias3_bfq",
    # BOLL
    "boll_lower_bfq", "boll_mid_bfq", "boll_upper_bfq",
    # BRAR
    "brar_ar_bfq", "brar_br_bfq",
    # CCI
    "cci_bfq",
    # CR
    "cr_bfq",
    # DFMA
    "dfma_dif_bfq", "dfma_difma_bfq",
    # DMI
    "dmi_adx_bfq", "dmi_adxr_bfq", "dmi_mdi_bfq", "dmi_pdi_bfq",
    # Days
    "downdays", "updays", "lowdays", "topdays",
    # DPO
    "dpo_bfq", "madpo_bfq",
    # EMA
    "ema_bfq_5", "ema_bfq_10", "ema_bfq_20", "ema_bfq_30", "ema_bfq_60", "ema_bfq_90", "ema_bfq_250",
    # EMV
    "emv_bfq", "maemv_bfq",
    # EXPMA
    "expma_12_bfq", "expma_50_bfq",
    # KDJ
    "kdj_bfq", "kdj_d_bfq", "kdj_k_bfq",
    # KTN
    "ktn_down_bfq", "ktn_mid_bfq", "ktn_upper_bfq",
    # MA
    "ma_bfq_5", "ma_bfq_10", "ma_bfq_20", "ma_bfq_30", "ma_bfq_60", "ma_bfq_90", "ma_bfq_250",
    # MACD
    "macd_bfq", "macd_dea_bfq", "macd_dif_bfq",
    # MASS
    "mass_bfq", "ma_mass_bfq",
    # MFI
    "mfi_bfq",
    # MTM
    "mtm_bfq", "mtmma_bfq",
    # OBV
    "obv_bfq",
    # PSY
    "psy_bfq", "psyma_bfq",
    # ROC
    "roc_bfq", "maroc_bfq",
    # RSI
    "rsi_bfq_6", "rsi_bfq_12", "rsi_bfq_24",
    # TAQ
    "taq_down_bfq", "taq_mid_bfq", "taq_up_bfq",
    # TRIX
    "trix_bfq", "trma_bfq",
    # VR
    "vr_bfq",
    # WR
    "wr_bfq", "wr1_bfq",
    # XSII
    "xsii_td1_bfq", "xsii_td2_bfq", "xsii_td3_bfq", "xsii_td4_bfq",
]

# 业务表新增字段（全部 Numeric）
BIZ_NEW_COLUMNS = [
    ("dmi_pdi", "12,4"), ("dmi_mdi", "12,4"), ("dmi_adx", "12,4"), ("dmi_adxr", "12,4"),
    ("mtm", "20,4"), ("mtmma", "20,4"),
    ("roc", "12,4"), ("maroc", "12,4"),
    ("psy", "12,4"), ("psyma", "12,4"),
    ("trix", "12,4"), ("trma", "12,4"),
    ("emv", "20,4"), ("maemv", "20,4"),
    ("vr", "20,4"),
    ("brar_ar", "12,4"), ("brar_br", "12,4"),
    ("cr", "20,4"),
    ("mfi", "12,4"),
    ("dpo", "20,4"), ("madpo", "20,4"),
    ("mass", "20,4"), ("ma_mass", "20,4"),
    ("asi", "20,4"), ("asit", "20,4"),
    ("dfma_dif", "20,4"), ("dfma_difma", "20,4"),
    ("ema5", "20,4"), ("ema10", "20,4"), ("ema20", "20,4"), ("ema30", "20,4"),
    ("ema60", "20,4"), ("ema90", "20,4"), ("ema250", "20,4"),
    ("expma_12", "20,4"), ("expma_50", "20,4"),
    ("ktn_upper", "20,4"), ("ktn_mid", "20,4"), ("ktn_lower", "20,4"),
    ("taq_up", "20,4"), ("taq_mid", "20,4"), ("taq_down", "20,4"),
    ("xsii_td1", "20,4"), ("xsii_td2", "20,4"), ("xsii_td3", "20,4"), ("xsii_td4", "20,4"),
    ("updays", "20,4"), ("downdays", "20,4"), ("topdays", "20,4"), ("lowdays", "20,4"),
    ("bbi", "20,4"),
]

# 业务表删除字段
BIZ_DROP_COLUMNS = ["donchian_upper", "donchian_lower"]


def upgrade() -> None:
    # --- raw_tushare_index_factor_pro: 删除旧字段 ---
    for col in RAW_OLD_COLUMNS:
        op.drop_column("raw_tushare_index_factor_pro", col)

    # --- raw_tushare_index_factor_pro: 新增字段 ---
    for col in RAW_NEW_COLUMNS:
        op.add_column(
            "raw_tushare_index_factor_pro",
            sa.Column(col, sa.Numeric(20, 4), nullable=True),
        )

    # --- index_technical_daily: 新增指标字段 ---
    for col_name, precision in BIZ_NEW_COLUMNS:
        p, s = precision.split(",")
        op.add_column(
            "index_technical_daily",
            sa.Column(col_name, sa.Numeric(int(p), int(s)), nullable=True),
        )

    # --- index_technical_daily: 删除 donchian 字段 ---
    for col in BIZ_DROP_COLUMNS:
        op.drop_column("index_technical_daily", col)


def downgrade() -> None:
    # --- index_technical_daily: 恢复 donchian 字段 ---
    for col in BIZ_DROP_COLUMNS:
        op.add_column(
            "index_technical_daily",
            sa.Column(col, sa.Numeric(12, 4), nullable=True),
        )

    # --- index_technical_daily: 删除新增字段 ---
    for col_name, _ in BIZ_NEW_COLUMNS:
        op.drop_column("index_technical_daily", col_name)

    # --- raw_tushare_index_factor_pro: 删除新字段 ---
    for col in RAW_NEW_COLUMNS:
        op.drop_column("raw_tushare_index_factor_pro", col)

    # --- raw_tushare_index_factor_pro: 恢复旧字段 ---
    for col in RAW_OLD_COLUMNS:
        op.add_column(
            "raw_tushare_index_factor_pro",
            sa.Column(col, sa.Numeric(12, 4), nullable=True),
        )
