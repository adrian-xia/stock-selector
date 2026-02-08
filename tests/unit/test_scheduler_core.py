"""测试调度器核心配置。"""

from app.scheduler.core import create_scheduler


class TestCreateScheduler:
    """测试 create_scheduler() 配置正确性。"""

    def test_timezone(self) -> None:
        """时区应为 Asia/Shanghai。"""
        scheduler = create_scheduler()
        assert str(scheduler.timezone) == "Asia/Shanghai"

    def test_coalesce_default(self) -> None:
        """默认 coalesce 应为 True。"""
        scheduler = create_scheduler()
        assert scheduler._job_defaults["coalesce"] is True

    def test_max_instances_default(self) -> None:
        """默认 max_instances 应为 1。"""
        scheduler = create_scheduler()
        assert scheduler._job_defaults["max_instances"] == 1

    def test_misfire_grace_time(self) -> None:
        """默认 misfire_grace_time 应为 300 秒。"""
        scheduler = create_scheduler()
        assert scheduler._job_defaults["misfire_grace_time"] == 300

    def test_not_running_initially(self) -> None:
        """创建后调度器不应自动启动。"""
        scheduler = create_scheduler()
        assert not scheduler.running
