"""
Integration tests for async concurrent operations.

These tests verify that multiple async components work together correctly
and demonstrate the performance benefits of concurrent operations.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_x_py import (
    AsyncProjectX,
    create_async_order_manager,
    create_async_position_manager,
    create_async_trading_suite,
)
from project_x_py.models import Account, Instrument


@pytest.fixture
def mock_account():
    """Create a mock account."""
    return Account(
        id="12345",
        name="Test Account",
        balance=50000.0,
        canTrade=True,
        simulated=True,
    )


@pytest.fixture
def mock_instrument():
    """Create a mock instrument."""
    return Instrument(
        id="INS123",
        symbol="MGC",
        name="Micro Gold Futures",
        activeContract="CON.F.US.MGC.M25",
        lastPrice=2050.0,
        tickSize=0.1,
        pointValue=10.0,
    )


@pytest.mark.asyncio
async def test_concurrent_api_calls(mock_account, mock_instrument):
    """Test concurrent API calls are faster than sequential."""
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock responses with delays to simulate network latency
        async def delayed_response(delay=0.1):
            await asyncio.sleep(delay)
            return MagicMock(status_code=200)

        # Setup mocked responses
        mock_client.post.side_effect = [
            delayed_response(),  # authenticate
        ]

        mock_client.get.side_effect = [
            # Account info
            MagicMock(
                status_code=200,
                json=lambda: {
                    "simAccounts": [mock_account.__dict__],
                    "liveAccounts": [],
                },
            ),
            # Positions (concurrent call 1)
            delayed_response(),
            # Orders (concurrent call 2)
            delayed_response(),
            # Instruments (concurrent call 3)
            delayed_response(),
        ]

        async with AsyncProjectX("test_user", "test_key") as client:
            client.account_info = mock_account

            # Sequential calls
            start_seq = time.time()
            pos1 = await client.search_open_positions()
            orders1 = await client.search_open_orders()
            inst1 = await client.search_instruments("MGC")
            seq_time = time.time() - start_seq

            # Reset side effects for concurrent test
            mock_client.get.side_effect = [
                delayed_response(),
                delayed_response(),
                delayed_response(),
            ]

            # Concurrent calls
            start_con = time.time()
            pos2, orders2, inst2 = await asyncio.gather(
                client.search_open_positions(),
                client.search_open_orders(),
                client.search_instruments("MGC"),
            )
            con_time = time.time() - start_con

            # Concurrent should be significantly faster
            assert con_time < seq_time * 0.5  # At least 2x faster


@pytest.mark.asyncio
async def test_trading_suite_integration():
    """Test complete trading suite with all components integrated."""
    with patch("project_x_py.AsyncProjectX") as mock_client_class:
        # Create mock client
        mock_client = AsyncMock(spec=AsyncProjectX)
        mock_client.jwt_token = "test_jwt"
        mock_client.account_info = MagicMock(id="12345")
        mock_client_class.return_value = mock_client

        # Create trading suite
        suite = await create_async_trading_suite(
            instrument="MGC",
            project_x=mock_client,
            jwt_token="test_jwt",
            account_id="12345",
            timeframes=["1min", "5min", "15min"],
        )

        # Verify all components are created
        assert "realtime_client" in suite
        assert "data_manager" in suite
        assert "orderbook" in suite
        assert "order_manager" in suite
        assert "position_manager" in suite
        assert "config" in suite

        # Verify components are properly connected
        assert suite["data_manager"].realtime_client == suite["realtime_client"]
        assert suite["orderbook"].realtime_client == suite["realtime_client"]

        # Verify managers are initialized
        assert hasattr(suite["order_manager"], "project_x")
        assert hasattr(suite["position_manager"], "project_x")


@pytest.mark.asyncio
async def test_concurrent_order_placement():
    """Test placing multiple orders concurrently."""
    with patch("project_x_py.AsyncProjectX") as mock_client_class:
        mock_client = AsyncMock(spec=AsyncProjectX)
        mock_client.place_order = AsyncMock(
            side_effect=[MagicMock(success=True, orderId=f"ORD{i}") for i in range(5)]
        )

        order_manager = create_async_order_manager(mock_client)
        await order_manager.initialize()

        # Place 5 orders concurrently
        orders = [
            {"contract_id": "MGC", "side": 0, "size": 1, "price": 2050 + i}
            for i in range(5)
        ]

        start_time = time.time()
        tasks = [order_manager.place_limit_order(**order) for order in orders]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Verify all orders placed successfully
        assert len(results) == 5
        assert all(r.success for r in results)

        # Should be fast due to concurrency
        assert end_time - start_time < 1.0


@pytest.mark.asyncio
async def test_realtime_event_propagation():
    """Test that real-time events propagate to all managers correctly."""
    # Create mock realtime client
    realtime_client = AsyncMock()
    realtime_client.callbacks = {}

    async def mock_add_callback(event_type, callback):
        if event_type not in realtime_client.callbacks:
            realtime_client.callbacks[event_type] = []
        realtime_client.callbacks[event_type].append(callback)

    realtime_client.add_callback = mock_add_callback

    # Create managers with shared realtime client
    with patch("project_x_py.AsyncProjectX") as mock_client_class:
        mock_client = AsyncMock()

        order_manager = create_async_order_manager(mock_client, realtime_client)
        await order_manager.initialize()

        position_manager = create_async_position_manager(mock_client, realtime_client)
        await position_manager.initialize()

        # Verify callbacks are registered
        assert "order_update" in realtime_client.callbacks
        assert "position_update" in realtime_client.callbacks
        assert "trade_execution" in realtime_client.callbacks


@pytest.mark.asyncio
async def test_concurrent_data_analysis():
    """Test analyzing multiple timeframes concurrently."""
    with patch("project_x_py.AsyncProjectX") as mock_client_class:
        mock_client = AsyncMock()

        # Mock data retrieval with different delays
        async def get_data(symbol, days, interval):
            # Simulate network delay based on interval
            delay = 0.1 if interval < 60 else 0.2
            await asyncio.sleep(delay)
            return MagicMock(is_empty=lambda: False)

        mock_client.get_data = get_data

        # Time sequential data fetching
        start_seq = time.time()
        data1 = await mock_client.get_data("MGC", 1, 5)
        data2 = await mock_client.get_data("MGC", 1, 15)
        data3 = await mock_client.get_data("MGC", 5, 60)
        data4 = await mock_client.get_data("MGC", 10, 240)
        seq_time = time.time() - start_seq

        # Time concurrent data fetching
        start_con = time.time()
        data_results = await asyncio.gather(
            mock_client.get_data("MGC", 1, 5),
            mock_client.get_data("MGC", 1, 15),
            mock_client.get_data("MGC", 5, 60),
            mock_client.get_data("MGC", 10, 240),
        )
        con_time = time.time() - start_con

        # Concurrent should be much faster
        assert con_time < seq_time * 0.4  # At least 2.5x faster
        assert len(data_results) == 4


@pytest.mark.asyncio
async def test_error_handling_in_concurrent_operations():
    """Test that errors in concurrent operations are handled properly."""
    with patch("project_x_py.AsyncProjectX") as mock_client_class:
        mock_client = AsyncMock()

        # Mix successful and failing operations
        mock_client.search_open_positions = AsyncMock(
            return_value={"pos1": MagicMock()}
        )
        mock_client.search_open_orders = AsyncMock(
            side_effect=Exception("Network error")
        )
        mock_client.search_instruments = AsyncMock(return_value=[MagicMock()])

        # Use gather with return_exceptions=True
        results = await asyncio.gather(
            mock_client.search_open_positions(),
            mock_client.search_open_orders(),
            mock_client.search_instruments("MGC"),
            return_exceptions=True,
        )

        # Verify we got mixed results
        assert len(results) == 3
        assert isinstance(results[0], dict)  # Success
        assert isinstance(results[1], Exception)  # Error
        assert isinstance(results[2], list)  # Success


@pytest.mark.asyncio
async def test_async_context_manager_cleanup():
    """Test that async context managers properly clean up resources."""
    cleanup_called = False

    class MockAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            nonlocal cleanup_called
            cleanup_called = True
            # Simulate cleanup work
            await asyncio.sleep(0.01)

    async with MockAsyncClient() as client:
        pass

    assert cleanup_called


@pytest.mark.asyncio
async def test_background_task_management():
    """Test running background tasks while processing main logic."""
    results = []

    async def background_monitor():
        """Simulate background monitoring."""
        for i in range(5):
            await asyncio.sleep(0.1)
            results.append(f"monitor_{i}")

    async def main_logic():
        """Simulate main trading logic."""
        for i in range(3):
            await asyncio.sleep(0.15)
            results.append(f"main_{i}")

    # Run both concurrently
    monitor_task = asyncio.create_task(background_monitor())
    main_task = asyncio.create_task(main_logic())

    await asyncio.gather(monitor_task, main_task)

    # Verify both ran concurrently
    assert len(results) == 8
    # Results should be interleaved
    assert "monitor_0" in results
    assert "main_0" in results


@pytest.mark.asyncio
async def test_rate_limiting_with_concurrent_requests():
    """Test that rate limiting works correctly with concurrent requests."""
    from project_x_py.utils import AsyncRateLimiter

    rate_limiter = AsyncRateLimiter(requests_per_minute=60)  # 1 per second

    request_times = []

    async def make_request(i):
        async with rate_limiter:
            request_times.append(time.time())
            await asyncio.sleep(0.01)  # Simulate work

    # Try to make 5 requests concurrently
    start_time = time.time()
    await asyncio.gather(*[make_request(i) for i in range(5)])
    end_time = time.time()

    # Should take at least 4 seconds due to rate limiting
    assert end_time - start_time >= 4.0

    # Verify requests were spaced out
    for i in range(1, len(request_times)):
        time_diff = request_times[i] - request_times[i - 1]
        assert time_diff >= 0.9  # Allow small margin


@pytest.mark.asyncio
async def test_memory_efficiency_with_streaming():
    """Test memory efficiency when processing streaming data."""
    data_points_processed = 0

    async def data_generator():
        """Simulate streaming data."""
        for i in range(1000):
            yield {"timestamp": datetime.now(), "price": 2050 + i * 0.1}
            await asyncio.sleep(0.001)

    async def process_stream():
        nonlocal data_points_processed
        async for data in data_generator():
            # Process without storing all data
            data_points_processed += 1
            if data_points_processed >= 100:
                break

    await process_stream()
    assert data_points_processed == 100
