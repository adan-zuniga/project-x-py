"""Additional tests for risk manager to improve coverage."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_x_py.risk_manager.core import RiskManager
from project_x_py.risk_manager.managed_trade import ManagedTrade
from project_x_py.types import OrderSide


@pytest.mark.asyncio
class TestAdditionalCoverage:
    """Additional tests to improve coverage."""

    @pytest.fixture
    def setup_risk_manager(self):
        """Create a RiskManager for testing."""
        mock_client = AsyncMock()
        mock_order_manager = AsyncMock()
        mock_position_manager = AsyncMock()
        mock_event_bus = AsyncMock()

        # Mock the async task creation to avoid runtime errors
        with patch('asyncio.create_task'):
            risk_manager = RiskManager(
                project_x=mock_client,
                order_manager=mock_order_manager,
                event_bus=mock_event_bus,
            )
            risk_manager.set_position_manager(mock_position_manager)
            # Set the _init_task to a mock to avoid issues
            risk_manager._init_task = MagicMock()

        return {
            "risk_manager": risk_manager,
            "client": mock_client,
            "order_manager": mock_order_manager,
            "position_manager": mock_position_manager,
            "event_bus": mock_event_bus,
        }

    @pytest.fixture
    def setup_managed_trade(self):
        """Create a ManagedTrade for testing."""
        mock_client = AsyncMock()
        mock_order_manager = AsyncMock()
        mock_position_manager = AsyncMock()
        mock_event_bus = AsyncMock()
        mock_data_manager = AsyncMock()

        # Mock the async task creation to avoid runtime errors
        with patch('asyncio.create_task'):
            risk_manager = RiskManager(
                project_x=mock_client,
                order_manager=mock_order_manager,
                event_bus=mock_event_bus,
            )
            risk_manager.set_position_manager(mock_position_manager)
            risk_manager._init_task = MagicMock()

        managed_trade = ManagedTrade(
            risk_manager=risk_manager,
            order_manager=mock_order_manager,
            position_manager=mock_position_manager,
            instrument_id="MNQ",
            data_manager=mock_data_manager,
            event_bus=mock_event_bus,
        )

        return {
            "trade": managed_trade,
            "risk_manager": risk_manager,
            "order_manager": mock_order_manager,
            "position_manager": mock_position_manager,
            "event_bus": mock_event_bus,
            "data_manager": mock_data_manager,
            "client": mock_client,
        }

    async def test_managed_trade_property_aliases(self, setup_managed_trade):
        """Test ManagedTrade property aliases."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Test property aliases
        assert trade.risk_manager is trade.risk
        assert trade.order_manager is trade.orders
        assert trade.position_manager is trade.positions

    async def test_managed_trade_concurrent_entries_prevention(self, setup_managed_trade):
        """Test that concurrent entries are prevented."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Set existing entry order
        entry_order = MagicMock()
        entry_order.id = 123
        trade._entry_order = entry_order

        # Should prevent concurrent entries
        with pytest.raises(ValueError, match="Trade already has entry order"):
            await trade.enter_long()

    async def test_managed_trade_no_data_manager_market_price(self, setup_managed_trade):
        """Test market price retrieval without data manager."""
        mocks = setup_managed_trade
        trade = mocks["trade"]
        trade.data_manager = None

        with pytest.raises(RuntimeError, match="No data manager available"):
            await trade._get_market_price()

    async def test_managed_trade_market_price_fallback(self, setup_managed_trade):
        """Test market price fallback to current price."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Mock data retrieval to fail, fallback to current price
        mocks["data_manager"].get_data = AsyncMock(return_value=None)
        mocks["data_manager"].get_current_price = AsyncMock(return_value=20000.0)

        price = await trade._get_market_price()
        assert price == 20000.0

    async def test_managed_trade_is_filled_states(self, setup_managed_trade):
        """Test is_filled method with various states."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # No entry order
        assert not trade.is_filled()

        # Entry order not filled
        entry_order = MagicMock()
        entry_order.status = 1  # Working
        trade._entry_order = entry_order
        assert not trade.is_filled()

        # Entry order filled
        entry_order.status = 2  # Filled
        entry_order.filled_quantity = 2
        entry_order.size = 2
        assert trade.is_filled()

    async def test_managed_trade_emergency_exit(self, setup_managed_trade):
        """Test emergency exit functionality."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Set up orders and position
        order1 = MagicMock()
        order1.id = 123
        trade._orders = [order1]

        position = MagicMock()
        trade._positions = [position]

        # Mock close position
        trade.close_position = AsyncMock(return_value={"success": True})

        result = await trade.emergency_exit()
        assert result is True

    async def test_risk_manager_extract_symbol(self, setup_risk_manager):
        """Test symbol extraction from contract ID."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Normal contract ID
        symbol = rm._extract_symbol("CON.F.US.MNQ.U24")
        assert symbol == "MNQ"

        # Short contract ID
        symbol = rm._extract_symbol("MNQ")
        assert symbol == "MNQ"

    async def test_risk_manager_kelly_fraction_edge_cases(self, setup_risk_manager):
        """Test Kelly fraction calculation edge cases."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Zero win rate
        rm._win_rate = 0.0
        kelly = rm._calculate_kelly_fraction()
        assert kelly == 0.0

        # Zero average loss
        rm._win_rate = 0.6
        rm._avg_loss = 0.0
        kelly = rm._calculate_kelly_fraction()
        assert kelly == 0.0

    async def test_risk_manager_calculate_stop_loss_fallback(self, setup_risk_manager):
        """Test stop loss calculation fallback."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Unknown stop loss type
        rm.config.stop_loss_type = "unknown"

        stop_price = await rm.calculate_stop_loss(20000.0, OrderSide.BUY)
        assert stop_price == 19950.0  # fallback

    async def test_risk_manager_should_activate_trailing_stop_disabled(self, setup_risk_manager):
        """Test trailing stop activation when disabled."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        rm.config.use_trailing_stops = False
        result = await rm.should_activate_trailing_stop(20000.0, 20100.0, OrderSide.BUY)
        assert result is False

    async def test_risk_manager_portfolio_risk_empty_positions(self, setup_risk_manager):
        """Test portfolio risk calculation with empty positions."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        risk = await rm._calculate_portfolio_risk([])
        assert risk == 0.0

    async def test_risk_manager_sharpe_ratio_edge_cases(self, setup_risk_manager):
        """Test Sharpe ratio calculation edge cases."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Empty history
        rm._trade_history.clear()
        sharpe = rm._calculate_sharpe_ratio()
        assert sharpe == 0.0

        # Single trade
        rm._trade_history.append({"pnl": 100.0})
        sharpe = rm._calculate_sharpe_ratio()
        assert sharpe == 0.0

        # Zero standard deviation
        rm._trade_history.clear()
        for _ in range(5):
            rm._trade_history.append({"pnl": 100.0})
        sharpe = rm._calculate_sharpe_ratio()
        assert sharpe == 0.0

    async def test_managed_trade_wait_for_fill_no_event_bus(self, setup_managed_trade):
        """Test wait for fill without event bus."""
        mocks = setup_managed_trade
        trade = mocks["trade"]
        trade.event_bus = None

        order = MagicMock()
        order.id = 123

        trade._poll_for_order_fill = AsyncMock(return_value=True)

        result = await trade._wait_for_order_fill(order, timeout_seconds=1)
        assert result is True

    async def test_managed_trade_poll_for_fill_exception_handling(self, setup_managed_trade):
        """Test polling with exception handling."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        order = MagicMock()
        order.id = 123

        # First call raises exception, second succeeds
        call_count = 0
        def mock_search_with_exception():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            else:
                updated_order = MagicMock()
                updated_order.id = 123
                updated_order.is_filled = True
                return [updated_order]

        mocks["order_manager"].search_open_orders = AsyncMock(side_effect=mock_search_with_exception)
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[])

        result = await trade._poll_for_order_fill(order, timeout_seconds=2)
        assert result is True

    async def test_managed_trade_adjust_stop_loss_failure(self, setup_managed_trade):
        """Test adjust stop loss failure."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # No stop order
        result = await trade.adjust_stop_loss(19940.0)
        assert result is False

        # With stop order but modify fails
        stop_order = MagicMock()
        stop_order.id = 123
        trade._stop_order = stop_order

        mocks["order_manager"].modify_order = AsyncMock(side_effect=Exception("Modify failed"))
        result = await trade.adjust_stop_loss(19940.0)
        assert result is False

    async def test_risk_manager_get_account_info_no_accounts(self, setup_risk_manager):
        """Test get account info when no accounts found."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        mocks["client"].list_accounts = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="No account found"):
            await rm._get_account_info()

    async def test_risk_manager_trading_hours_validation(self, setup_risk_manager):
        """Test trading hours validation."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Disabled restriction
        rm.config.restrict_trading_hours = False
        assert rm._is_within_trading_hours() is True

    async def test_risk_manager_memory_stats_error(self, setup_risk_manager):
        """Test memory stats error handling."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Force error
        rm._trade_history = None

        stats = rm.get_memory_stats()
        assert "error_code" in stats
        assert stats["error_code"] == 1.0

    async def test_managed_trade_calculate_position_size_with_overrides(self, setup_managed_trade):
        """Test position size calculation with risk overrides."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        trade.max_risk_percent = 0.02
        trade.max_risk_amount = 1000.0

        mocks["risk_manager"].calculate_position_size = AsyncMock(
            return_value={"position_size": 2}
        )

        result = await trade.calculate_position_size(
            entry_price=20000.0,
            stop_loss=19950.0
        )

        assert result == 2
        mocks["risk_manager"].calculate_position_size.assert_called_once_with(
            entry_price=20000.0,
            stop_loss=19950.0,
            risk_percent=0.02,
            risk_amount=1000.0,
        )

    async def test_managed_trade_get_account_balance_methods(self, setup_managed_trade):
        """Test get account balance methods."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Successful retrieval
        account = MagicMock()
        account.balance = 150000.0
        mocks["client"].list_accounts = AsyncMock(return_value=[account])

        balance = await trade._get_account_balance()
        assert balance == 150000.0

        # No accounts
        mocks["client"].list_accounts = AsyncMock(return_value=[])
        balance = await trade._get_account_balance()
        assert balance == 100000.0  # Default
