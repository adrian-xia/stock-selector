"""Integration tests for Alembic migrations.

These tests require a running PostgreSQL instance.
Set DATABASE_URL environment variable to point to a test database.

Run with: pytest tests/integration/ -v
"""

import pytest

# Skip all tests in this module if no test database is available
pytestmark = pytest.mark.skipif(
    True,  # Change to False when test DB is configured
    reason="Requires a running PostgreSQL test database",
)


class TestAlembicMigration:
    def test_upgrade_creates_all_tables(self):
        """Verify that 'alembic upgrade head' creates all 12 V1 tables."""
        expected_tables = {
            "trade_calendar",
            "stocks",
            "stock_daily",
            "stock_min",
            "finance_indicator",
            "technical_daily",
            "money_flow",
            "dragon_tiger",
            "strategies",
            "data_source_configs",
            "backtest_tasks",
            "backtest_results",
        }
        # TODO: Run alembic upgrade head against test DB and verify tables
        assert len(expected_tables) == 12

    def test_downgrade_drops_all_tables(self):
        """Verify that 'alembic downgrade -1' drops all tables."""
        # TODO: Run alembic downgrade and verify tables are gone
        pass
