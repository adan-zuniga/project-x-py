"""Comprehensive tests for RiskManager financial metrics following TDD methodology.

Tests define the EXPECTED behavior, not current implementation.
If tests fail, we fix the implementation, not the tests.
"""

import statistics
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from project_x_py.models import Account, Position
from project_x_py.risk_manager import RiskConfig, RiskManager
from project_x_py.types import OrderSide


@pytest.fixture
def mock_client():
    """Create a mock ProjectX client."""
    client = MagicMock()
    client.account_info = Account(
        id=12345,
        name="Test Account",
        balance=100000.0,
        canTrade=True,
        isVisible=True,
        simulated=True
    )
    client.list_accounts = AsyncMock(return_value=[client.account_info])
    return client


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus."""
    bus = MagicMock()
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
async def risk_manager(mock_client, mock_event_bus):
    """Create a RiskManager instance for testing."""
    rm = RiskManager(
        project_x=mock_client,
        order_manager=MagicMock(),
        event_bus=mock_event_bus,
        config=RiskConfig()
    )
    return rm


class TestProfitFactor:
    """Test profit factor calculation."""

    @pytest.mark.asyncio
    async def test_calculate_profit_factor_with_wins_and_losses(self, risk_manager):
        """Test profit factor calculation with both winning and losing trades."""
        # Setup trade history
        risk_manager._trade_history = [
            {"pnl": 500.0},   # Win
            {"pnl": 300.0},   # Win
            {"pnl": -200.0},  # Loss
            {"pnl": -100.0},  # Loss
            {"pnl": 400.0},   # Win
        ]

        # Calculate profit factor
        pf = risk_manager._calculate_profit_factor()

        # Expected: Gross profit = 1200, Gross loss = 300, PF = 4.0
        assert pf == 4.0

    @pytest.mark.asyncio
    async def test_calculate_profit_factor_no_losses(self, risk_manager):
        """Test profit factor when there are no losses."""
        # Setup only winning trades
        risk_manager._trade_history = [
            {"pnl": 500.0},
            {"pnl": 300.0},
            {"pnl": 400.0},
        ]

        # Calculate profit factor
        pf = risk_manager._calculate_profit_factor()

        # Should return 0 when no losses (divide by zero protection)
        assert pf == 0.0

    @pytest.mark.asyncio
    async def test_calculate_profit_factor_no_wins(self, risk_manager):
        """Test profit factor when there are no wins."""
        # Setup only losing trades
        risk_manager._trade_history = [
            {"pnl": -200.0},
            {"pnl": -100.0},
            {"pnl": -150.0},
        ]

        # Calculate profit factor
        pf = risk_manager._calculate_profit_factor()

        # Should return 0 when no wins
        assert pf == 0.0

    @pytest.mark.asyncio
    async def test_calculate_profit_factor_empty_history(self, risk_manager):
        """Test profit factor with no trade history."""
        risk_manager._trade_history = []

        # Calculate profit factor
        pf = risk_manager._calculate_profit_factor()

        # Should return 0 with empty history
        assert pf == 0.0


class TestSharpeRatio:
    """Test Sharpe ratio calculation."""

    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio_normal_returns(self, risk_manager):
        """Test Sharpe ratio calculation with normal returns."""
        # Setup consistent returns for predictable calculation
        risk_manager._trade_history = [
            {"pnl": 100.0},
            {"pnl": 150.0},
            {"pnl": 80.0},
            {"pnl": 120.0},
            {"pnl": 90.0},
        ]

        # Calculate Sharpe ratio
        sharpe = risk_manager._calculate_sharpe_ratio()

        # Verify calculation
        returns = [100.0, 150.0, 80.0, 120.0, 90.0]
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        expected_sharpe = (avg_return / std_return) * (252 ** 0.5)

        assert abs(sharpe - expected_sharpe) < 0.01

    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio_zero_volatility(self, risk_manager):
        """Test Sharpe ratio when all returns are identical (zero volatility)."""
        # Setup identical returns
        risk_manager._trade_history = [
            {"pnl": 100.0},
            {"pnl": 100.0},
            {"pnl": 100.0},
        ]

        # Calculate Sharpe ratio
        sharpe = risk_manager._calculate_sharpe_ratio()

        # Should return 0 when standard deviation is 0
        assert sharpe == 0.0

    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio_insufficient_data(self, risk_manager):
        """Test Sharpe ratio with insufficient data."""
        # Less than 2 trades
        risk_manager._trade_history = [{"pnl": 100.0}]

        # Calculate Sharpe ratio
        sharpe = risk_manager._calculate_sharpe_ratio()

        # Should return 0 with insufficient data
        assert sharpe == 0.0

    @pytest.mark.asyncio
    async def test_calculate_sharpe_ratio_negative_returns(self, risk_manager):
        """Test Sharpe ratio with negative average returns."""
        # Setup losing trades
        risk_manager._trade_history = [
            {"pnl": -100.0},
            {"pnl": -150.0},
            {"pnl": -80.0},
            {"pnl": -120.0},
        ]

        # Calculate Sharpe ratio
        sharpe = risk_manager._calculate_sharpe_ratio()

        # Should handle negative returns correctly (will be negative)
        assert sharpe < 0


class TestKellyCriterion:
    """Test Kelly criterion calculations."""

    @pytest.mark.asyncio
    async def test_calculate_kelly_fraction_normal(self, risk_manager):
        """Test Kelly fraction calculation with normal win/loss rates."""
        # Setup win/loss statistics
        risk_manager._win_rate = 0.6  # 60% win rate
        risk_manager._avg_win = Decimal("500")
        risk_manager._avg_loss = Decimal("300")

        # Calculate Kelly fraction
        kelly = risk_manager._calculate_kelly_fraction()

        # Verify calculation
        # Kelly formula: f = (p * b - q) / b
        # where p = 0.6, q = 0.4, b = 500/300 = 1.667
        # f = (0.6 * 1.667 - 0.4) / 1.667 = 0.36
        # Applied fraction of 0.25 = 0.36 * 0.25 = 0.09
        # Capped at 0.25 max

        assert kelly > 0
        assert kelly <= 0.25  # Max cap

    @pytest.mark.asyncio
    async def test_calculate_kelly_fraction_zero_win_rate(self, risk_manager):
        """Test Kelly fraction with zero win rate."""
        risk_manager._win_rate = 0.0
        risk_manager._avg_win = Decimal("500")
        risk_manager._avg_loss = Decimal("300")

        kelly = risk_manager._calculate_kelly_fraction()

        # Should return 0 with zero win rate
        assert kelly == 0.0

    @pytest.mark.asyncio
    async def test_calculate_kelly_fraction_zero_avg_loss(self, risk_manager):
        """Test Kelly fraction with zero average loss."""
        risk_manager._win_rate = 0.6
        risk_manager._avg_win = Decimal("500")
        risk_manager._avg_loss = Decimal("0")

        kelly = risk_manager._calculate_kelly_fraction()

        # Should return 0 when avg_loss is 0
        assert kelly == 0.0

    @pytest.mark.asyncio
    async def test_calculate_kelly_size_with_fraction(self, risk_manager):
        """Test Kelly position size calculation."""
        # Setup
        risk_manager._win_rate = 0.6
        risk_manager._avg_win = Decimal("500")
        risk_manager._avg_loss = Decimal("300")

        # Calculate Kelly size
        kelly_size = risk_manager._calculate_kelly_size(
            base_size=10,
            account_balance=100000.0,
            entry_price=1000.0
        )

        # Should return a reasonable position size
        assert kelly_size > 0
        assert kelly_size <= 10  # Should not exceed base size

    @pytest.mark.asyncio
    async def test_kelly_size_with_negative_fraction(self, risk_manager):
        """Test Kelly size when fraction would be negative."""
        # Setup losing statistics
        risk_manager._win_rate = 0.3  # Low win rate
        risk_manager._avg_win = Decimal("100")
        risk_manager._avg_loss = Decimal("500")

        kelly_size = risk_manager._calculate_kelly_size(
            base_size=10,
            account_balance=100000.0,
            entry_price=1000.0
        )

        # Should return base size when Kelly is negative/zero
        assert kelly_size == 10


class TestTradeHistory:
    """Test trade history management."""

    @pytest.mark.asyncio
    async def test_record_trade_result(self, risk_manager):
        """Test recording a trade result."""
        # Record a winning trade
        await risk_manager.record_trade_result(
            position_id="POS1",
            pnl=500.0,
            duration_seconds=3600
        )

        # Verify trade added to history
        assert len(risk_manager._trade_history) == 1
        trade = risk_manager._trade_history[0]
        assert trade["position_id"] == "POS1"
        assert trade["pnl"] == 500.0
        assert trade["duration"] == 3600
        assert "timestamp" in trade

    @pytest.mark.asyncio
    async def test_record_losing_trade_updates_daily_loss(self, risk_manager):
        """Test that losing trades update daily loss."""
        initial_loss = risk_manager._daily_loss

        # Record a losing trade
        await risk_manager.record_trade_result(
            position_id="POS1",
            pnl=-300.0,
            duration_seconds=1800
        )

        # Verify daily loss updated
        assert risk_manager._daily_loss == initial_loss + Decimal("300")

    @pytest.mark.asyncio
    async def test_record_trade_updates_daily_trades(self, risk_manager):
        """Test that recording trades increments daily trade counter."""
        initial_trades = risk_manager._daily_trades

        # Record trades
        await risk_manager.record_trade_result("POS1", 100.0, 1000)
        await risk_manager.record_trade_result("POS2", -50.0, 2000)

        # Verify counter incremented
        assert risk_manager._daily_trades == initial_trades + 2

    @pytest.mark.asyncio
    async def test_trade_history_max_size(self, risk_manager):
        """Test that trade history respects max size."""
        # Add many trades (more than maxlen of 100)
        for i in range(150):
            await risk_manager.record_trade_result(
                position_id=f"POS{i}",
                pnl=100.0,
                duration_seconds=1000
            )

        # Verify only last 100 trades kept
        assert len(risk_manager._trade_history) == 100
        # First 50 trades should be dropped
        assert risk_manager._trade_history[0]["position_id"] == "POS50"

    @pytest.mark.asyncio
    async def test_update_trade_statistics(self, risk_manager):
        """Test updating win rate and average win/loss statistics."""
        # Add trades
        await risk_manager.add_trade_result(
            instrument="MNQ",
            pnl=500.0,
            entry_price=15000.0,
            exit_price=15050.0,
            size=10,
            side=OrderSide.BUY
        )
        await risk_manager.add_trade_result(
            instrument="MNQ",
            pnl=-200.0,
            entry_price=15000.0,
            exit_price=14980.0,
            size=10,
            side=OrderSide.BUY
        )
        await risk_manager.add_trade_result(
            instrument="MNQ",
            pnl=300.0,
            entry_price=15000.0,
            exit_price=15030.0,
            size=10,
            side=OrderSide.BUY
        )

        # Update statistics
        await risk_manager.update_trade_statistics()

        # Verify statistics updated
        assert risk_manager._win_rate == 2/3  # 2 wins out of 3 trades
        assert risk_manager._avg_win == Decimal("400")  # (500 + 300) / 2
        assert risk_manager._avg_loss == Decimal("200")  # abs(-200) / 1


class TestDailyResetMechanics:
    """Test daily reset functionality."""

    @pytest.mark.asyncio
    async def test_check_daily_reset_new_day(self, risk_manager):
        """Test daily reset when date changes."""
        # Set yesterday's date
        risk_manager._last_reset_date = date.today() - timedelta(days=1)
        risk_manager._daily_loss = Decimal("1000")
        risk_manager._daily_trades = 5

        # Trigger reset check
        await risk_manager.check_daily_reset()

        # Verify reset occurred
        assert risk_manager._daily_loss == Decimal("0")
        assert risk_manager._daily_trades == 0
        assert risk_manager._last_reset_date == date.today()

    @pytest.mark.asyncio
    async def test_check_daily_reset_same_day(self, risk_manager):
        """Test no reset on same day."""
        # Set today's date
        risk_manager._last_reset_date = date.today()
        risk_manager._daily_loss = Decimal("1000")
        risk_manager._daily_trades = 5

        # Trigger reset check
        await risk_manager.check_daily_reset()

        # Verify no reset
        assert risk_manager._daily_loss == Decimal("1000")
        assert risk_manager._daily_trades == 5

    @pytest.mark.asyncio
    async def test_concurrent_daily_reset_thread_safety(self, risk_manager):
        """Test that daily reset is thread-safe."""
        # Set yesterday's date
        risk_manager._last_reset_date = date.today() - timedelta(days=1)
        risk_manager._daily_loss = Decimal("1000")

        # Simulate concurrent reset attempts
        import asyncio
        tasks = [
            asyncio.create_task(risk_manager._check_daily_reset()),
            asyncio.create_task(risk_manager._check_daily_reset()),
            asyncio.create_task(risk_manager._check_daily_reset()),
        ]

        await asyncio.gather(*tasks)

        # Verify reset only happened once
        assert risk_manager._daily_loss == Decimal("0")
        assert risk_manager._last_reset_date == date.today()


class TestPortfolioRisk:
    """Test portfolio risk calculations."""

    @pytest.mark.asyncio
    async def test_calculate_portfolio_risk_with_positions(self, risk_manager):
        """Test portfolio risk calculation with multiple positions."""
        # Setup positions
        positions = [
            MagicMock(spec=Position, id=1, contractId="MNQ", averagePrice=15000.0, size=2),
            MagicMock(spec=Position, id=2, contractId="ES", averagePrice=4400.0, size=1),
        ]

        # Mock position risk calculations
        async def mock_calculate_position_risk(pos):
            if pos.id == 1:
                return {"amount": Decimal("1000"), "percent": Decimal("0.01")}
            else:
                return {"amount": Decimal("500"), "percent": Decimal("0.005")}

        risk_manager._calculate_position_risk = mock_calculate_position_risk

        # Calculate portfolio risk
        total_risk = await risk_manager._calculate_portfolio_risk(positions)

        # Expected: (1000 + 500) / 100000 = 0.015
        assert total_risk == 0.015

    @pytest.mark.asyncio
    async def test_calculate_portfolio_risk_empty(self, risk_manager):
        """Test portfolio risk with no positions."""
        total_risk = await risk_manager._calculate_portfolio_risk([])

        # Should return 0 with no positions
        assert total_risk == 0.0

    @pytest.mark.asyncio
    async def test_calculate_position_risk_with_stop_order(self, risk_manager):
        """Test individual position risk calculation with stop order."""
        # Setup position
        position = MagicMock(spec=Position)
        position.contractId = "MNQ"
        position.averagePrice = 15000.0
        position.size = 2

        # Setup stop order
        stop_order = MagicMock()
        stop_order.contractId = "MNQ"
        stop_order.type = 4  # STOP
        stop_order.stopPrice = 14950.0

        risk_manager.orders = MagicMock()
        risk_manager.orders.search_open_orders = AsyncMock(return_value=[stop_order])

        # Calculate risk
        risk = await risk_manager._calculate_position_risk(position)

        # Risk = (15000 - 14950) * 2 = 100
        assert risk["amount"] == Decimal("100")
        assert risk["percent"] == Decimal("0.001")  # 100 / 100000

    @pytest.mark.asyncio
    async def test_calculate_position_risk_without_stop(self, risk_manager):
        """Test position risk calculation without stop order."""
        # Setup position
        position = MagicMock(spec=Position)
        position.contractId = "MNQ"
        position.averagePrice = 15000.0
        position.size = 2

        risk_manager.orders = MagicMock()
        risk_manager.orders.search_open_orders = AsyncMock(return_value=[])
        risk_manager.config.default_stop_distance = Decimal("50")

        # Calculate risk (uses default stop distance)
        risk = await risk_manager._calculate_position_risk(position)

        # Risk = 50 * 2 = 100
        assert risk["amount"] == Decimal("100")


class TestMemoryStats:
    """Test memory statistics reporting."""

    @pytest.mark.asyncio
    async def test_get_memory_stats(self, risk_manager):
        """Test memory statistics calculation."""
        # Add some trade history
        for i in range(10):
            risk_manager._trade_history.append({"pnl": 100.0})

        # Get memory stats
        stats = risk_manager.get_memory_stats()

        # Verify stats structure
        assert "total_mb" in stats
        assert "trade_history_mb" in stats
        assert "base_overhead_mb" in stats
        assert "risk_data_mb" in stats
        assert "config_mb" in stats

        # Verify reasonable values
        assert stats["total_mb"] > 0
        assert stats["trade_history_mb"] >= 0

    @pytest.mark.asyncio
    async def test_get_memory_stats_error_handling(self, risk_manager):
        """Test memory stats error handling."""
        # Force an error by corrupting internal state
        risk_manager._trade_history = None

        # Should handle error gracefully
        stats = risk_manager.get_memory_stats()

        assert stats["total_mb"] == 0.0
        assert stats["error_code"] == 1.0
