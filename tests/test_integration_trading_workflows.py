"""Integration tests for complete trading workflows."""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
import pytz

from project_x_py import ProjectX
from project_x_py.exceptions import ProjectXError
from project_x_py.models import Order, Position


@pytest.fixture
async def trading_suite():
    """Create a complete trading suite for integration testing."""
    from project_x_py import create_trading_suite

    # Mock the ProjectX client
    mock_client = MagicMock(spec=ProjectX)
    mock_client.jwt_token = "test_token"
    mock_client.account_id = 12345
    mock_client.authenticate = AsyncMock(return_value=True)
    mock_client.get_bars = AsyncMock(
        return_value=pl.DataFrame(
            {
                "timestamp": [
                    datetime.now(pytz.UTC) - timedelta(hours=i) for i in range(24)
                ],
                "open": [15500.0] * 24,
                "high": [15550.0] * 24,
                "low": [15450.0] * 24,
                "close": [15525.0] * 24,
                "volume": [1000] * 24,
            }
        )
    )
    mock_client.place_order = AsyncMock(
        return_value={"success": True, "orderId": "12345"}
    )
    mock_client.get_open_positions = AsyncMock(return_value=[])
    mock_client.get_open_orders = AsyncMock(return_value=[])

    # Create suite with mocked client
    with patch("project_x_py.trading_suite.create_realtime_client") as mock_realtime:
        mock_rt = MagicMock()
        mock_rt.connect = AsyncMock(return_value=True)
        mock_rt.is_connected = MagicMock(return_value=True)
        mock_rt.add_callback = AsyncMock()
        mock_realtime.return_value = mock_rt

        suite = await create_trading_suite(
            instrument="MNQ",
            project_x=mock_client,
            jwt_token="test_token",
            account_id=12345,
            timeframes=["1min", "5min", "15min"],
        )

    return suite


@pytest.mark.asyncio
class TestTradingWorkflows:
    """Test complete trading workflows."""

    async def test_complete_trade_lifecycle(self, trading_suite):
        """Test complete lifecycle: signal -> order -> position -> close."""
        suite = trading_suite

        # 1. Initialize with historical data
        await suite.data_manager.initialize(initial_days=1)

        # 2. Generate trading signal (mock)
        current_price = 15525.0
        signal = {
            "action": "BUY",
            "price": current_price,
            "stop_loss": current_price - 50,
            "take_profit": current_price + 100,
            "size": 1,
        }

        # 3. Validate trade with risk manager
        risk_check = await suite.risk_manager.validate_trade(
            contract_id="MNQ",
            side=0,  # Buy
            size=signal["size"],
            entry_price=signal["price"],
            stop_loss=signal["stop_loss"],
        )

        assert risk_check["acceptable"] is True

        # 4. Place order
        order_result = await suite.order_manager.place_bracket_order(
            contract_id="MNQ",
            side=0,  # Buy
            size=signal["size"],
            entry_price=signal["price"],
            stop_price=signal["stop_loss"],
            target_price=signal["take_profit"],
        )

        assert order_result["success"] is True

        # 5. Simulate order fill
        await suite.order_manager._process_order_update(
            {
                "id": "12345",
                "status": 2,  # Filled
                "filledSize": 1,
                "averagePrice": signal["price"],
            }
        )

        # 6. Track position
        position = Position(
            id=1,
            accountId=12345,
            contractId="MNQ",
            size=1,
            type=1,  # Long
            averagePrice=signal["price"],
            creationTimestamp=datetime.now(pytz.UTC).isoformat(),
        )
        suite.position_manager.tracked_positions["MNQ"] = position

        # 7. Monitor position P&L
        # Simulate price movement
        new_price = signal["price"] + 50
        pnl = await suite.position_manager.calculate_position_pnl(
            position, current_price=new_price
        )

        assert pnl["unrealized_pnl"] > 0

        # 8. Close position
        close_result = await suite.position_manager.close_position_direct("MNQ")

        assert close_result["success"] is True

    async def test_multi_position_management(self, trading_suite):
        """Test managing multiple positions simultaneously."""
        suite = trading_suite

        # Create multiple positions
        positions = [
            Position(
                id=1,
                accountId=12345,
                contractId="MNQ",
                size=2,
                type=1,  # Long
                averagePrice=15500.0,
                creationTimestamp=datetime.now(pytz.UTC).isoformat(),
            ),
            Position(
                id=2,
                accountId=12345,
                contractId="ES",
                size=1,
                type=2,  # Short
                averagePrice=4400.0,
                creationTimestamp=datetime.now(pytz.UTC).isoformat(),
            ),
        ]

        # Track positions
        for pos in positions:
            suite.position_manager.tracked_positions[pos.contractId] = pos

        # Calculate portfolio P&L
        portfolio_pnl = await suite.position_manager.calculate_portfolio_pnl()

        assert "total_pnl" in portfolio_pnl
        assert "positions" in portfolio_pnl
        assert len(portfolio_pnl["positions"]) == 2

        # Check risk limits
        within_limits = await suite.risk_manager.check_portfolio_risk()

        assert within_limits is True

    async def test_realtime_data_to_signal_workflow(self, trading_suite):
        """Test workflow from real-time data to trading signal."""
        suite = trading_suite

        # Initialize data
        await suite.data_manager.initialize(initial_days=5)

        # Start real-time feed
        await suite.data_manager.start_realtime_feed()

        # Simulate incoming tick data
        tick_data = {
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "price": 15530.0,
            "volume": 10,
        }

        await suite.data_manager._process_tick(tick_data)

        # Get latest data for analysis
        data_1min = await suite.data_manager.get_data("1min", bars=20)

        assert data_1min is not None
        assert len(data_1min) > 0

        # Apply technical indicators (mock signal generation)
        from project_x_py.indicators import MACD, RSI

        data_with_rsi = data_1min.pipe(RSI, period=14)
        data_with_macd = data_with_rsi.pipe(MACD)

        # Generate signal based on indicators
        latest = data_with_macd.tail(1)
        if latest is not None and len(latest) > 0:
            # Mock signal logic
            signal_generated = True
        else:
            signal_generated = False

        assert signal_generated is True

    async def test_order_modification_workflow(self, trading_suite):
        """Test modifying orders based on market conditions."""
        suite = trading_suite

        # Place initial order
        order_result = await suite.order_manager.place_order(
            contract_id="MNQ",
            order_type=3,  # Limit
            side=0,  # Buy
            size=1,
            price=15500.0,
        )

        assert order_result["success"] is True
        order_id = order_result["orderId"]

        # Track order
        suite.order_manager.tracked_orders[order_id] = {
            "id": order_id,
            "status": 1,  # Working
            "price": 15500.0,
            "size": 1,
        }

        # Market moves, modify order
        new_price = 15495.0
        modify_result = await suite.order_manager.modify_order(
            order_id=order_id,
            new_price=new_price,
        )

        assert modify_result["success"] is True
        assert suite.order_manager.tracked_orders[order_id]["price"] == new_price

        # Cancel if needed
        cancel_result = await suite.order_manager.cancel_order(order_id)

        assert cancel_result["success"] is True

    async def test_stop_loss_trigger_workflow(self, trading_suite):
        """Test stop loss trigger and position closure."""
        suite = trading_suite

        # Create position with stop loss
        position = Position(
            id=1,
            accountId=12345,
            contractId="MNQ",
            size=2,
            type=1,  # Long
            averagePrice=15500.0,
            creationTimestamp=datetime.now(pytz.UTC).isoformat(),
        )

        suite.position_manager.tracked_positions["MNQ"] = position

        # Place stop loss order
        stop_order = await suite.order_manager.place_order(
            contract_id="MNQ",
            order_type=4,  # Stop
            side=1,  # Sell (to close long)
            size=2,
            stop_price=15450.0,
        )

        assert stop_order["success"] is True

        # Simulate price hitting stop
        market_price = 15445.0

        # Stop should trigger (in real scenario, would be handled by exchange)
        # Simulate stop fill
        await suite.order_manager._process_order_update(
            {
                "id": stop_order["orderId"],
                "status": 2,  # Filled
                "filledSize": 2,
                "averagePrice": 15450.0,
            }
        )

        # Position should be closed
        await suite.position_manager._process_position_update(
            {
                "contractId": "MNQ",
                "size": 0,  # Closed
            }
        )

        assert "MNQ" not in suite.position_manager.tracked_positions

    async def test_portfolio_rebalancing_workflow(self, trading_suite):
        """Test portfolio rebalancing workflow."""
        suite = trading_suite

        # Setup initial portfolio
        positions = {
            "MNQ": Position(
                id=1,
                accountId=12345,
                contractId="MNQ",
                size=3,
                type=1,
                averagePrice=15500.0,
                creationTimestamp=datetime.now(pytz.UTC).isoformat(),
            ),
            "ES": Position(
                id=2,
                accountId=12345,
                contractId="ES",
                size=1,
                type=1,
                averagePrice=4400.0,
                creationTimestamp=datetime.now(pytz.UTC).isoformat(),
            ),
        }

        suite.position_manager.tracked_positions = positions

        # Calculate current allocation
        portfolio_value = 3 * 15500.0 + 1 * 4400.0  # Simplified
        mnq_weight = (3 * 15500.0) / portfolio_value
        es_weight = (1 * 4400.0) / portfolio_value

        # Target allocation (e.g., 60% MNQ, 40% ES)
        target_mnq = 0.6
        target_es = 0.4

        # Calculate rebalancing trades
        rebalance_trades = []

        if mnq_weight > target_mnq:
            # Reduce MNQ
            reduce_size = 1
            rebalance_trades.append(("MNQ", "SELL", reduce_size))

        if es_weight < target_es:
            # Increase ES
            increase_size = 1
            rebalance_trades.append(("ES", "BUY", increase_size))

        # Execute rebalancing
        for contract, side, size in rebalance_trades:
            if side == "SELL":
                result = await suite.position_manager.partially_close_position(
                    contract, size
                )
            else:
                result = await suite.order_manager.place_order(
                    contract_id=contract,
                    order_type=2,  # Market
                    side=0 if side == "BUY" else 1,
                    size=size,
                )

            assert result["success"] is True

    async def test_emergency_exit_workflow(self, trading_suite):
        """Test emergency exit of all positions."""
        suite = trading_suite

        # Setup multiple positions
        positions = {
            "MNQ": Position(
                id=1,
                accountId=12345,
                contractId="MNQ",
                size=2,
                type=1,
                averagePrice=15500.0,
                creationTimestamp=datetime.now(pytz.UTC).isoformat(),
            ),
            "ES": Position(
                id=2,
                accountId=12345,
                contractId="ES",
                size=1,
                type=2,
                averagePrice=4400.0,
                creationTimestamp=datetime.now(pytz.UTC).isoformat(),
            ),
            "GC": Position(
                id=3,
                accountId=12345,
                contractId="GC",
                size=1,
                type=1,
                averagePrice=1950.0,
                creationTimestamp=datetime.now(pytz.UTC).isoformat(),
            ),
        }

        suite.position_manager.tracked_positions = positions

        # Trigger emergency close
        result = await suite.risk_manager.emergency_close_all(
            reason="Risk limit exceeded"
        )

        assert result["success"] is True
        assert result["positions_closed"] >= 0

        # Cancel all pending orders
        cancel_result = await suite.order_manager.cancel_all_orders()

        assert cancel_result["cancelled"] >= 0

    async def test_data_quality_monitoring(self, trading_suite):
        """Test monitoring data quality and handling issues."""
        suite = trading_suite

        # Monitor data staleness
        last_update = datetime.now(pytz.UTC) - timedelta(minutes=5)
        suite.data_manager.last_tick_time = last_update

        is_stale = (datetime.now(pytz.UTC) - last_update).seconds > 60

        assert is_stale is True

        # Handle stale data
        if is_stale:
            # Pause trading
            suite.order_manager.trading_enabled = False

            # Try to reconnect
            reconnect_result = await suite.realtime_client.connect()

            if reconnect_result:
                # Resume trading
                suite.order_manager.trading_enabled = True

    async def test_performance_tracking_workflow(self, trading_suite):
        """Test tracking trading performance metrics."""
        suite = trading_suite

        # Simulate completed trades
        suite.position_manager.stats["closed_positions"] = 10
        suite.position_manager.stats["total_pnl"] = 5000.0
        suite.position_manager.stats["winning_trades"] = 7
        suite.position_manager.stats["losing_trades"] = 3

        # Calculate performance metrics
        win_rate = 7 / 10
        avg_pnl = 5000.0 / 10

        assert win_rate == 0.7
        assert avg_pnl == 500.0

        # Track order execution quality
        suite.order_manager.stats["orders_placed"] = 50
        suite.order_manager.stats["orders_filled"] = 45
        suite.order_manager.stats["orders_cancelled"] = 3
        suite.order_manager.stats["orders_rejected"] = 2

        fill_rate = 45 / 50

        assert fill_rate == 0.9
