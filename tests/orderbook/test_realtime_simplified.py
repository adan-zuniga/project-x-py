"""Simplified tests for OrderBook public API only."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from project_x_py.orderbook import OrderBook


@pytest.fixture
async def orderbook():
    """Create an OrderBook instance for testing."""
    mock_client = MagicMock()
    mock_event_bus = MagicMock()
    mock_event_bus.emit = AsyncMock()
    mock_event_bus.subscribe = AsyncMock()

    ob = OrderBook(
        instrument="MNQ",
        event_bus=mock_event_bus,
        project_x=mock_client,
    )

    # Mock realtime-related attributes for testing
    ob.realtime_client = MagicMock()
    ob.realtime_client.is_connected = MagicMock(return_value=True)
    ob.realtime_client.add_callback = AsyncMock()
    ob.realtime_client.subscribe_market_data = AsyncMock()
    ob.is_streaming = False

    return ob


@pytest.mark.asyncio
class TestOrderBookPublicAPI:
    """Test OrderBook public API methods."""

    async def test_initialize_realtime(self, orderbook):
        """Test initializing real-time orderbook feed."""
        ob = orderbook

        # Mock realtime client
        mock_realtime = MagicMock()
        mock_realtime.is_connected = MagicMock(return_value=True)
        mock_realtime.add_callback = AsyncMock()
        mock_realtime.subscribe_market_data = AsyncMock()

        result = await ob.initialize(
            realtime_client=mock_realtime,
            subscribe_to_depth=True,
            subscribe_to_quotes=True,
        )

        assert result is True

        # Should register callbacks
        mock_realtime.add_callback.assert_called()

    async def test_cleanup(self, orderbook):
        """Test cleaning up orderbook resources."""
        ob = orderbook

        # Call cleanup
        await ob.cleanup()

        # Memory manager should have cleaned up
        assert ob.memory_manager is not None

    async def test_get_market_imbalance(self, orderbook):
        """Test getting market imbalance."""
        ob = orderbook

        # Get imbalance with empty orderbook
        result = await ob.get_market_imbalance(levels=3)

        # Should return imbalance metrics
        assert result is not None
        assert "depth_imbalance" in result
        assert "bid_liquidity" in result
        assert "ask_liquidity" in result

    async def test_get_statistics(self, orderbook):
        """Test getting orderbook statistics."""
        ob = orderbook

        # Get statistics
        stats = await ob.get_statistics()

        # Should return stats dict
        assert stats is not None
        assert isinstance(stats, dict)

    async def test_get_spread_analysis(self, orderbook):
        """Test spread analysis."""
        ob = orderbook

        # Get spread analysis
        analysis = await ob.get_spread_analysis()

        # Should return spread metrics
        assert analysis is not None
        assert "avg_spread" in analysis
        assert "spread_volatility" in analysis

    async def test_get_orderbook_depth(self, orderbook):
        """Test getting orderbook depth."""
        ob = orderbook

        # Get depth
        depth = await ob.get_orderbook_depth(price_range=1.0)

        assert depth is not None
        assert "estimated_fill_price" in depth

    async def test_get_cumulative_delta(self, orderbook):
        """Test getting cumulative delta."""
        ob = orderbook

        # Get cumulative delta
        delta = await ob.get_cumulative_delta()

        assert delta is not None
        assert "cumulative_delta" in delta
        assert "buy_volume" in delta
        assert "sell_volume" in delta

    async def test_get_volume_profile(self, orderbook):
        """Test getting volume profile."""
        ob = orderbook

        # Get volume profile
        profile = await ob.get_volume_profile()

        assert profile is not None
        assert "poc" in profile
        assert "value_area_high" in profile
        assert "value_area_low" in profile

    async def test_get_trade_flow_summary(self, orderbook):
        """Test getting trade flow summary."""
        ob = orderbook

        # Get trade flow summary
        summary = await ob.get_trade_flow_summary()

        assert summary is not None
        assert "aggressive_buy_volume" in summary
        assert "aggressive_sell_volume" in summary

    async def test_detect_iceberg_orders(self, orderbook):
        """Test detection of iceberg orders."""
        ob = orderbook

        # Detect icebergs
        result = await ob.detect_iceberg_orders()

        # Should return detection result
        assert result is not None
        assert isinstance(result, dict)

    async def test_detect_order_clusters(self, orderbook):
        """Test detecting order clusters."""
        ob = orderbook

        # Detect clusters
        clusters = await ob.detect_order_clusters()

        assert clusters is not None
        assert isinstance(clusters, (dict, list))

    async def test_get_advanced_market_metrics(self, orderbook):
        """Test getting advanced market metrics."""
        ob = orderbook

        # Get metrics
        metrics = await ob.get_advanced_market_metrics()

        assert metrics is not None
        assert isinstance(metrics, dict)

    async def test_get_liquidity_levels(self, orderbook):
        """Test getting liquidity levels."""
        ob = orderbook

        # Get liquidity levels
        levels = await ob.get_liquidity_levels()

        assert levels is not None
        assert isinstance(levels, dict)

    async def test_get_support_resistance_levels(self, orderbook):
        """Test getting support and resistance levels."""
        ob = orderbook

        # Get support/resistance levels
        levels = await ob.get_support_resistance_levels()

        assert levels is not None
        assert isinstance(levels, dict)

    async def test_get_memory_stats(self, orderbook):
        """Test getting memory statistics."""
        ob = orderbook

        # Get memory stats
        stats = await ob.get_memory_stats()

        # Should return memory stats
        assert stats is not None
        assert isinstance(stats, dict)
