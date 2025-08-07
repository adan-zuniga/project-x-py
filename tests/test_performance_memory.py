"""Tests for performance and memory management."""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import psutil
import pytest
import pytz


@pytest.mark.asyncio
class TestPerformanceMemory:
    """Test performance characteristics and memory management."""

    async def test_data_manager_memory_limits(self):
        """Test that data manager respects memory limits."""
        from project_x_py.realtime_data_manager import RealtimeDataManager

        mock_client = MagicMock()
        mock_realtime = MagicMock()

        manager = RealtimeDataManager(
            instrument="MNQ",
            project_x=mock_client,
            realtime_client=mock_realtime,
        )

        # Add many data points
        for i in range(2000):
            manager.bars["1min"].append(
                {
                    "timestamp": datetime.now(pytz.UTC) - timedelta(minutes=i),
                    "open": 15500.0,
                    "high": 15550.0,
                    "low": 15450.0,
                    "close": 15525.0,
                    "volume": 100,
                }
            )

        # Trigger cleanup
        await manager._cleanup_old_data()

        # Should respect max_bars_per_timeframe (default 1000)
        assert len(manager.bars["1min"]) <= manager.memory_config.max_bars_per_timeframe

    async def test_orderbook_memory_limits(self):
        """Test that orderbook respects memory limits."""
        from project_x_py.orderbook import OrderBook

        mock_client = MagicMock()
        mock_realtime = MagicMock()

        orderbook = OrderBook(
            instrument="MNQ",
            project_x=mock_client,
            realtime_client=mock_realtime,
        )

        # Add many trades
        for i in range(15000):
            orderbook.trades.append(
                {
                    "price": 15500.0 + i * 0.25,
                    "size": 1,
                    "timestamp": (
                        datetime.now(pytz.UTC) - timedelta(seconds=i)
                    ).isoformat(),
                }
            )

        # Cleanup
        await orderbook._cleanup_old_trades()

        # Should respect max_trades limit (default 10000)
        assert len(orderbook.trades) <= orderbook.memory_config.max_trades

    async def test_concurrent_operations_performance(self):
        """Test performance under concurrent operations."""
        from project_x_py.order_manager import OrderManager

        mock_client = MagicMock()
        mock_client.place_order = AsyncMock(
            return_value={"success": True, "orderId": "12345"}
        )
        mock_realtime = MagicMock()

        manager = OrderManager(mock_client, mock_realtime)

        # Measure time for concurrent order placement
        start_time = time.time()

        # Place multiple orders concurrently
        tasks = []
        for i in range(10):
            task = manager.place_order(
                contract_id="MNQ",
                order_type=2,  # Market
                side=0,  # Buy
                size=1,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        elapsed_time = time.time() - start_time

        # All should succeed
        assert all(r["success"] for r in results)

        # Should complete reasonably quickly (< 2 seconds for 10 orders)
        assert elapsed_time < 2.0

    async def test_data_processing_latency(self):
        """Test latency of data processing pipeline."""
        from project_x_py.realtime_data_manager import RealtimeDataManager

        mock_client = MagicMock()
        mock_realtime = MagicMock()

        manager = RealtimeDataManager(
            instrument="MNQ",
            project_x=mock_client,
            realtime_client=mock_realtime,
        )

        # Measure tick processing time
        tick_data = {
            "timestamp": datetime.now(pytz.UTC).isoformat(),
            "price": 15500.0,
            "volume": 10,
        }

        start_time = time.perf_counter()
        await manager._process_tick(tick_data)
        processing_time = time.perf_counter() - start_time

        # Should process in under 10ms
        assert processing_time < 0.01

    async def test_callback_execution_performance(self):
        """Test performance of callback execution."""
        from project_x_py.realtime import ProjectXRealtimeClient

        # Create client with mocked dependencies
        client = ProjectXRealtimeClient(
            jwt_token="test",
            account_id="12345",
        )

        # Track callback execution times
        execution_times = []

        async def test_callback(data):
            start = time.perf_counter()
            # Simulate some work
            await asyncio.sleep(0.001)
            execution_times.append(time.perf_counter() - start)

        # Add multiple callbacks
        for i in range(10):
            await client.add_callback("test_event", test_callback)

        # Trigger callbacks
        start_time = time.perf_counter()
        await client._trigger_callbacks("test_event", {"test": "data"})
        total_time = time.perf_counter() - start_time

        # Should execute all callbacks efficiently
        assert len(execution_times) == 10
        # Total time should be reasonable (callbacks run concurrently)
        assert total_time < 0.1

    async def test_memory_leak_prevention(self):
        """Test that there are no memory leaks in long-running operations."""
        from project_x_py.position_manager import PositionManager

        mock_client = MagicMock()
        mock_realtime = MagicMock()

        manager = PositionManager(mock_client, mock_realtime)

        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform many operations
        for i in range(1000):
            # Add and remove positions
            manager.tracked_positions[f"POS_{i}"] = {
                "contractId": f"POS_{i}",
                "size": 1,
                "averagePrice": 100.0,
            }

            if i > 100:
                # Remove old positions
                old_key = f"POS_{i - 100}"
                if old_key in manager.tracked_positions:
                    del manager.tracked_positions[old_key]

        # Force garbage collection
        import gc

        gc.collect()

        # Check memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be minimal (< 50 MB)
        assert memory_increase < 50

    async def test_large_dataset_handling(self):
        """Test handling of large datasets efficiently."""
        from project_x_py.indicators import MACD, RSI, SMA

        # Create large dataset
        size = 10000
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime.now(pytz.UTC) - timedelta(minutes=i) for i in range(size)
                ],
                "open": [15500.0 + i * 0.1 for i in range(size)],
                "high": [15550.0 + i * 0.1 for i in range(size)],
                "low": [15450.0 + i * 0.1 for i in range(size)],
                "close": [15525.0 + i * 0.1 for i in range(size)],
                "volume": [100 + i for i in range(size)],
            }
        )

        # Apply multiple indicators
        start_time = time.perf_counter()

        result = df.pipe(SMA, period=20).pipe(RSI, period=14).pipe(MACD)

        processing_time = time.perf_counter() - start_time

        # Should process large dataset efficiently (< 1 second)
        assert processing_time < 1.0
        assert len(result) == size

    async def test_connection_pool_efficiency(self):
        """Test HTTP connection pool efficiency."""
        from project_x_py import ProjectX

        client = ProjectX(api_key="test", username="test")
        client._authenticated = True

        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"success": True, "data": []}

        client._client = MagicMock()
        client._client.request = AsyncMock(return_value=mock_response)

        # Make multiple requests
        start_time = time.perf_counter()

        tasks = []
        for i in range(20):
            task = client._make_request("GET", f"/test/endpoint/{i}")
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        elapsed_time = time.perf_counter() - start_time

        # Should reuse connections efficiently (< 1 second for 20 requests)
        assert elapsed_time < 1.0
        assert all(r["success"] for r in results)

    async def test_cache_performance(self):
        """Test cache performance for frequently accessed data."""
        from project_x_py import ProjectX

        client = ProjectX(api_key="test", username="test")
        client._authenticated = True

        # Mock instrument response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "success": True,
            "data": {"id": "MNQ", "name": "Micro E-mini NASDAQ"},
        }

        client._client = MagicMock()
        client._client.request = AsyncMock(return_value=mock_response)

        # First call (cache miss)
        start_time = time.perf_counter()
        instrument1 = await client.get_instrument("MNQ")
        first_call_time = time.perf_counter() - start_time

        # Second call (cache hit)
        start_time = time.perf_counter()
        instrument2 = await client.get_instrument("MNQ")
        second_call_time = time.perf_counter() - start_time

        # Cache hit should be much faster
        assert second_call_time < first_call_time / 10

        # Should only make one API call
        assert client._client.request.call_count == 1

    async def test_event_bus_performance(self):
        """Test EventBus performance with many subscribers."""
        from project_x_py import EventBus

        bus = EventBus()

        # Track callback executions
        callback_count = 0

        async def test_handler(event):
            nonlocal callback_count
            callback_count += 1

        # Subscribe many handlers
        for i in range(100):
            await bus.subscribe(f"handler_{i}", "test_event", test_handler)

        # Emit event
        start_time = time.perf_counter()
        await bus.emit("test_event", {"data": "test"})
        emit_time = time.perf_counter() - start_time

        # Should handle all subscribers efficiently
        assert callback_count == 100
        assert emit_time < 0.1  # Under 100ms for 100 handlers

    async def test_sliding_window_efficiency(self):
        """Test sliding window operations efficiency."""
        from collections import deque

        # Test deque performance for sliding windows
        window_size = 1000
        window = deque(maxlen=window_size)

        # Add many items
        start_time = time.perf_counter()
        for i in range(10000):
            window.append({"value": i})
        append_time = time.perf_counter() - start_time

        # Should maintain fixed size efficiently
        assert len(window) == window_size
        assert append_time < 0.1  # Under 100ms for 10k operations

    async def test_concurrent_position_updates(self):
        """Test handling concurrent position updates efficiently."""
        from project_x_py.position_manager import PositionManager

        mock_client = MagicMock()
        mock_realtime = MagicMock()

        manager = PositionManager(mock_client, mock_realtime)

        # Simulate concurrent position updates
        async def update_position(contract_id, size):
            async with manager.position_lock:
                manager.tracked_positions[contract_id] = {
                    "contractId": contract_id,
                    "size": size,
                    "averagePrice": 100.0,
                }

        # Create many concurrent updates
        start_time = time.perf_counter()

        tasks = []
        for i in range(100):
            task = update_position(f"POS_{i}", i)
            tasks.append(task)

        await asyncio.gather(*tasks)

        elapsed_time = time.perf_counter() - start_time

        # Should handle concurrent updates efficiently
        assert len(manager.tracked_positions) == 100
        assert elapsed_time < 1.0  # Under 1 second for 100 updates

    async def test_orderbook_update_performance(self):
        """Test orderbook update performance."""
        from project_x_py.orderbook import OrderBook

        mock_client = MagicMock()
        mock_realtime = MagicMock()

        orderbook = OrderBook(
            instrument="MNQ",
            project_x=mock_client,
            realtime_client=mock_realtime,
        )

        # Simulate rapid orderbook updates
        start_time = time.perf_counter()

        for i in range(1000):
            dom_update = {
                "contractId": "MNQ",
                "bids": [
                    {"price": 15500.0 - j * 0.25, "size": 10 + j} for j in range(10)
                ],
                "asks": [
                    {"price": 15501.0 + j * 0.25, "size": 10 + j} for j in range(10)
                ],
                "timestamp": datetime.now(pytz.UTC).isoformat(),
            }
            await orderbook._process_dom_update(dom_update)

        processing_time = time.perf_counter() - start_time

        # Should process 1000 updates efficiently
        assert processing_time < 2.0  # Under 2 seconds
        assert orderbook.stats["dom_updates"] == 1000
