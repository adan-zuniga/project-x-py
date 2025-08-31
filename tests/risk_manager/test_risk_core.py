"""Tests for RiskManager core functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from project_x_py.risk_manager import RiskManager


@pytest.mark.asyncio
class TestRiskManagerCore:
    """Test RiskManager core functionality."""

    @pytest.fixture
    async def risk_manager(self):
        """Create a RiskManager instance for testing."""
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(balance=100000.0)

        mock_position_manager = MagicMock()
        mock_order_manager = MagicMock()
        mock_event_bus = MagicMock()

        rm = RiskManager(
            project_x=mock_client,
            position_manager=mock_position_manager,
            order_manager=mock_order_manager,
            event_bus=mock_event_bus,
        )
        return rm

    async def test_validate_trade_risk_acceptable(self, risk_manager):
        """Test trade validation with acceptable risk."""
        from datetime import datetime

        from project_x_py.models import Account, Order

        rm = risk_manager

        # Properly mock the position manager as an async mock object
        mock_positions = AsyncMock()
        mock_positions.get_all_positions = AsyncMock(return_value=[])
        rm.positions = mock_positions

        # Mock internal methods
        mock_account = Account(
            id=12345,
            name="Test Account",
            balance=100000.0,
            canTrade=True,
            isVisible=True,
            simulated=True,
        )
        rm._get_account_info = AsyncMock(return_value=mock_account)
        rm._calculate_portfolio_risk = AsyncMock(return_value=0.02)  # 2% risk
        rm._count_correlated_positions = AsyncMock(return_value=0)
        rm._is_within_trading_hours = MagicMock(return_value=True)

        # Create an Order object
        order = Order(
            id=1,
            accountId=12345,
            contractId="MGC",
            creationTimestamp=datetime.now().isoformat(),
            updateTimestamp=None,
            status=1,  # Open
            type=2,  # Market
            side=0,  # Buy
            size=2,
            limitPrice=1900.0,
            stopPrice=1890.0,
        )

        result = await rm.validate_trade(order)

        # Check correct response fields
        assert result["is_valid"] is True
        assert result["current_risk"] >= 0
        assert len(result["reasons"]) == 0  # No rejection reasons

    async def test_validate_trade_risk_too_high(self, risk_manager):
        """Test trade validation with excessive risk."""
        from datetime import datetime

        from project_x_py.models import Account, Order

        rm = risk_manager

        # Mock the position manager
        mock_positions = AsyncMock()
        mock_positions.get_all_positions = AsyncMock(return_value=[])
        rm.positions = mock_positions

        # Mock internal methods
        mock_account = Account(
            id=12345,
            name="Test Account",
            balance=100000.0,
            canTrade=True,
            isVisible=True,
            simulated=True,
        )
        rm._get_account_info = AsyncMock(return_value=mock_account)
        rm._calculate_portfolio_risk = AsyncMock(return_value=0.02)  # 2% risk
        rm._count_correlated_positions = AsyncMock(return_value=0)
        rm._is_within_trading_hours = MagicMock(return_value=True)

        # Set daily trades to exceed limit
        rm._daily_trades = 100  # Exceed default limit

        # Create an Order object
        order = Order(
            id=1,
            accountId=12345,
            contractId="NQ",
            creationTimestamp=datetime.now().isoformat(),
            updateTimestamp=None,
            status=1,  # Open
            type=2,  # Market
            side=0,  # Buy
            size=10,
            limitPrice=15000.0,
            stopPrice=14000.0,  # $1000 per contract risk
        )

        result = await rm.validate_trade(order)

        assert result["is_valid"] is False
        assert len(result["reasons"]) > 0  # Should have rejection reasons

    async def test_validate_trade_max_positions_exceeded(self, risk_manager):
        """Test trade validation when max positions exceeded."""
        from datetime import datetime

        from project_x_py.models import Account, Order

        rm = risk_manager

        # Mock many existing positions
        existing_positions = [MagicMock(contractId=f"POS{i}") for i in range(10)]

        # Mock the position manager
        mock_positions = AsyncMock()
        mock_positions.get_all_positions = AsyncMock(return_value=existing_positions)
        rm.positions = mock_positions

        # Mock internal methods
        mock_account = Account(
            id=12345,
            name="Test Account",
            balance=100000.0,
            canTrade=True,
            isVisible=True,
            simulated=True,
        )
        rm._get_account_info = AsyncMock(return_value=mock_account)
        rm._calculate_portfolio_risk = AsyncMock(return_value=0.02)  # 2% risk
        rm._count_correlated_positions = AsyncMock(return_value=0)
        rm._is_within_trading_hours = MagicMock(return_value=True)

        # Create an Order object
        order = Order(
            id=1,
            accountId=12345,
            contractId="NEW",
            creationTimestamp=datetime.now().isoformat(),
            updateTimestamp=None,
            status=1,  # Open
            type=2,  # Market
            side=0,  # Buy
            size=1,
            limitPrice=100.0,
            stopPrice=99.0,
        )

        result = await rm.validate_trade(order)

        assert result["is_valid"] is False
        assert any(
            "Maximum positions limit reached" in reason for reason in result["reasons"]
        )

    async def test_calculate_position_size(self, risk_manager):
        """Test position size calculation based on risk."""
        from project_x_py.models import Account

        rm = risk_manager

        # Mock internal methods
        mock_account = Account(
            id=12345,
            name="Test Account",
            balance=100000.0,
            canTrade=True,
            isVisible=True,
            simulated=True,
        )
        rm._get_account_info = AsyncMock(return_value=mock_account)
        rm._get_win_rate = MagicMock(return_value=(0.6, 2.0))  # 60% win rate, 2:1 R:R

        result = await rm.calculate_position_size(
            entry_price=1900.0,
            stop_loss=1890.0,
            risk_amount=1000.0,  # Risk $1000
        )

        # Result should be a dictionary with position size
        assert result["position_size"] > 0
        assert result["risk_amount"] > 0
        assert result["risk_percent"] >= 0

    async def test_calculate_position_size_with_max_limit(self, risk_manager):
        """Test position size calculation respects max size."""
        from project_x_py.models import Account

        rm = risk_manager
        rm.config.max_position_size = 50

        # Mock internal methods
        mock_account = Account(
            id=12345,
            name="Test Account",
            balance=100000.0,
            canTrade=True,
            isVisible=True,
            simulated=True,
        )
        rm._get_account_info = AsyncMock(return_value=mock_account)
        rm._get_win_rate = MagicMock(return_value=(0.6, 2.0))  # 60% win rate, 2:1 R:R

        result = await rm.calculate_position_size(
            entry_price=4400.0,
            stop_loss=4390.0,
            risk_amount=10000.0,  # Large risk amount
        )

        # Should be capped at max_position_size
        assert result["position_size"] <= rm.config.max_position_size
