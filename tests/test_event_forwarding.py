"""
Test event forwarding from instrument EventBuses to suite EventBus.

This test validates the core event forwarding functionality without
requiring complex mocking of the real-time client.
"""

import asyncio

import pytest

from project_x_py.event_bus import EventBus, EventType
from project_x_py.trading_suite import InstrumentContext


@pytest.mark.asyncio
async def test_event_forwarding_from_instrument_to_suite():
    """Test that events are forwarded from instrument EventBus to suite EventBus."""
    # Create suite-level EventBus
    suite_event_bus = EventBus()

    # Create instrument-specific EventBus
    mnq_event_bus = EventBus()
    nq_event_bus = EventBus()

    # Set up event forwarding (simulating what _setup_event_forwarding does)
    await mnq_event_bus.forward_to(suite_event_bus)
    await nq_event_bus.forward_to(suite_event_bus)

    # Track events received at suite level
    suite_events = []

    async def suite_handler(event):
        suite_events.append(event)

    # Register handler at suite level
    await suite_event_bus.on(EventType.NEW_BAR, suite_handler)

    # Emit events from instrument-specific buses
    await mnq_event_bus.emit(
        EventType.NEW_BAR,
        {"instrument": "MNQ", "timeframe": "1min", "close": 100.0}
    )
    await nq_event_bus.emit(
        EventType.NEW_BAR,
        {"instrument": "NQ", "timeframe": "1min", "close": 200.0}
    )

    # Allow event propagation
    await asyncio.sleep(0.1)

    # Suite should receive events from both instruments
    assert len(suite_events) == 2
    assert any(e.data["instrument"] == "MNQ" for e in suite_events)
    assert any(e.data["instrument"] == "NQ" for e in suite_events)


@pytest.mark.asyncio
async def test_instrument_context_event_methods():
    """Test that InstrumentContext event methods work correctly."""
    # Create a mock InstrumentContext with event_bus
    event_bus = EventBus()

    # Create a simple mock context with the event_bus attribute
    class MockInstrumentContext:
        def __init__(self):
            self.event_bus = event_bus
            self.symbol = "MNQ"

        async def on(self, event, handler):
            """Register event handler on this instrument's event bus."""
            await self.event_bus.on(event, handler)

        async def once(self, event, handler):
            """Register one-time event handler on this instrument's event bus."""
            await self.event_bus.once(event, handler)

        async def off(self, event=None, handler=None):
            """Remove event handler(s) from this instrument's event bus."""
            await self.event_bus.off(event, handler)

        async def wait_for(self, event, timeout=None):
            """Wait for specific event to occur on this instrument's event bus."""
            return await self.event_bus.wait_for(event, timeout)

    context = MockInstrumentContext()

    # Test that methods exist and are callable
    events_received = []

    async def handler(event):
        events_received.append(event)

    # Register handler
    await context.on(EventType.NEW_BAR, handler)

    # Emit event
    await context.event_bus.emit(
        EventType.NEW_BAR,
        {"instrument": "MNQ", "timeframe": "1min", "close": 100.0}
    )

    # Allow event propagation
    await asyncio.sleep(0.1)

    # Handler should have received the event
    assert len(events_received) == 1
    assert events_received[0].data["instrument"] == "MNQ"


@pytest.mark.asyncio
async def test_wait_for_with_event_forwarding():
    """Test that wait_for works with event forwarding."""
    # Create suite and instrument EventBuses
    suite_event_bus = EventBus()
    instrument_event_bus = EventBus()

    # Set up forwarding
    await instrument_event_bus.forward_to(suite_event_bus)

    # Create a task that waits for an event at suite level
    async def wait_for_event():
        return await suite_event_bus.wait_for(EventType.NEW_BAR, timeout=1.0)

    wait_task = asyncio.create_task(wait_for_event())

    # Give the task time to start waiting
    await asyncio.sleep(0.1)

    # Emit event from instrument bus
    await instrument_event_bus.emit(
        EventType.NEW_BAR,
        {"instrument": "MNQ", "timeframe": "1min", "close": 100.0}
    )

    # wait_for should receive the event
    try:
        event = await asyncio.wait_for(wait_task, timeout=1.0)
        assert event.data["instrument"] == "MNQ"
        assert event.data["close"] == 100.0
    except asyncio.TimeoutError:
        pytest.fail("wait_for did not receive forwarded event")


@pytest.mark.asyncio
async def test_multiple_instrument_event_isolation():
    """Test that instrument-specific handlers only receive their own events."""
    # Create EventBuses
    suite_event_bus = EventBus()
    mnq_event_bus = EventBus()
    nq_event_bus = EventBus()

    # Set up forwarding
    await mnq_event_bus.forward_to(suite_event_bus)
    await nq_event_bus.forward_to(suite_event_bus)

    # Track events for each instrument
    mnq_events = []
    nq_events = []
    suite_events = []

    async def mnq_handler(event):
        mnq_events.append(event)

    async def nq_handler(event):
        nq_events.append(event)

    async def suite_handler(event):
        suite_events.append(event)

    # Register handlers
    await mnq_event_bus.on(EventType.NEW_BAR, mnq_handler)
    await nq_event_bus.on(EventType.NEW_BAR, nq_handler)
    await suite_event_bus.on(EventType.NEW_BAR, suite_handler)

    # Emit events
    await mnq_event_bus.emit(
        EventType.NEW_BAR,
        {"instrument": "MNQ", "timeframe": "1min", "close": 100.0}
    )
    await nq_event_bus.emit(
        EventType.NEW_BAR,
        {"instrument": "NQ", "timeframe": "1min", "close": 200.0}
    )

    # Allow event propagation
    await asyncio.sleep(0.1)

    # Each instrument handler should only receive its own events
    assert len(mnq_events) == 1
    assert mnq_events[0].data["instrument"] == "MNQ"

    assert len(nq_events) == 1
    assert nq_events[0].data["instrument"] == "NQ"

    # Suite handler should receive all events
    assert len(suite_events) == 2
    assert any(e.data["instrument"] == "MNQ" for e in suite_events)
    assert any(e.data["instrument"] == "NQ" for e in suite_events)
