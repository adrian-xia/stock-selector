"""测试 P5 补充数据 28 个 sync_raw_* 方法和 sync_p5_core 集成逻辑。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.manager import DataManager


def _make_manager():
    """创建测试用 DataManager，mock session 和 client。"""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    sf = MagicMock(return_value=session)
    client = AsyncMock()
    mgr = DataManager(
        session_factory=sf,
        clients={"tushare": client},
        primary="tushare",
    )
    # mock _upsert_raw 返回写入行数
    mgr._upsert_raw = AsyncMock(return_value=5)
    return mgr, client


class TestBasicSupplementarySync:
    """测试基础补充表同步（5 张）。"""

    @pytest.mark.asyncio
    async def test_sync_raw_namechange(self):
        mgr, client = _make_manager()
        client.fetch_raw_namechange.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_namechange()
        assert result["namechange"] == 5
        client.fetch_raw_namechange.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_raw_stk_managers(self):
        mgr, client = _make_manager()
        client.fetch_raw_stk_managers.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_stk_managers()
        assert result["stk_managers"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_stk_rewards(self):
        mgr, client = _make_manager()
        client.fetch_raw_stk_rewards.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_stk_rewards()
        assert result["stk_rewards"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_new_share(self):
        mgr, client = _make_manager()
        client.fetch_raw_new_share.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_new_share()
        assert result["new_share"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_stk_list_his(self):
        mgr, client = _make_manager()
        client.fetch_raw_stk_list_his.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_stk_list_his()
        assert result["stk_list_his"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_empty_data(self):
        """空数据时返回 0。"""
        mgr, client = _make_manager()
        client.fetch_raw_namechange.return_value = []
        result = await mgr.sync_raw_namechange()
        assert result["namechange"] == 0
        mgr._upsert_raw.assert_not_called()


class TestQuoteSupplementarySync:
    """测试行情补充表同步（2 张）。"""

    @pytest.mark.asyncio
    async def test_sync_raw_hsgt_top10(self):
        mgr, client = _make_manager()
        client.fetch_raw_hsgt_top10.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_hsgt_top10(date(2026, 2, 19))
        assert result["hsgt_top10"] == 5
        client.fetch_raw_hsgt_top10.assert_called_once_with(trade_date="20260219")

    @pytest.mark.asyncio
    async def test_sync_raw_ggt_daily(self):
        mgr, client = _make_manager()
        client.fetch_raw_ggt_daily.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_ggt_daily(date(2026, 2, 19))
        assert result["ggt_daily"] == 5


class TestMarketReferenceSync:
    """测试市场参考表同步（4 张）。"""

    @pytest.mark.asyncio
    async def test_sync_raw_pledge_stat(self):
        mgr, client = _make_manager()
        client.fetch_raw_pledge_stat.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_pledge_stat()
        assert result["pledge_stat"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_pledge_detail(self):
        mgr, client = _make_manager()
        client.fetch_raw_pledge_detail.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_pledge_detail()
        assert result["pledge_detail"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_repurchase(self):
        mgr, client = _make_manager()
        client.fetch_raw_repurchase.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_repurchase()
        assert result["repurchase"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_share_float(self):
        mgr, client = _make_manager()
        client.fetch_raw_share_float.return_value = [{"ann_date": "20260219"}]
        result = await mgr.sync_raw_share_float(date(2026, 2, 19))
        assert result["share_float"] == 5


class TestSpecialtyDataSync:
    """测试特色数据表同步（7 张）。"""

    @pytest.mark.asyncio
    async def test_sync_raw_report_rc(self):
        mgr, client = _make_manager()
        client.fetch_raw_report_rc.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_report_rc(date(2026, 2, 19))
        assert result["report_rc"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_cyq_perf(self):
        mgr, client = _make_manager()
        client.fetch_raw_cyq_perf.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_cyq_perf(date(2026, 2, 19))
        assert result["cyq_perf"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_cyq_chips(self):
        mgr, client = _make_manager()
        client.fetch_raw_cyq_chips.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_cyq_chips(date(2026, 2, 19))
        assert result["cyq_chips"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_ccass_hold(self):
        mgr, client = _make_manager()
        client.fetch_raw_ccass_hold.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_ccass_hold(date(2026, 2, 19))
        assert result["ccass_hold"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_ccass_hold_detail(self):
        mgr, client = _make_manager()
        client.fetch_raw_ccass_hold_detail.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_ccass_hold_detail(date(2026, 2, 19))
        assert result["ccass_hold_detail"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_hk_hold(self):
        mgr, client = _make_manager()
        client.fetch_raw_hk_hold.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_hk_hold(date(2026, 2, 19))
        assert result["hk_hold"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_stk_surv(self):
        mgr, client = _make_manager()
        client.fetch_raw_stk_surv.return_value = [{"ts_code": "000001.SZ"}]
        result = await mgr.sync_raw_stk_surv()
        assert result["stk_surv"] == 5

class TestMarginSupplementarySync:
    """测试两融补充表同步（1 张）。"""

    @pytest.mark.asyncio
    async def test_sync_raw_slb_len(self):
        mgr, client = _make_manager()
        client.fetch_raw_slb_len.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_slb_len(date(2026, 2, 19))
        assert result["slb_len"] == 5


class TestBoardHittingSync:
    """测试打板专题表同步（9 张）。"""

    @pytest.mark.asyncio
    async def test_sync_raw_limit_step(self):
        mgr, client = _make_manager()
        client.fetch_raw_limit_step.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_limit_step(date(2026, 2, 19))
        assert result["limit_step"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_hm_detail(self):
        mgr, client = _make_manager()
        client.fetch_raw_hm_detail.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_hm_detail(date(2026, 2, 19))
        assert result["hm_detail"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_stk_auction(self):
        mgr, client = _make_manager()
        client.fetch_raw_stk_auction.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_stk_auction(date(2026, 2, 19))
        assert result["stk_auction"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_stk_auction_o(self):
        mgr, client = _make_manager()
        client.fetch_raw_stk_auction_o.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_stk_auction_o(date(2026, 2, 19))
        assert result["stk_auction_o"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_kpl_list(self):
        mgr, client = _make_manager()
        client.fetch_raw_kpl_list.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_kpl_list(date(2026, 2, 19))
        assert result["kpl_list"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_kpl_concept(self):
        mgr, client = _make_manager()
        client.fetch_raw_kpl_concept.return_value = [{"trade_date": "20260219"}]
        result = await mgr.sync_raw_kpl_concept(date(2026, 2, 19))
        assert result["kpl_concept"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_broker_recommend(self):
        mgr, client = _make_manager()
        client.fetch_raw_broker_recommend.return_value = [{"date": "20260219"}]
        result = await mgr.sync_raw_broker_recommend(date(2026, 2, 19))
        assert result["broker_recommend"] == 5

    @pytest.mark.asyncio
    async def test_sync_raw_ggt_monthly(self):
        mgr, client = _make_manager()
        client.fetch_raw_ggt_monthly.return_value = [{"month": "202602"}]
        result = await mgr.sync_raw_ggt_monthly(date(2026, 2, 19))
        assert result["ggt_monthly"] == 5
        client.fetch_raw_ggt_monthly.assert_called_once_with(month="202602")


class TestSyncP5CoreIntegration:
    """测试 sync_p5_core 集成逻辑。"""

    @pytest.mark.asyncio
    async def test_daily_ext_methods_called(self):
        """普通交易日应调用日频补充表方法。"""
        mgr, client = _make_manager()
        # mock 所有 sync_raw_* 方法
        for attr in dir(mgr):
            if attr.startswith("sync_raw_") or attr.startswith("etl_"):
                setattr(mgr, attr, AsyncMock(return_value={}))

        td = date(2026, 2, 18)  # 周三，非月末非季初
        result = await mgr.sync_p5_core(td)

        # 验证日频补充表被调用
        mgr.sync_raw_hsgt_top10.assert_called_once_with(td)
        mgr.sync_raw_ggt_daily.assert_called_once_with(td)
        mgr.sync_raw_ccass_hold.assert_called_once_with(td)
        mgr.sync_raw_cyq_perf.assert_called_once_with(td)
        mgr.sync_raw_slb_len.assert_called_once_with(td)
        mgr.sync_raw_limit_step.assert_called_once_with(td)
        mgr.sync_raw_broker_recommend.assert_called_once_with(td)

    @pytest.mark.asyncio
    async def test_monthly_ggt_monthly_called(self):
        """月末应调用 ggt_monthly。"""
        mgr, client = _make_manager()
        for attr in dir(mgr):
            if attr.startswith("sync_raw_") or attr.startswith("etl_"):
                setattr(mgr, attr, AsyncMock(return_value={}))

        td = date(2026, 2, 28)  # 2 月最后一天
        result = await mgr.sync_p5_core(td)
        mgr.sync_raw_ggt_monthly.assert_called_once_with(td)

    @pytest.mark.asyncio
    async def test_quarterly_static_methods_called(self):
        """季度首个交易日应调用静态补充表方法。"""
        mgr, client = _make_manager()
        for attr in dir(mgr):
            if attr.startswith("sync_raw_") or attr.startswith("etl_"):
                setattr(mgr, attr, AsyncMock(return_value={}))

        td = date(2026, 1, 2)  # 1 月 2 日，季度首
        result = await mgr.sync_p5_core(td)

        mgr.sync_raw_namechange.assert_called_once()
        mgr.sync_raw_stk_managers.assert_called_once()
        mgr.sync_raw_stk_rewards.assert_called_once()
        mgr.sync_raw_new_share.assert_called_once()
        mgr.sync_raw_stk_list_his.assert_called_once()
        mgr.sync_raw_pledge_stat.assert_called_once()
        mgr.sync_raw_pledge_detail.assert_called_once()
        mgr.sync_raw_repurchase.assert_called_once()
        mgr.sync_raw_stk_surv.assert_called_once()
        mgr.sync_raw_share_float.assert_called_once_with(td)
        mgr.sync_raw_report_rc.assert_called_once_with(td)

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """单个方法失败不影响其他方法执行。"""
        mgr, client = _make_manager()
        for attr in dir(mgr):
            if attr.startswith("sync_raw_") or attr.startswith("etl_"):
                setattr(mgr, attr, AsyncMock(return_value={}))

        # 让 hsgt_top10 抛异常
        mgr.sync_raw_hsgt_top10 = AsyncMock(side_effect=Exception("API error"))

        td = date(2026, 2, 18)
        result = await mgr.sync_p5_core(td)

        # hsgt_top10 标记为 error
        assert result["hsgt_top10"] == {"error": True}
        # 其他方法仍然被调用
        mgr.sync_raw_ggt_daily.assert_called_once_with(td)
        mgr.sync_raw_slb_len.assert_called_once_with(td)

    @pytest.mark.asyncio
    async def test_non_quarterly_skips_static(self):
        """非季度首日不调用静态方法。"""
        mgr, client = _make_manager()
        for attr in dir(mgr):
            if attr.startswith("sync_raw_") or attr.startswith("etl_"):
                setattr(mgr, attr, AsyncMock(return_value={}))

        td = date(2026, 2, 18)  # 非季度首
        result = await mgr.sync_p5_core(td)

        mgr.sync_raw_namechange.assert_not_called()
        mgr.sync_raw_stk_managers.assert_not_called()

