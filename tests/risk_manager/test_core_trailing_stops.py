"""Tests for RiskManager trailing stop functionality to achieve full coverage."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_x_py.models import Account, Instrument
from project_x_py.risk_manager.core import RiskManager
from project_x_py.types import OrderSide, OrderType


@pytest.mark.asyncio
class TestRiskManagerTrailingStops:
    """Test RiskManager trailing stop functionality comprehensively."""

    @pytest.fixture
    async def setup_risk_manager(self):
        """Create a fully configured RiskManager for testing."""
        mock_client = AsyncMock()
        mock_order_manager = AsyncMock()
        mock_position_manager = AsyncMock()
        mock_event_bus = AsyncMock()
        mock_data_manager = AsyncMock()

        # Create risk manager with mocked async task
        with patch('asyncio.create_task'):
            risk_manager = RiskManager(
                project_x=mock_client,
                order_manager=mock_order_manager,
                event_bus=mock_event_bus,
                data_manager=mock_data_manager,
            )
            risk_manager.set_position_manager(mock_position_manager)
            risk_manager._init_task = MagicMock()

        # Mock account info
        account = Account(
            id=12345,
            name="Test Account",
            balance=100000.0,
            canTrade=True,
            isVisible=True,
            simulated=True,
        )
        mock_client.list_accounts = AsyncMock(return_value=[account])

        return {
            "risk_manager": risk_manager,
            "client": mock_client,
            "order_manager": mock_order_manager,
            "position_manager": mock_position_manager,
            "event_bus": mock_event_bus,
            "data_manager": mock_data_manager,
        }

    async def test_attach_risk_orders_atr_stop_no_data_manager(self, setup_risk_manager):
        """Test ATR stop calculation with no data manager (lines 438-442)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]
        rm.data_manager = None  # Remove data manager

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2
        position.averagePrice = 20000.0

        # Configure for ATR stop
        rm.config.use_stop_loss = True
        rm.config.stop_loss_type = "atr"
        rm.config.default_stop_distance = 10.0  # 10 ticks
        rm.config.default_stop_atr_multiplier = 2.0

        # Mock instrument
        instrument = MagicMock()
        instrument.tickSize = 0.25
        mocks["client"].get_instrument = AsyncMock(return_value=instrument)

        # Mock order placement success
        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = "123"
        mocks["order_manager"].place_stop_order = AsyncMock(return_value=stop_response)

        result = await rm.attach_risk_orders(position)

        # Should fall back to fixed stop when no data manager
        mocks["order_manager"].place_stop_order.assert_called_once()
        assert result["bracket_order"].success is True

    async def test_attach_risk_orders_atr_stop_insufficient_data(self, setup_risk_manager):
        """Test ATR stop calculation with insufficient data (lines 452-458)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2
        position.averagePrice = 20000.0

        # Configure for ATR stop
        rm.config.use_stop_loss = True
        rm.config.stop_loss_type = "atr"
        rm.config.default_stop_distance = 10.0
        rm.config.default_stop_atr_multiplier = 2.0

        # Mock instrument
        instrument = MagicMock()
        instrument.tickSize = 0.25
        mocks["client"].get_instrument = AsyncMock(return_value=instrument)

        # Mock insufficient data (less than 14 periods)
        import polars as pl
        insufficient_data = pl.DataFrame({
            "high": [20010.0, 20020.0, 20005.0],
            "low": [19990.0, 19995.0, 19980.0],
            "close": [20000.0, 20010.0, 19995.0],
        })
        mocks["data_manager"].get_data = AsyncMock(return_value=insufficient_data)

        # Mock order placement
        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = "123"
        mocks["order_manager"].place_stop_order = AsyncMock(return_value=stop_response)

        result = await rm.attach_risk_orders(position)

        # Should fall back to fixed stop with insufficient data
        mocks["order_manager"].place_stop_order.assert_called_once()
        assert result["bracket_order"].success is True

    async def test_attach_risk_orders_atr_stop_success(self, setup_risk_manager):
        """Test successful ATR stop calculation (lines 460-472)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2
        position.averagePrice = 20000.0

        # Configure for ATR stop
        rm.config.use_stop_loss = True
        rm.config.stop_loss_type = "atr"
        rm.config.default_stop_distance = 10.0
        rm.config.default_stop_atr_multiplier = 2.0

        # Mock instrument
        instrument = MagicMock()
        instrument.tickSize = 0.25
        mocks["client"].get_instrument = AsyncMock(return_value=instrument)

        # Mock sufficient data for ATR calculation
        import polars as pl
        data = pl.DataFrame({
            "high": [20010.0 + i * 5 for i in range(50)],
            "low": [19990.0 + i * 5 for i in range(50)],
            "close": [20000.0 + i * 5 for i in range(50)],
        })
        mocks["data_manager"].get_data = AsyncMock(return_value=data)

        # Mock calculate_atr function
        with patch('project_x_py.indicators.calculate_atr') as mock_atr:
            atr_data = data.clone()
            atr_data = atr_data.with_columns(pl.lit(50.0).alias("atr_14"))
            mock_atr.return_value = atr_data

            # Mock order placement
            stop_response = MagicMock()
            stop_response.success = True
            stop_response.orderId = "123"
            mocks["order_manager"].place_stop_order = AsyncMock(return_value=stop_response)

            await rm.attach_risk_orders(position)

            # Should use ATR calculation
            mock_atr.assert_called_once_with(data, period=14)
            mocks["order_manager"].place_stop_order.assert_called_once()
            # Stop loss should be entry - (ATR * multiplier) = 20000 - (50 * 2) = 19900
            call_args = mocks["order_manager"].place_stop_order.call_args
            assert call_args[1]["stop_price"] == 19900.0

    async def test_attach_risk_orders_atr_calculation_none_result(self, setup_risk_manager):
        """Test ATR calculation returning None (lines 469-472)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2
        position.averagePrice = 20000.0

        # Configure for ATR stop
        rm.config.use_stop_loss = True
        rm.config.stop_loss_type = "atr"
        rm.config.default_stop_distance = 10.0
        rm.config.default_stop_atr_multiplier = 2.0

        # Mock instrument
        instrument = MagicMock()
        instrument.tickSize = 0.25
        mocks["client"].get_instrument = AsyncMock(return_value=instrument)

        # Mock sufficient data but ATR calculation returns None
        import polars as pl
        data = pl.DataFrame({
            "high": [20010.0 + i * 5 for i in range(50)],
            "low": [19990.0 + i * 5 for i in range(50)],
            "close": [20000.0 + i * 5 for i in range(50)],
        })
        mocks["data_manager"].get_data = AsyncMock(return_value=data)

        # Mock calculate_atr to return None ATR value
        with patch('project_x_py.indicators.calculate_atr') as mock_atr:
            atr_data = data.clone()
            atr_data = atr_data.with_columns(pl.lit(None).alias("atr_14"))
            mock_atr.return_value = atr_data

            # Mock order placement
            stop_response = MagicMock()
            stop_response.success = True
            stop_response.orderId = "123"
            mocks["order_manager"].place_stop_order = AsyncMock(return_value=stop_response)

            await rm.attach_risk_orders(position)

            # Should fall back to fixed stop when ATR is None
            mocks["order_manager"].place_stop_order.assert_called_once()
            # Should use fixed stop: 10 ticks * 0.25 = 2.5 points = 19997.5
            call_args = mocks["order_manager"].place_stop_order.call_args
            assert call_args[1]["stop_price"] == 19997.5

    async def test_adjust_stops_order_not_found(self, setup_risk_manager):
        """Test adjust stops when order is not found (line 534)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.id = "pos123"

        # Mock search to return no stop orders
        mocks["order_manager"].search_open_orders = AsyncMock(return_value=[])

        result = await rm.adjust_stops(position, new_stop=19990.0)

        # Should return False when no stop order found
        assert result is False

    async def test_attach_risk_orders_order_placement_failure(self, setup_risk_manager):
        """Test attach risk orders with order placement failure (lines 603-605)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2
        position.averagePrice = 20000.0

        # Configure stops
        rm.config.use_stop_loss = True
        rm.config.use_take_profit = True

        # Mock instrument
        instrument = MagicMock()
        instrument.tickSize = 0.25
        mocks["client"].get_instrument = AsyncMock(return_value=instrument)

        # Mock stop order placement failure
        stop_response = MagicMock()
        stop_response.success = False
        mocks["order_manager"].place_stop_order = AsyncMock(return_value=stop_response)

        # Mock target order placement success
        target_response = MagicMock()
        target_response.success = True
        target_response.orderId = "124"
        mocks["order_manager"].place_limit_order = AsyncMock(return_value=target_response)

        # Mock event emission
        mocks["event_bus"].emit = AsyncMock()

        # Should not raise exception, just return unsuccessful result
        result = await rm.attach_risk_orders(position, stop_loss=19950.0, take_profit=20100.0)

        # Stop order should have failed
        assert result["bracket_order"].success is False

    async def test_adjust_stops_modification_error(self, setup_risk_manager):
        """Test adjust stops with modification error (lines 663-665)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.id = "pos123"

        # Create stop order
        stop_order = MagicMock()
        stop_order.contractId = "MNQ"
        stop_order.type = OrderType.STOP
        stop_order.side = OrderSide.SELL
        stop_order.id = 123
        mocks["order_manager"].search_open_orders = AsyncMock(return_value=[stop_order])

        # Mock modify order to raise exception
        mocks["order_manager"].modify_order = AsyncMock(side_effect=Exception("Modification failed"))

        result = await rm.adjust_stops(position, new_stop=19990.0)

        assert result is False

    async def test_get_risk_metrics_position_manager_not_set(self, setup_risk_manager):
        """Test get risk metrics when position manager not set (line 678)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Remove position manager
        rm.positions = None

        with pytest.raises(ValueError, match="Position manager not set"):
            await rm.get_risk_metrics()

    async def test_get_risk_metrics_error_handling(self, setup_risk_manager):
        """Test get risk metrics with error handling (lines 720-722)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Mock position manager to raise exception
        mocks["position_manager"].get_all_positions = AsyncMock(side_effect=Exception("Position fetch failed"))

        with pytest.raises(Exception, match="Position fetch failed"):
            await rm.get_risk_metrics()

    async def test_get_account_info_no_accounts(self, setup_risk_manager):
        """Test get account info when no accounts found (line 731)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Mock client to return empty accounts list
        mocks["client"].list_accounts = AsyncMock(return_value=[])

        with pytest.raises(ValueError, match="No account found"):
            await rm._get_account_info()

    async def test_calculate_kelly_fraction_edge_cases(self, setup_risk_manager):
        """Test Kelly fraction calculation edge cases (line 766)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test with zero avg_loss (b = 0 case)
        rm._win_rate = 0.6
        rm._avg_win = 150.0
        rm._avg_loss = 0.0

        kelly = rm._calculate_kelly_fraction()
        assert kelly == 0.0

        # Test with negative Kelly result (should be clamped to 0)
        rm._avg_loss = 300.0  # Very high loss
        rm._avg_win = 50.0    # Low win
        rm._win_rate = 0.3    # Low win rate

        kelly = rm._calculate_kelly_fraction()
        assert kelly == 0.0

    async def test_extract_symbol_edge_cases(self, setup_risk_manager):
        """Test symbol extraction edge cases (line 825)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test with insufficient parts
        short_contract_id = "MNQ"
        symbol = rm._extract_symbol(short_contract_id)
        assert symbol == "MNQ"

        # Test with normal contract ID
        normal_contract_id = "CON.F.US.MNQ.U24"
        symbol = rm._extract_symbol(normal_contract_id)
        assert symbol == "MNQ"

    async def test_is_within_trading_hours_edge_cases(self, setup_risk_manager):
        """Test trading hours validation edge cases (line 841, 849)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test when restriction is disabled
        rm.config.restrict_trading_hours = False
        result = rm._is_within_trading_hours()
        assert result is True

        # Test with valid trading hours
        rm.config.restrict_trading_hours = True
        rm.config.allowed_trading_hours = [("09:30", "16:00")]

        # Mock current time to be within hours
        with patch('project_x_py.risk_manager.core.datetime') as mock_datetime:
            from datetime import datetime, time
            mock_datetime.now.return_value.time.return_value = time(12, 0)  # 12:00 PM
            mock_datetime.strptime = datetime.strptime

            result = rm._is_within_trading_hours()
            assert result is True

        # Test with time outside hours
        with patch('project_x_py.risk_manager.core.datetime') as mock_datetime:
            from datetime import datetime, time
            mock_datetime.now.return_value.time.return_value = time(8, 0)  # 8:00 AM
            mock_datetime.strptime = datetime.strptime

            result = rm._is_within_trading_hours()
            assert result is False

    async def test_get_market_price_comprehensive(self, setup_risk_manager):
        """Test get market price with comprehensive scenarios (lines 877-898)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test with no data manager
        rm.data_manager = None
        with pytest.raises(RuntimeError, match="Data manager not available"):
            await rm._get_market_price("MNQ")

        # Restore data manager
        rm.data_manager = mocks["data_manager"]

        # Test successful retrieval from first timeframe
        import polars as pl
        data = pl.DataFrame({"close": [20000.0]})
        mocks["data_manager"].get_data = AsyncMock(return_value=data)

        price = await rm._get_market_price("MNQ")
        assert price == 20000.0

        # Test fallback through timeframes
        # First mock to fail for 3 calls, then succeed
        call_results = [
            Exception("No data"),
            Exception("No data"),
            Exception("No data"),
            pl.DataFrame({"close": [20100.0]})
        ]
        mocks["data_manager"].get_data = AsyncMock(side_effect=call_results)

        price = await rm._get_market_price("MNQ")
        assert price == 20100.0

        # Test fallback to current price
        mocks["data_manager"].get_data = AsyncMock(side_effect=Exception("No OHLC data"))
        mocks["data_manager"].get_current_price = AsyncMock(return_value=20200.0)

        price = await rm._get_market_price("MNQ")
        assert price == 20200.0

        # Test complete failure
        mocks["data_manager"].get_current_price = AsyncMock(side_effect=Exception("No current price"))

        with pytest.raises(RuntimeError, match="Unable to fetch current market price"):
            await rm._get_market_price("MNQ")

    async def test_monitor_trailing_stop_comprehensive(self, setup_risk_manager):
        """Test trailing stop monitoring comprehensive scenarios (lines 919-962)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2
        position.averagePrice = 20000.0
        position.id = "pos123"

        # Configure trailing stops
        rm.config.trailing_stop_trigger = 100.0  # $100 profit trigger
        rm.config.trailing_stop_distance = 50.0   # $50 trail distance

        # Test with position manager not set
        rm.positions = None
        bracket_order = {"stop_order_id": "123", "target_order_id": "124"}

        # Should exit early
        task = asyncio.create_task(rm._monitor_trailing_stop(position, bracket_order))
        await asyncio.sleep(0.1)  # Let it run briefly
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Restore position manager
        rm.positions = mocks["position_manager"]

        # Test position closed scenario
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[])

        task = asyncio.create_task(rm._monitor_trailing_stop(position, bracket_order))
        await asyncio.sleep(0.1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Test normal monitoring with price movement
        current_position = MagicMock()
        current_position.id = "pos123"
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[current_position])

        # Mock market price progression
        price_progression = [20000.0, 20050.0, 20120.0]  # Price increases enough to trigger trailing
        price_index = 0

        def mock_get_market_price(_contract_id):
            nonlocal price_index
            if price_index < len(price_progression):
                price = price_progression[price_index]
                price_index += 1
                return price
            return 20120.0

        rm._get_market_price = AsyncMock(side_effect=mock_get_market_price)
        mocks["risk_manager"].adjust_stops = AsyncMock(return_value=True)

        # Start monitoring task and let it run briefly
        task = asyncio.create_task(rm._monitor_trailing_stop(position, bracket_order))
        await asyncio.sleep(0.3)  # Let it run and trigger trailing stop
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have attempted to adjust stops
        assert rm._get_market_price.call_count > 0

    async def test_monitor_trailing_stop_price_fetch_error(self, setup_risk_manager):
        """Test trailing stop monitoring with price fetch errors (lines 932-936)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2
        position.averagePrice = 20000.0
        position.id = "pos123"

        current_position = MagicMock()
        current_position.id = "pos123"
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[current_position])

        # Mock price fetch to raise RuntimeError
        rm._get_market_price = AsyncMock(side_effect=RuntimeError("Price fetch failed"))

        bracket_order = {"stop_order_id": "123", "target_order_id": "124"}

        # Start monitoring task
        task = asyncio.create_task(rm._monitor_trailing_stop(position, bracket_order))
        await asyncio.sleep(0.2)  # Let it handle the error
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have attempted to get price and handled the error gracefully
        rm._get_market_price.assert_called()

    async def test_monitor_trailing_stop_exception_handling(self, setup_risk_manager):
        """Test trailing stop monitoring exception handling (line 962)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create position
        position = MagicMock()
        position.contractId = "MNQ"
        position.id = "pos123"

        # Mock position manager to raise exception
        mocks["position_manager"].get_all_positions = AsyncMock(side_effect=Exception("Position fetch failed"))

        bracket_order = {"stop_order_id": "123", "target_order_id": "124"}

        # Should handle exception gracefully
        task = asyncio.create_task(rm._monitor_trailing_stop(position, bracket_order))
        await asyncio.sleep(0.1)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Exception should be caught and logged, not propagated

    async def test_calculate_sharpe_ratio_edge_cases(self, setup_risk_manager):
        """Test Sharpe ratio calculation edge cases (line 985)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test with empty trade history
        rm._trade_history.clear()
        sharpe = rm._calculate_sharpe_ratio()
        assert sharpe == 0.0

        # Test with single trade (insufficient data)
        rm._trade_history.append({"pnl": 100.0})
        sharpe = rm._calculate_sharpe_ratio()
        assert sharpe == 0.0

        # Test with zero standard deviation (all identical returns)
        rm._trade_history.clear()
        for _ in range(5):
            rm._trade_history.append({"pnl": 100.0})  # All same PnL

        sharpe = rm._calculate_sharpe_ratio()
        assert sharpe == 0.0  # Zero std dev should return 0

    async def test_cleanup_task_exception_handling(self, setup_risk_manager):
        """Test cleanup task exception handling (line 1103, 1106-1107)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create a task that will raise an exception
        async def failing_task():
            raise ValueError("Task failed")

        task = asyncio.create_task(failing_task())
        rm._active_tasks.add(task)

        # Let the task fail
        with pytest.raises(ValueError):
            await task

        # Now test cleanup
        rm._cleanup_task(task, "pos123")

        # Task should be removed from active tasks
        assert task not in rm._active_tasks

    async def test_cleanup_error_handling(self, setup_risk_manager):
        """Test cleanup error handling during cleanup (lines 1144-1145)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Create a mock task that will cause issues during cleanup
        mock_task = MagicMock()
        mock_task.done.side_effect = Exception("Done check failed")
        mock_task.cancel.side_effect = Exception("Cancel failed")

        rm._active_tasks.add(mock_task)
        rm._trailing_stop_tasks["pos123"] = mock_task

        # Cleanup should handle exceptions gracefully
        await rm.cleanup()  # Should not raise exception

    async def test_calculate_stop_loss_fallback(self, setup_risk_manager):
        """Test calculate stop loss fallback case (line 1186)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test with unrecognized stop loss type
        rm.config.stop_loss_type = "unknown"

        stop_price = await rm.calculate_stop_loss(20000.0, OrderSide.BUY)
        assert stop_price == 19950.0  # entry_price - 50

        stop_price = await rm.calculate_stop_loss(20000.0, OrderSide.SELL)
        assert stop_price == 20050.0  # entry_price + 50

    async def test_calculate_take_profit_edge_cases(self, setup_risk_manager):
        """Test calculate take profit edge cases (lines 1196-1202)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test with None risk_reward_ratio (should use config default)
        rm.config.default_risk_reward_ratio = 2.0

        target = await rm.calculate_take_profit(20000.0, 19950.0, OrderSide.BUY)
        # Risk = 50, Reward = 50 * 2 = 100, Target = 20000 + 100 = 20100
        assert target == 20100.0

        target = await rm.calculate_take_profit(20000.0, 20050.0, OrderSide.SELL)
        # Risk = 50, Reward = 50 * 2 = 100, Target = 20000 - 100 = 19900
        assert target == 19900.0

    async def test_should_activate_trailing_stop_disabled(self, setup_risk_manager):
        """Test should activate trailing stop when disabled (line 1209)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Disable trailing stops
        rm.config.use_trailing_stops = False

        result = await rm.should_activate_trailing_stop(20000.0, 20150.0, OrderSide.BUY)
        assert result is False

    async def test_calculate_kelly_position_size_edge_cases(self, setup_risk_manager):
        """Test Kelly position size calculation edge cases (line 1341)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Test with zero avg_loss
        result = await rm.calculate_kelly_position_size(10, 0.6, 150.0, 0.0)
        assert result == 10  # Should return base size

        # Test with zero win_rate
        result = await rm.calculate_kelly_position_size(10, 0.0, 150.0, 100.0)
        assert result == 10  # Should return base size

        # Test with negative Kelly (high loss rate)
        result = await rm.calculate_kelly_position_size(10, 0.2, 50.0, 200.0)
        assert result == 10  # Kelly negative, clamped to base size

    async def test_cleanup_initialization_error(self, setup_risk_manager):
        """Test cleanup during initialization error (lines 1390-1391, 1396)."""
        mocks = setup_risk_manager
        rm = mocks["risk_manager"]

        # Simulate initialization task failing
        rm._init_task = asyncio.create_task(rm._initialize_risk_stats())
        await asyncio.sleep(0.1)  # Let it start

        # Cancel it to simulate error
        rm._init_task.cancel()

        # Cleanup should handle cancelled initialization task
        await rm.cleanup()

        # The init task should have been processed by cleanup
        # Just verify no exception occurred during cleanup
        assert True  # Cleanup completed without error
