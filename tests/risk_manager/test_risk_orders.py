"""Comprehensive tests for RiskManager order attachment and management following TDD methodology.

Tests define the EXPECTED behavior, not current implementation.
If tests fail, we fix the implementation, not the tests.
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch

import pytest

from project_x_py.event_bus import EventBus
from project_x_py.models import (
    Account,
    BracketOrderResponse,
    Instrument,
    Order,
    Position,
)
from project_x_py.risk_manager import RiskConfig, RiskManager
from project_x_py.types import OrderSide, OrderStatus, OrderType


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
    client.get_instrument = AsyncMock(return_value=Instrument(
        id="MNQ",
        name="Micro E-mini Nasdaq",
        description="Micro E-mini Nasdaq futures",
        tickSize=0.25,
        tickValue=5.0,
        activeContract=True
    ))
    return client


@pytest.fixture
def mock_order_manager():
    """Create a mock OrderManager."""
    om = MagicMock()
    om.search_open_orders = AsyncMock(return_value=[])
    om.place_stop_order = AsyncMock()
    om.place_limit_order = AsyncMock()
    om.modify_order = AsyncMock(return_value=True)
    return om


@pytest.fixture
def mock_position():
    """Create a mock Position."""
    position = MagicMock(spec=Position)
    position.id = 1
    position.contractId = "MNQ"
    position.averagePrice = 15000.0
    position.size = 2
    position.netQuantity = 2
    position.is_long = True
    return position


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBus."""
    bus = MagicMock(spec=EventBus)
    bus.emit = AsyncMock()
    return bus


@pytest.fixture
def mock_data_manager():
    """Create a mock DataManager."""
    dm = MagicMock()
    dm.get_data = AsyncMock(return_value=None)
    return dm


@pytest.fixture
async def risk_manager(mock_client, mock_order_manager, mock_event_bus, mock_data_manager):
    """Create a RiskManager instance for testing."""
    rm = RiskManager(
        project_x=mock_client,
        order_manager=mock_order_manager,
        event_bus=mock_event_bus,
        config=RiskConfig(),
        data_manager=mock_data_manager
    )

    # Wait for initialization
    if hasattr(rm, '_init_task'):
        try:
            await asyncio.wait_for(rm._init_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass

    return rm


class TestAttachRiskOrders:
    """Test risk order attachment to positions."""

    @pytest.mark.asyncio
    async def test_attach_stop_loss_to_long_position(self, risk_manager, mock_position, mock_order_manager):
        """Test attaching stop loss to a long position."""
        # Setup
        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100
        mock_order_manager.place_stop_order.return_value = stop_response

        # Execute
        result = await risk_manager.attach_risk_orders(
            position=mock_position,
            stop_loss=14950.0
        )

        # Verify
        assert result["position_id"] == mock_position.id
        assert result["stop_loss"] == 14950.0
        assert result["bracket_order"].stop_order_id == 100

        # Verify correct order placement
        mock_order_manager.place_stop_order.assert_called_once_with(
            contract_id="MNQ",
            side=OrderSide.SELL,  # Opposite side for exit
            size=2,
            stop_price=14950.0
        )

    @pytest.mark.asyncio
    async def test_attach_take_profit_to_long_position(self, risk_manager, mock_position, mock_order_manager):
        """Test attaching take profit to a long position."""
        # Setup
        target_response = MagicMock()
        target_response.success = True
        target_response.orderId = 101
        mock_order_manager.place_limit_order.return_value = target_response

        # Execute
        result = await risk_manager.attach_risk_orders(
            position=mock_position,
            take_profit=15100.0
        )

        # Verify
        assert result["take_profit"] == 15100.0
        assert result["bracket_order"].target_order_id == 101

        # Verify correct order placement
        mock_order_manager.place_limit_order.assert_called_once_with(
            contract_id="MNQ",
            side=OrderSide.SELL,  # Opposite side for exit
            size=2,
            limit_price=15100.0
        )

    @pytest.mark.asyncio
    async def test_attach_both_stop_and_target(self, risk_manager, mock_position, mock_order_manager):
        """Test attaching both stop loss and take profit."""
        # Setup
        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100

        target_response = MagicMock()
        target_response.success = True
        target_response.orderId = 101

        mock_order_manager.place_stop_order.return_value = stop_response
        mock_order_manager.place_limit_order.return_value = target_response

        # Execute
        result = await risk_manager.attach_risk_orders(
            position=mock_position,
            stop_loss=14950.0,
            take_profit=15100.0
        )

        # Verify both orders placed
        assert result["stop_loss"] == 14950.0
        assert result["take_profit"] == 15100.0
        assert result["bracket_order"].stop_order_id == 100
        assert result["bracket_order"].target_order_id == 101

        # Verify both order calls
        assert mock_order_manager.place_stop_order.call_count == 1
        assert mock_order_manager.place_limit_order.call_count == 1

    @pytest.mark.asyncio
    async def test_attach_orders_to_short_position(self, risk_manager, mock_order_manager):
        """Test attaching risk orders to a short position."""
        # Setup short position
        short_position = MagicMock(spec=Position)
        short_position.id = 2
        short_position.contractId = "MNQ"
        short_position.averagePrice = 15000.0
        short_position.size = 2
        short_position.is_long = False  # Short position

        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100
        mock_order_manager.place_stop_order.return_value = stop_response

        # Execute
        result = await risk_manager.attach_risk_orders(
            position=short_position,
            stop_loss=15050.0  # Stop above entry for short
        )

        # Verify opposite side order for short position
        mock_order_manager.place_stop_order.assert_called_once_with(
            contract_id="MNQ",
            side=OrderSide.BUY,  # Buy to cover short
            size=2,
            stop_price=15050.0
        )

    @pytest.mark.asyncio
    async def test_auto_calculate_stop_loss_fixed(self, risk_manager, mock_position, mock_order_manager):
        """Test automatic stop loss calculation with fixed distance."""
        # Setup
        risk_manager.config.use_stop_loss = True
        risk_manager.config.stop_loss_type = "fixed"
        risk_manager.config.default_stop_distance = Decimal("50")

        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100
        mock_order_manager.place_stop_order.return_value = stop_response

        # Execute without providing stop_loss
        result = await risk_manager.attach_risk_orders(position=mock_position)

        # Verify auto-calculated stop
        expected_stop = 15000.0 - (50 * 0.25)  # entry - (distance * tick_size)
        assert result["stop_loss"] == expected_stop

        # Verify order placed with calculated stop
        mock_order_manager.place_stop_order.assert_called_once()
        call_args = mock_order_manager.place_stop_order.call_args
        assert call_args.kwargs["stop_price"] == expected_stop

    @pytest.mark.asyncio
    async def test_auto_calculate_stop_loss_percentage(self, risk_manager, mock_position, mock_order_manager):
        """Test automatic stop loss calculation with percentage."""
        # Setup
        risk_manager.config.use_stop_loss = True
        risk_manager.config.stop_loss_type = "percentage"
        risk_manager.config.default_stop_distance = Decimal("1")  # 1%

        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100
        mock_order_manager.place_stop_order.return_value = stop_response

        # Execute
        result = await risk_manager.attach_risk_orders(position=mock_position)

        # Verify percentage-based stop
        expected_stop = 15000.0 * (1 - 0.01)  # 1% below entry
        assert result["stop_loss"] == expected_stop

    @pytest.mark.asyncio
    async def test_auto_calculate_take_profit_from_stop(self, risk_manager, mock_position, mock_order_manager):
        """Test automatic take profit calculation based on risk/reward ratio."""
        # Setup
        risk_manager.config.use_stop_loss = True
        risk_manager.config.use_take_profit = True
        risk_manager.config.default_risk_reward_ratio = Decimal("2.0")

        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100

        target_response = MagicMock()
        target_response.success = True
        target_response.orderId = 101

        mock_order_manager.place_stop_order.return_value = stop_response
        mock_order_manager.place_limit_order.return_value = target_response

        # Execute with explicit stop
        result = await risk_manager.attach_risk_orders(
            position=mock_position,
            stop_loss=14950.0  # 50 points risk
        )

        # Verify take profit based on R:R ratio
        risk = 15000.0 - 14950.0  # 50 points
        expected_target = 15000.0 + (risk * 2)  # 2:1 R:R
        assert result["take_profit"] == expected_target
        assert result["risk_reward_ratio"] == 2.0

    @pytest.mark.asyncio
    async def test_trailing_stop_setup(self, risk_manager, mock_position, mock_order_manager):
        """Test trailing stop monitoring setup."""
        # Setup
        risk_manager.config.use_trailing_stops = True
        risk_manager.config.trailing_stop_distance = Decimal("20")
        risk_manager.config.trailing_stop_trigger = Decimal("30")

        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100
        mock_order_manager.place_stop_order.return_value = stop_response

        # Execute
        result = await risk_manager.attach_risk_orders(
            position=mock_position,
            stop_loss=14950.0,
            use_trailing=True
        )

        # Verify trailing stop configuration
        assert result["use_trailing"] is True

        # Verify trailing stop task was created
        assert str(mock_position.id) in risk_manager._trailing_stop_tasks

        # Clean up the task
        task = risk_manager._trailing_stop_tasks[str(mock_position.id)]
        task.cancel()
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_event_emission_on_order_attachment(self, risk_manager, mock_position, mock_order_manager, mock_event_bus):
        """Test that events are emitted when risk orders are attached."""
        # Setup
        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100
        mock_order_manager.place_stop_order.return_value = stop_response

        # Execute
        await risk_manager.attach_risk_orders(
            position=mock_position,
            stop_loss=14950.0
        )

        # Verify event was emitted
        mock_event_bus.emit.assert_called_once()
        event_name = mock_event_bus.emit.call_args[0][0]
        event_data = mock_event_bus.emit.call_args[0][1]

        assert event_name == "risk_orders_placed"
        assert event_data["position"] == mock_position
        assert event_data["stop_loss"] == 14950.0


class TestAdjustStops:
    """Test stop loss adjustment functionality."""

    @pytest.mark.asyncio
    async def test_adjust_stop_with_order_id(self, risk_manager, mock_position, mock_order_manager):
        """Test adjusting stop loss with specific order ID."""
        # Execute
        success = await risk_manager.adjust_stops(
            position=mock_position,
            new_stop=14975.0,
            order_id="100"
        )

        # Verify
        assert success is True
        mock_order_manager.modify_order.assert_called_once_with(
            order_id=100,
            stop_price=14975.0
        )

    @pytest.mark.asyncio
    async def test_adjust_stop_find_existing_order(self, risk_manager, mock_position, mock_order_manager):
        """Test adjusting stop loss by finding existing stop order."""
        # Setup existing stop order
        stop_order = MagicMock(spec=Order)
        stop_order.id = 100
        stop_order.contractId = "MNQ"
        stop_order.type = 4  # STOP order type
        stop_order.side = OrderSide.SELL.value  # Opposite of long position

        mock_order_manager.search_open_orders.return_value = [stop_order]

        # Execute without order_id
        success = await risk_manager.adjust_stops(
            position=mock_position,
            new_stop=14975.0
        )

        # Verify found and modified correct order
        assert success is True
        mock_order_manager.modify_order.assert_called_once_with(
            order_id=100,
            stop_price=14975.0
        )

    @pytest.mark.asyncio
    async def test_adjust_stop_no_existing_order(self, risk_manager, mock_position, mock_order_manager):
        """Test adjusting stop when no stop order exists."""
        # Setup - no stop orders
        mock_order_manager.search_open_orders.return_value = []

        # Execute
        success = await risk_manager.adjust_stops(
            position=mock_position,
            new_stop=14975.0
        )

        # Verify returns False when no order found
        assert success is False
        mock_order_manager.modify_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_adjust_stop_modification_fails(self, risk_manager, mock_position, mock_order_manager):
        """Test handling when stop adjustment fails."""
        # Setup
        mock_order_manager.modify_order.return_value = False

        # Execute
        success = await risk_manager.adjust_stops(
            position=mock_position,
            new_stop=14975.0,
            order_id="100"
        )

        # Verify returns False on modification failure
        assert success is False

    @pytest.mark.asyncio
    async def test_adjust_stop_emits_event(self, risk_manager, mock_position, mock_order_manager, mock_event_bus):
        """Test that event is emitted on successful stop adjustment."""
        # Execute
        await risk_manager.adjust_stops(
            position=mock_position,
            new_stop=14975.0,
            order_id="100"
        )

        # Verify event emitted
        mock_event_bus.emit.assert_called_once()
        event_name = mock_event_bus.emit.call_args[0][0]
        event_data = mock_event_bus.emit.call_args[0][1]

        assert event_name == "stop_adjusted"
        assert event_data["position"] == mock_position
        assert event_data["new_stop"] == 14975.0
        assert event_data["order_id"] == "100"


class TestTrailingStopMonitoring:
    """Test trailing stop monitoring functionality."""

    @pytest.mark.asyncio
    async def test_should_activate_trailing_stop_long(self, risk_manager):
        """Test trailing stop activation logic for long positions."""
        risk_manager.config.use_trailing_stops = True
        risk_manager.config.trailing_stop_trigger = Decimal("30")

        # Test activation when profit exceeds trigger
        should_activate = await risk_manager.should_activate_trailing_stop(
            entry_price=15000.0,
            current_price=15035.0,  # 35 points profit
            side=OrderSide.BUY
        )
        assert should_activate is True

        # Test no activation when profit below trigger
        should_activate = await risk_manager.should_activate_trailing_stop(
            entry_price=15000.0,
            current_price=15025.0,  # 25 points profit
            side=OrderSide.BUY
        )
        assert should_activate is False

    @pytest.mark.asyncio
    async def test_should_activate_trailing_stop_short(self, risk_manager):
        """Test trailing stop activation logic for short positions."""
        risk_manager.config.use_trailing_stops = True
        risk_manager.config.trailing_stop_trigger = Decimal("30")

        # Test activation for short position
        should_activate = await risk_manager.should_activate_trailing_stop(
            entry_price=15000.0,
            current_price=14965.0,  # 35 points profit for short
            side=OrderSide.SELL
        )
        assert should_activate is True

    @pytest.mark.asyncio
    async def test_calculate_trailing_stop_price(self, risk_manager):
        """Test trailing stop price calculation."""
        risk_manager.config.trailing_stop_distance = Decimal("20")

        # Test for long position
        stop_price = risk_manager.calculate_trailing_stop(
            current_price=15050.0,
            side=OrderSide.BUY
        )
        assert stop_price == 15050.0 - 20  # Trail by 20 points

        # Test for short position
        stop_price = risk_manager.calculate_trailing_stop(
            current_price=14950.0,
            side=OrderSide.SELL
        )
        assert stop_price == 14950.0 + 20  # Trail by 20 points

    @pytest.mark.asyncio
    async def test_stop_trailing_stop_for_position(self, risk_manager):
        """Test stopping trailing stop monitoring for specific position."""
        # Setup a mock task using asyncio's Future for proper async behavior
        import asyncio
        mock_task = asyncio.create_task(asyncio.sleep(10))

        risk_manager._trailing_stop_tasks["1"] = mock_task
        risk_manager._active_tasks.add(mock_task)

        # Execute
        await risk_manager.stop_trailing_stops(position_id="1")

        # Verify task cancelled
        assert mock_task.cancelled()
        assert "1" not in risk_manager._trailing_stop_tasks

    @pytest.mark.asyncio
    async def test_stop_all_trailing_stops(self, risk_manager):
        """Test stopping all trailing stop monitoring."""
        # Setup multiple tasks using real asyncio tasks
        import asyncio
        mock_task1 = asyncio.create_task(asyncio.sleep(10))
        mock_task2 = asyncio.create_task(asyncio.sleep(10))

        risk_manager._trailing_stop_tasks = {"1": mock_task1, "2": mock_task2}

        # Execute
        await risk_manager.stop_trailing_stops()

        # Verify all tasks cancelled
        assert mock_task1.cancelled()
        assert mock_task2.cancelled()
        assert len(risk_manager._trailing_stop_tasks) == 0


class TestRiskOrderEdgeCases:
    """Test edge cases in risk order management."""

    @pytest.mark.asyncio
    async def test_attach_orders_with_atr_stop_no_data(self, risk_manager, mock_position, mock_order_manager):
        """Test ATR stop calculation fallback when no data available."""
        # Setup
        risk_manager.config.use_stop_loss = True
        risk_manager.config.stop_loss_type = "atr"
        risk_manager.config.default_stop_distance = Decimal("50")

        # Data manager returns no data
        risk_manager.data_manager.get_data.return_value = None

        stop_response = MagicMock()
        stop_response.success = True
        stop_response.orderId = 100
        mock_order_manager.place_stop_order.return_value = stop_response

        # Execute
        result = await risk_manager.attach_risk_orders(position=mock_position)

        # Should fall back to fixed stop distance
        expected_stop = 15000.0 - (50 * 0.25)
        assert result["stop_loss"] == expected_stop

    @pytest.mark.asyncio
    async def test_attach_orders_order_placement_fails(self, risk_manager, mock_position, mock_order_manager):
        """Test handling when order placement fails."""
        # Setup
        stop_response = MagicMock()
        stop_response.success = False
        stop_response.orderId = None
        mock_order_manager.place_stop_order.return_value = stop_response

        target_response = MagicMock()
        target_response.success = True
        target_response.orderId = 101
        mock_order_manager.place_limit_order.return_value = target_response

        # Execute
        result = await risk_manager.attach_risk_orders(
            position=mock_position,
            stop_loss=14950.0,
            take_profit=15100.0
        )

        # Verify correct handling of partial failures
        assert result["bracket_order"].stop_order_id is None
        assert result["bracket_order"].success is False  # Correctly False when stop fails
        assert result["bracket_order"].target_order_id == 101
        assert result["bracket_order"].error_message == "One or more risk orders failed to place"

    @pytest.mark.asyncio
    async def test_cleanup_trailing_stop_tasks(self, risk_manager):
        """Test cleanup of trailing stop tasks on shutdown."""
        # Setup tasks using real asyncio task
        import asyncio
        mock_task = asyncio.create_task(asyncio.sleep(10))

        risk_manager._trailing_stop_tasks["1"] = mock_task
        risk_manager._active_tasks.add(mock_task)

        # Execute cleanup
        await risk_manager.cleanup()

        # Verify all tasks cancelled
        assert mock_task.cancelled()
        assert len(risk_manager._trailing_stop_tasks) == 0
        assert len(risk_manager._active_tasks) == 0
