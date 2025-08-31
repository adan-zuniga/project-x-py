"""Tests for ManagedTrade edge cases and concurrency scenarios."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_x_py.event_bus import EventType
from project_x_py.models import BracketOrderResponse
from project_x_py.risk_manager.core import RiskManager
from project_x_py.risk_manager.managed_trade import ManagedTrade
from project_x_py.types import OrderSide, OrderStatus, OrderType


@pytest.mark.asyncio
class TestManagedTradeEdgeCases:
    """Test ManagedTrade edge cases and concurrency scenarios."""

    @pytest.fixture
    async def setup_managed_trade(self):
        """Create a ManagedTrade instance for edge case testing."""
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
            )
            risk_manager.set_position_manager(mock_position_manager)
            risk_manager._init_task = MagicMock()

        # Create managed trade
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

    async def test_concurrent_entry_prevention(self, setup_managed_trade):
        """Test that concurrent entries are prevented properly."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Set up an existing entry order
        entry_order = MagicMock()
        entry_order.id = 123
        trade._entry_order = entry_order

        # Try to enter long while already having an entry order
        with pytest.raises(ValueError, match="Trade already has entry order"):
            await trade.enter_long()

        # Same for short
        with pytest.raises(ValueError, match="Trade already has entry order"):
            await trade.enter_short(stop_loss=20050.0)

    async def test_websocket_disconnection_during_fill_wait(self, setup_managed_trade):
        """Test behavior when WebSocket disconnects during order fill waiting."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Mock order
        order = MagicMock()
        order.id = 123

        # Mock event bus to simulate connection loss
        fill_event_triggered = False

        async def mock_on_handler(*args):
            # Simulate connection dropping after handler is set up
            nonlocal fill_event_triggered
            await asyncio.sleep(0.1)
            # Don't trigger fill event to simulate disconnection

        mocks["event_bus"].on = AsyncMock(side_effect=mock_on_handler)
        mocks["event_bus"].remove_callback = AsyncMock()

        # Should timeout when no fill event is received
        result = await trade._wait_for_order_fill(order, timeout_seconds=0.2)
        assert result is False

    async def test_multiple_partial_fills_handling(self, setup_managed_trade):
        """Test handling of multiple partial fills."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Mock risk validation
        mocks["risk_manager"].validate_trade = AsyncMock(
            return_value={"is_valid": True, "reasons": []}
        )

        # Mock order placement
        order_result = MagicMock()
        order_result.success = True
        order_result.orderId = 123
        mocks["order_manager"].place_market_order = AsyncMock(return_value=order_result)

        # Mock entry order with partial fills
        entry_order = MagicMock()
        entry_order.id = 123
        entry_order.size = 3
        entry_order.filled_quantity = 1  # Only partially filled initially
        entry_order.status = 3  # Partially filled status

        mocks["order_manager"].search_open_orders = AsyncMock(return_value=[entry_order])
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[])

        # Enter trade
        result = await trade.enter_long(size=3, stop_loss=19950.0)

        # Should detect partial fill
        assert not trade.is_filled()  # Should not be considered fully filled

        # Simulate full fill
        entry_order.filled_quantity = 3
        entry_order.status = 2  # Filled
        assert trade.is_filled()  # Now should be fully filled

    async def test_order_state_race_conditions(self, setup_managed_trade):
        """Test race conditions in order state updates."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Create scenario where order states change rapidly
        order = MagicMock()
        order.id = 123

        # Simulate rapid state changes in polling
        order_states = [
            {"is_filled": False, "is_terminal": False},  # Working
            {"is_filled": False, "is_terminal": False},  # Still working
            {"is_filled": True, "is_terminal": True},   # Filled
        ]

        call_count = 0
        def mock_search_with_state_changes():
            nonlocal call_count
            state = order_states[min(call_count, len(order_states) - 1)]
            call_count += 1

            updated_order = MagicMock()
            updated_order.id = 123
            updated_order.is_filled = state["is_filled"]
            updated_order.is_terminal = state["is_terminal"]
            return [updated_order]

        mocks["order_manager"].search_open_orders = AsyncMock(side_effect=mock_search_with_state_changes)
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[])

        # Should eventually detect fill (needs at least 1.5 seconds for 3 polling cycles)
        result = await trade._poll_for_order_fill(order, timeout_seconds=2)
        assert result is True

    async def test_market_price_gaps_and_slippage(self, setup_managed_trade):
        """Test handling of market price gaps and slippage."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Mock significant price gaps between data requests
        price_sequence = [20000.0, 19800.0, 20300.0]  # Large gaps
        price_index = 0

        def mock_get_data_with_gaps(timeframe, bars):
            nonlocal price_index
            if price_index < len(price_sequence):
                import polars as pl
                price = price_sequence[price_index]
                price_index += 1
                return pl.DataFrame({"close": [price]})
            return None

        mocks["data_manager"].get_data = AsyncMock(side_effect=mock_get_data_with_gaps)

        # Should handle price gaps without errors
        price1 = await trade._get_market_price()
        assert price1 == 20000.0

        price2 = await trade._get_market_price()
        assert price2 == 19800.0  # Large gap down

        price3 = await trade._get_market_price()
        assert price3 == 20300.0  # Large gap up

    async def test_event_handler_memory_leaks_prevention(self, setup_managed_trade):
        """Test that event handlers are properly cleaned up to prevent memory leaks."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        order = MagicMock()
        order.id = 123

        # Track handler registrations and removals
        registered_handlers = []
        removed_handlers = []

        async def mock_on(event_type, handler):
            registered_handlers.append((event_type, handler))

        async def mock_remove_callback(event_type, handler):
            removed_handlers.append((event_type, handler))

        mocks["event_bus"].on = mock_on
        mocks["event_bus"].remove_callback = mock_remove_callback

        # Wait for fill with timeout
        result = await trade._wait_for_order_fill(order, timeout_seconds=0.1)

        # Should have registered 3 handlers (FILLED, CANCELLED, REJECTED)
        assert len(registered_handlers) == 3

        # Should have removed all registered handlers
        assert len(removed_handlers) == 3

        # Verify all event types are handled
        event_types = {reg[0] for reg in registered_handlers}
        expected_types = {EventType.ORDER_FILLED, EventType.ORDER_CANCELLED, EventType.ORDER_REJECTED}
        assert event_types == expected_types

    async def test_high_frequency_order_updates(self, setup_managed_trade):
        """Test handling of high-frequency order updates."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        order = MagicMock()
        order.id = 123

        # Simulate frequent order updates (limited by polling interval)
        update_count = 0
        max_updates = 8  # Realistic for 5-second timeout with 0.5s polling interval

        def mock_frequent_updates():
            nonlocal update_count
            update_count += 1

            updated_order = MagicMock()
            updated_order.id = 123

            # Fill after many updates
            if update_count >= max_updates:
                updated_order.is_filled = True
                updated_order.is_terminal = True
            else:
                updated_order.is_filled = False
                updated_order.is_terminal = False

            return [updated_order]

        mocks["order_manager"].search_open_orders = AsyncMock(side_effect=mock_frequent_updates)
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[])

        # Should handle high-frequency updates efficiently
        start_time = asyncio.get_event_loop().time()
        result = await trade._poll_for_order_fill(order, timeout_seconds=5)
        end_time = asyncio.get_event_loop().time()

        assert result is True
        assert update_count >= max_updates
        # Should complete within reasonable time (8 polls * 0.5s + overhead = ~4.5s max)
        assert (end_time - start_time) < 5.0

    async def test_complex_bracket_order_lifecycle(self, setup_managed_trade):
        """Test complex bracket order lifecycle with various scenarios."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Mock comprehensive setup for bracket order
        mocks["risk_manager"].validate_trade = AsyncMock(
            return_value={"is_valid": True, "reasons": []}
        )

        # Mock entry order placement
        entry_result = MagicMock()
        entry_result.success = True
        entry_result.orderId = 123
        mocks["order_manager"].place_market_order = AsyncMock(return_value=entry_result)

        # Mock entry order
        entry_order = MagicMock()
        entry_order.id = 123

        # Mock position
        position = MagicMock()
        position.contractId = "MNQ"
        position.is_long = True
        position.size = 2

        # Mock bracket response with both stop and target
        bracket_response = BracketOrderResponse(
            success=True,
            entry_order_id=None,
            stop_order_id=124,
            target_order_id=125,
            entry_price=20000.0,
            stop_loss_price=19950.0,
            take_profit_price=20100.0,
            entry_response=None,
            stop_response=MagicMock(),
            target_response=MagicMock(),
            error_message=None,
        )

        mocks["risk_manager"].attach_risk_orders = AsyncMock(
            return_value={"bracket_order": bracket_response}
        )

        # Mock stop and target orders
        stop_order = MagicMock()
        stop_order.id = 124
        target_order = MagicMock()
        target_order.id = 125

        # Mock order searches returning different orders
        search_call_count = 0
        def mock_order_search():
            nonlocal search_call_count
            search_call_count += 1
            if search_call_count == 1:
                return [entry_order]  # Entry order search
            elif search_call_count == 2:
                return [stop_order]   # Stop order search
            else:
                return [target_order] # Target order search

        mocks["order_manager"].search_open_orders = AsyncMock(side_effect=mock_order_search)
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[position])

        # Wait for fill simulation
        trade._wait_for_order_fill = AsyncMock(return_value=True)

        # Execute bracket order
        result = await trade.enter_long(
            size=2,
            stop_loss=19950.0,
            take_profit=20100.0
        )

        # Verify all components are set up
        assert result["entry_order"] == entry_order
        assert trade._stop_order == stop_order
        assert trade._target_order == target_order
        assert trade._positions[0] == position

    async def test_network_interruption_recovery(self, setup_managed_trade):
        """Test recovery from network interruptions during operations."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        order = MagicMock()
        order.id = 123

        # Simulate network failures followed by recovery
        call_count = 0
        def mock_network_issues():
            nonlocal call_count
            call_count += 1

            if call_count <= 3:
                # First few calls fail due to network
                raise ConnectionError("Network unavailable")
            else:
                # Network recovers
                updated_order = MagicMock()
                updated_order.id = 123
                updated_order.is_filled = True
                return [updated_order]

        mocks["order_manager"].search_open_orders = AsyncMock(side_effect=mock_network_issues)
        mocks["position_manager"].get_all_positions = AsyncMock(return_value=[])

        # Should eventually succeed after network recovery
        result = await trade._poll_for_order_fill(order, timeout_seconds=3)
        assert result is True
        assert call_count > 3  # Should have retried multiple times

    async def test_emergency_exit_during_active_operations(self, setup_managed_trade):
        """Test emergency exit while other operations are in progress."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Set up active orders and positions
        entry_order = MagicMock()
        entry_order.id = 123
        stop_order = MagicMock()
        stop_order.id = 124
        target_order = MagicMock()
        target_order.id = 125

        trade._orders = [entry_order, stop_order, target_order]

        position = MagicMock()
        trade._positions = [position]

        # Mock close position
        trade.close_position = AsyncMock(return_value={"success": True})

        # Emergency exit should succeed even with multiple active orders
        result = await trade.emergency_exit()
        assert result is True

        # Should have attempted to cancel all orders
        assert mocks["order_manager"].cancel_order.call_count == 3

        # Should have closed position
        trade.close_position.assert_called_once()

    async def test_trailing_stop_with_volatile_market(self, setup_managed_trade):
        """Test trailing stop behavior in volatile market conditions."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Set up position and stop order
        position = MagicMock()
        position.is_long = True
        position.size = 2
        trade._positions = [position]

        stop_order = MagicMock()
        stop_order.stopPrice = 19950.0
        trade._stop_order = stop_order

        # Simulate volatile price movements
        volatile_prices = [
            20000.0, 20050.0, 19980.0, 20100.0, 20020.0, 20150.0, 20080.0
        ]

        price_index = 0
        def mock_volatile_price():
            nonlocal price_index
            if price_index < len(volatile_prices):
                price = volatile_prices[price_index]
                price_index += 1
                return price
            return 20080.0  # Final price

        trade._get_current_market_price = AsyncMock(side_effect=mock_volatile_price)
        trade.adjust_stop_loss = AsyncMock(return_value=True)

        # Set moderate risk amount
        trade._risk_amount = 100

        # Test multiple trailing stop checks
        results = []
        for _ in range(len(volatile_prices)):
            result = await trade.check_trailing_stop()
            results.append(result)

        # Should have made some adjustments during volatile periods
        assert any(results)  # At least some adjustments should have been made
        assert trade._get_current_market_price.call_count == len(volatile_prices)

    async def test_concurrent_scale_operations(self, setup_managed_trade):
        """Test concurrent scaling operations."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Enable scaling
        mocks["risk_manager"].config.scale_in_enabled = True
        mocks["risk_manager"].config.scale_out_enabled = True

        # Set up position
        position = MagicMock()
        position.is_long = True
        position.size = 5
        trade._positions = [position]

        # Mock order placements
        scale_in_result = MagicMock()
        scale_in_result.success = True
        scale_in_result.orderId = 126

        scale_out_result = MagicMock()
        scale_out_result.success = True
        scale_out_result.orderId = 127

        mocks["order_manager"].place_market_order = AsyncMock(
            side_effect=[scale_in_result, scale_out_result]
        )

        # Mock order searches
        scale_in_order = MagicMock()
        scale_in_order.id = 126
        scale_out_order = MagicMock()
        scale_out_order.id = 127

        call_count = 0
        def mock_order_search():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [scale_in_order]
            else:
                return [scale_out_order]

        mocks["order_manager"].search_open_orders = AsyncMock(side_effect=mock_order_search)

        # Execute concurrent scale operations
        scale_in_task = asyncio.create_task(trade.scale_in(2))
        scale_out_task = asyncio.create_task(trade.scale_out(1))

        scale_in_result, scale_out_result = await asyncio.gather(
            scale_in_task, scale_out_task
        )

        # Both operations should succeed
        assert scale_in_result["new_position_size"] == 7  # 5 + 2
        assert scale_out_result["remaining_size"] == 4   # 5 - 1

    async def test_data_manager_timeout_handling(self, setup_managed_trade):
        """Test handling of data manager timeouts."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Mock data manager to timeout on first few calls
        call_count = 0
        async def mock_timeout_then_success(timeframe, bars):
            nonlocal call_count
            call_count += 1

            if call_count <= 2:
                await asyncio.sleep(1)  # Simulate timeout
                raise asyncio.TimeoutError("Data request timeout")
            else:
                import polars as pl
                return pl.DataFrame({"close": [20000.0]})

        mocks["data_manager"].get_data = AsyncMock(side_effect=mock_timeout_then_success)

        # Should eventually get price after retries
        price = await trade._get_market_price()
        assert price == 20000.0
        assert call_count > 2  # Should have retried

    async def test_position_updates_during_monitoring(self, setup_managed_trade):
        """Test position updates during monitoring operations."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Mock position that changes during monitoring
        positions_sequence = [
            # Position exists initially
            [MagicMock(contractId="MNQ", size=2, unrealized=50.0)],
            # Position size changes
            [MagicMock(contractId="MNQ", size=3, unrealized=75.0)],
            # Position closed
            [],
        ]

        call_count = 0
        def mock_changing_positions():
            nonlocal call_count
            if call_count < len(positions_sequence):
                positions = positions_sequence[call_count]
                call_count += 1
                return positions
            return []

        mocks["position_manager"].get_all_positions = AsyncMock(side_effect=mock_changing_positions)

        # Monitor position changes (clear cache to force fresh data each time)
        results = []
        for _ in range(len(positions_sequence)):
            trade._positions = []  # Clear cache to get fresh data
            result = await trade.monitor_position()
            results.append(result)

        # Should track position changes
        assert results[0]["size"] == 2
        assert results[1]["size"] == 3
        assert results[2]["size"] == 0  # Position closed

    async def test_order_modification_race_conditions(self, setup_managed_trade):
        """Test order modification race conditions."""
        mocks = setup_managed_trade
        trade = mocks["trade"]

        # Set up stop order
        stop_order = MagicMock()
        stop_order.id = 123
        trade._stop_order = stop_order

        # Mock order modification with intermittent failures
        def mock_modify_order(*args, **kwargs):
            # Alternating success/failure pattern
            call_idx = mock_modify_order.call_count
            mock_modify_order.call_count += 1
            if call_idx % 2 == 0:  # Even calls fail
                raise Exception("Modification failed")
            return True  # Odd calls succeed

        mock_modify_order.call_count = 0
        mocks["order_manager"].modify_order = AsyncMock(side_effect=mock_modify_order)

        # Try multiple modifications
        results = []
        for new_price in [19940.0, 19930.0, 19920.0, 19910.0]:
            result = await trade.adjust_stop_loss(new_price)
            results.append(result)

        # Should have some successes and failures based on mock
        assert results == [False, True, False, True]
        assert mocks["order_manager"].modify_order.call_count == 4
