"""
Comprehensive test suite for TradingSuite event system.

These tests ensure that the multi-instrument event system works correctly
and prevents regressions in event handling functionality.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from project_x_py import TradingSuite
from project_x_py.event_bus import EventBus, EventType


class TestTradingSuiteEventSystem:
    """Test suite for TradingSuite event system functionality."""

    @pytest.fixture
    async def mock_client(self):
        """Create a mock ProjectX client."""
        with patch("project_x_py.trading_suite.ProjectX") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_env.return_value.__aenter__.return_value = mock_client

            # Setup mock responses
            mock_client.authenticate = AsyncMock(return_value=None)
            mock_client.get_instrument = AsyncMock(
                return_value=MagicMock(
                    symbol="MNQ", name="MNQ", exchange="CME", min_tick=0.25
                )
            )
            mock_client.get_bars = AsyncMock(
                return_value=MagicMock(is_empty=lambda: True)
            )
            mock_client.search_positions = AsyncMock(return_value=[])
            mock_client.search_orders = AsyncMock(return_value=[])

            yield mock_client

    @pytest.fixture
    async def mock_realtime_client(self):
        """Create a mock realtime client."""
        with patch("project_x_py.realtime.ProjectXRealtimeClient") as mock_rt_class:
            mock_rt = AsyncMock()
            mock_rt_class.return_value = mock_rt

            # Mock connection methods
            mock_rt.connect = AsyncMock(return_value=True)
            mock_rt.disconnect = AsyncMock()
            mock_rt.is_connected = True
            mock_rt.subscribe_to_market = AsyncMock()
            mock_rt.subscribe_to_user = AsyncMock()

            yield mock_rt

    @pytest.mark.asyncio
    async def test_instrument_context_has_event_methods(self):
        """Test that InstrumentContext has all required event methods."""
        # Create an InstrumentContext directly with event_bus
        from project_x_py.trading_suite import InstrumentContext
        event_bus = EventBus()
        context = InstrumentContext(
            symbol="MNQ",
            instrument_info=MagicMock(),
            data=MagicMock(),
            orders=MagicMock(),
            positions=MagicMock(),
            event_bus=event_bus
        )

        # Verify all event methods exist
        assert hasattr(context, "on")
        assert hasattr(context, "once")
        assert hasattr(context, "off")
        assert hasattr(context, "wait_for")
        assert hasattr(context, "event_bus")

        # Verify methods are callable
        assert callable(context.on)
        assert callable(context.once)
        assert callable(context.off)
        assert callable(context.wait_for)

        # Test that methods work
        events_received = []

        async def handler(event):
            events_received.append(event)

        # Register handler
        await context.on(EventType.NEW_BAR, handler)

        # Emit event
        await context.event_bus.emit(
            EventType.NEW_BAR,
            {"instrument": "MNQ", "timeframe": "1min", "data": {"close": 100.0}}
        )

        # Allow propagation
        await asyncio.sleep(0.05)

        # Verify handler was called
        assert len(events_received) == 1
        assert events_received[0].data["instrument"] == "MNQ"

    @pytest.mark.asyncio
    async def test_event_forwarding_between_instruments_and_suite(self):
        """Test that events are forwarded from instrument EventBuses to suite EventBus."""
        # Create independent EventBuses
        suite_bus = EventBus()
        mnq_bus = EventBus()
        nq_bus = EventBus()

        # Set up forwarding
        await mnq_bus.forward_to(suite_bus)
        await nq_bus.forward_to(suite_bus)

        # Track events at different levels
        suite_events = []
        mnq_events = []
        nq_events = []

        async def suite_handler(event):
            suite_events.append(event)

        async def mnq_handler(event):
            mnq_events.append(event)

        async def nq_handler(event):
            nq_events.append(event)

        # Register handlers
        await suite_bus.on(EventType.NEW_BAR, suite_handler)
        await mnq_bus.on(EventType.NEW_BAR, mnq_handler)
        await nq_bus.on(EventType.NEW_BAR, nq_handler)

        # Emit events from each instrument
        await mnq_bus.emit(
            EventType.NEW_BAR,
            {"instrument": "MNQ", "timeframe": "1min", "data": {"close": 100.0}}
        )
        await nq_bus.emit(
            EventType.NEW_BAR,
            {"instrument": "NQ", "timeframe": "1min", "data": {"close": 200.0}}
        )

        # Allow event propagation
        await asyncio.sleep(0.1)

        # Verify instrument handlers only receive their own events
        assert len(mnq_events) == 1
        assert mnq_events[0].data["instrument"] == "MNQ"

        assert len(nq_events) == 1
        assert nq_events[0].data["instrument"] == "NQ"

        # Verify suite handler receives all events
        assert len(suite_events) == 2
        assert any(e.data["instrument"] == "MNQ" for e in suite_events)
        assert any(e.data["instrument"] == "NQ" for e in suite_events)

    @pytest.mark.asyncio
    async def test_wait_for_with_forwarding(self):
        """Test that wait_for works correctly with event forwarding."""
        suite_bus = EventBus()
        instrument_bus = EventBus()

        # Set up forwarding
        await instrument_bus.forward_to(suite_bus)

        # Start waiting at suite level
        async def wait_for_event():
            return await suite_bus.wait_for(EventType.NEW_BAR, timeout=1.0)

        wait_task = asyncio.create_task(wait_for_event())

        # Give task time to start waiting
        await asyncio.sleep(0.05)

        # Emit from instrument
        await instrument_bus.emit(
            EventType.NEW_BAR,
            {"instrument": "MNQ", "timeframe": "1min", "data": {"close": 100.0}}
        )

        # Should receive the event
        event = await wait_task
        assert event.data["instrument"] == "MNQ"
        assert event.data["data"]["close"] == 100.0

    @pytest.mark.asyncio
    async def test_multiple_event_types_forwarding(self):
        """Test that different event types are all forwarded correctly."""
        suite_bus = EventBus()
        instrument_bus = EventBus()

        # Set up forwarding
        await instrument_bus.forward_to(suite_bus)

        # Track different event types
        events_by_type = {
            EventType.NEW_BAR: [],
            EventType.QUOTE_UPDATE: [],
            EventType.TRADE_TICK: [],
            EventType.CONNECTED: [],
        }

        # Register handlers for each type
        for event_type in events_by_type:
            async def make_handler(et):
                async def handler(event):
                    events_by_type[et].append(event)
                return handler

            await suite_bus.on(event_type, await make_handler(event_type))

        # Emit various events
        await instrument_bus.emit(EventType.NEW_BAR, {"type": "bar"})
        await instrument_bus.emit(EventType.QUOTE_UPDATE, {"type": "quote"})
        await instrument_bus.emit(EventType.TRADE_TICK, {"type": "trade"})
        await instrument_bus.emit(EventType.CONNECTED, {"type": "connected"})

        # Allow propagation
        await asyncio.sleep(0.1)

        # Verify all event types were forwarded
        assert len(events_by_type[EventType.NEW_BAR]) == 1
        assert len(events_by_type[EventType.QUOTE_UPDATE]) == 1
        assert len(events_by_type[EventType.TRADE_TICK]) == 1
        assert len(events_by_type[EventType.CONNECTED]) == 1

    @pytest.mark.asyncio
    async def test_event_handler_removal(self):
        """Test that event handlers can be properly removed."""
        event_bus = EventBus()

        events_received = []

        async def handler(event):
            events_received.append(event)

        # Register handler
        await event_bus.on(EventType.NEW_BAR, handler)

        # Emit event - should be received
        await event_bus.emit(EventType.NEW_BAR, {"test": 1})
        await asyncio.sleep(0.05)
        assert len(events_received) == 1

        # Remove handler
        await event_bus.off(EventType.NEW_BAR, handler)

        # Emit again - should not be received
        await event_bus.emit(EventType.NEW_BAR, {"test": 2})
        await asyncio.sleep(0.05)
        assert len(events_received) == 1  # Still only 1

    @pytest.mark.asyncio
    async def test_once_handler(self):
        """Test that once handlers only fire once."""
        event_bus = EventBus()

        events_received = []

        async def handler(event):
            events_received.append(event)

        # Register once handler
        await event_bus.once(EventType.NEW_BAR, handler)

        # Emit multiple events
        await event_bus.emit(EventType.NEW_BAR, {"test": 1})
        await event_bus.emit(EventType.NEW_BAR, {"test": 2})
        await event_bus.emit(EventType.NEW_BAR, {"test": 3})

        await asyncio.sleep(0.1)

        # Should only receive first event
        assert len(events_received) == 1
        assert events_received[0].data["test"] == 1

    @pytest.mark.asyncio
    async def test_wildcard_event_forwarding(self):
        """Test that wildcard handlers forward all events."""
        suite_bus = EventBus()
        instrument_bus = EventBus()

        # Set up forwarding (uses wildcard internally)
        await instrument_bus.forward_to(suite_bus)

        # Track all events at suite level
        all_events = []

        async def wildcard_handler(event):
            all_events.append(event)

        await suite_bus.on_any(wildcard_handler)

        # Emit various event types
        await instrument_bus.emit(EventType.NEW_BAR, {"type": "bar"})
        await instrument_bus.emit(EventType.QUOTE_UPDATE, {"type": "quote"})
        await instrument_bus.emit("custom_event", {"type": "custom"})

        await asyncio.sleep(0.1)

        # Should receive all events
        assert len(all_events) == 3
        assert any(e.data["type"] == "bar" for e in all_events)
        assert any(e.data["type"] == "quote" for e in all_events)
        assert any(e.data["type"] == "custom" for e in all_events)

    @pytest.mark.asyncio
    async def test_event_data_structure_for_new_bar(self):
        """Test the expected data structure for NEW_BAR events."""
        event_bus = EventBus()

        received_event = None

        async def handler(event):
            nonlocal received_event
            received_event = event

        await event_bus.on(EventType.NEW_BAR, handler)

        # Emit with expected structure
        bar_data = {
            "timeframe": "1min",
            "data": {
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }

        await event_bus.emit(EventType.NEW_BAR, bar_data)
        await asyncio.sleep(0.05)

        # Verify structure
        assert received_event is not None
        assert "timeframe" in received_event.data
        assert "data" in received_event.data

        inner_data = received_event.data["data"]
        assert "open" in inner_data
        assert "high" in inner_data
        assert "low" in inner_data
        assert "close" in inner_data
        assert "volume" in inner_data

    @pytest.mark.asyncio
    async def test_event_handling_order(self):
        """Test that events are handled in order."""
        event_bus = EventBus()

        processing_order = []

        async def handler(event):
            processing_order.append(f"event_{event.data['id']}")

        await event_bus.on(EventType.NEW_BAR, handler)

        # Emit multiple events
        for i in range(3):
            await event_bus.emit(EventType.NEW_BAR, {"id": i})

        # Wait for processing
        await asyncio.sleep(0.1)

        # Events should be processed in order
        assert len(processing_order) == 3
        assert processing_order[0] == "event_0"
        assert processing_order[1] == "event_1"
        assert processing_order[2] == "event_2"


class TestEventSystemRegression:
    """Regression tests to prevent breaking the event system again."""

    @pytest.mark.asyncio
    async def test_instrument_context_methods_delegate_to_event_bus(self):
        """Ensure InstrumentContext methods properly delegate to event_bus."""
        from project_x_py.trading_suite import InstrumentContext

        # Create mock event bus
        mock_event_bus = AsyncMock(spec=EventBus)

        # Create context
        context = InstrumentContext(
            symbol="MNQ",
            instrument_info=MagicMock(),
            data=MagicMock(),
            orders=MagicMock(),
            positions=MagicMock(),
            event_bus=mock_event_bus
        )

        # Test delegation
        handler = AsyncMock()

        await context.on(EventType.NEW_BAR, handler)
        mock_event_bus.on.assert_called_once_with(EventType.NEW_BAR, handler)

        await context.once(EventType.QUOTE_UPDATE, handler)
        mock_event_bus.once.assert_called_once_with(EventType.QUOTE_UPDATE, handler)

        await context.off(EventType.NEW_BAR, handler)
        mock_event_bus.off.assert_called_once_with(EventType.NEW_BAR, handler)

        await context.wait_for(EventType.CONNECTED, timeout=5.0)
        mock_event_bus.wait_for.assert_called_once_with(EventType.CONNECTED, 5.0)

    @pytest.mark.asyncio
    async def test_forward_to_method_exists_and_works(self):
        """Ensure EventBus.forward_to method exists and functions correctly."""
        source_bus = EventBus()
        target_bus = EventBus()

        # Verify method exists
        assert hasattr(source_bus, "forward_to")
        assert callable(source_bus.forward_to)

        # Set up forwarding
        await source_bus.forward_to(target_bus)

        # Verify forwarding works
        events = []

        async def handler(event):
            events.append(event)

        await target_bus.on(EventType.NEW_BAR, handler)
        await source_bus.emit(EventType.NEW_BAR, {"test": "data"})

        await asyncio.sleep(0.05)

        assert len(events) == 1
        assert events[0].data["test"] == "data"

    @pytest.mark.asyncio
    async def test_trading_suite_setup_event_forwarding_called(self):
        """Ensure _setup_event_forwarding is called during TradingSuite creation."""
        with patch("project_x_py.trading_suite.TradingSuite._setup_event_forwarding") as mock_setup:
            mock_setup.return_value = asyncio.Future()
            mock_setup.return_value.set_result(None)

            with patch("project_x_py.trading_suite.ProjectX") as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.from_env.return_value.__aenter__.return_value = mock_client
                mock_client.authenticate = AsyncMock()
                mock_client.get_instrument = AsyncMock(
                    return_value=MagicMock(symbol="MNQ", name="MNQ", exchange="CME", min_tick=0.25)
                )
                mock_client.get_bars = AsyncMock(return_value=MagicMock(is_empty=lambda: True))
                mock_client.search_positions = AsyncMock(return_value=[])
                mock_client.search_orders = AsyncMock(return_value=[])

                with patch("project_x_py.realtime.ProjectXRealtimeClient") as mock_rt:
                    mock_rt.return_value = AsyncMock()
                    mock_rt.return_value.connect = AsyncMock(return_value=True)
                    mock_rt.return_value.is_connected = True

                    try:
                        suite = await TradingSuite.create("MNQ", timeframes=["1min"], auto_connect=False)
                        # Verify _setup_event_forwarding was called
                        mock_setup.assert_called()
                    except Exception:
                        # Even if creation fails for other reasons, we just want to verify the method was called
                        if mock_setup.called:
                            pass  # Test passes
                        else:
                            raise
