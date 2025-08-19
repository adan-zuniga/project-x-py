"""
Integration tests for the enhanced statistics system.

Tests that all components properly expose statistics and that
the data is easily accessible for monitoring and alerting systems.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_x_py import TradingSuite
from project_x_py.order_manager import OrderManager
from project_x_py.position_manager import PositionManager
from project_x_py.realtime_data_manager import RealtimeDataManager
from project_x_py.risk_manager import RiskManager


class TestStatisticsIntegration:
    """Integration tests for statistics across all components."""

    @pytest.mark.asyncio
    async def test_all_components_have_stats_methods(self):
        """Verify all components expose the required statistics methods."""
        # Create mock clients
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(id=12345)
        mock_event_bus = MagicMock()
        mock_realtime = MagicMock()

        # Create components
        order_manager = OrderManager(mock_client, mock_event_bus)
        position_manager = PositionManager(mock_client, mock_event_bus)
        risk_manager = RiskManager(
            mock_client,
            order_manager,
            mock_event_bus,
            position_manager=position_manager,
        )

        # Check OrderManager has enhanced stats methods
        assert hasattr(order_manager, "track_operation")
        assert hasattr(order_manager, "track_error")
        assert hasattr(order_manager, "get_performance_metrics")
        assert hasattr(order_manager, "get_error_stats")
        assert hasattr(order_manager, "get_enhanced_memory_stats")
        assert hasattr(order_manager, "export_stats")

        # Check PositionManager has enhanced stats methods
        assert hasattr(position_manager, "track_operation")
        assert hasattr(position_manager, "track_error")
        assert hasattr(position_manager, "get_performance_metrics")
        assert hasattr(position_manager, "get_error_stats")
        assert hasattr(position_manager, "get_enhanced_memory_stats")

        # Check RiskManager has enhanced stats methods
        assert hasattr(risk_manager, "track_operation")
        assert hasattr(risk_manager, "track_error")
        assert hasattr(risk_manager, "get_performance_metrics")

    @pytest.mark.asyncio
    async def test_trading_suite_aggregates_stats(self):
        """Test that TradingSuite properly aggregates statistics from all components."""
        with patch("project_x_py.trading_suite.ProjectX") as MockProjectX:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.from_env = AsyncMock(return_value=mock_client)
            mock_client.authenticate = AsyncMock()
            mock_client.get_instrument = AsyncMock(
                return_value=MagicMock(id="MNQ123", tickSize=0.25)
            )
            mock_client.account_info = MagicMock(id=12345, name="Test")
            MockProjectX.from_env.return_value = mock_client

            # Create suite
            suite = TradingSuite(instrument="MNQ")
            suite.client = mock_client
            suite.instrument_info = MagicMock(id="MNQ123")

            # Mock components
            suite.orders = MagicMock()
            suite.orders.get_order_statistics = AsyncMock(
                return_value={"orders_placed": 10, "orders_filled": 8, "fill_rate": 0.8}
            )

            suite.positions = MagicMock()
            suite.positions.stats = {"positions_tracked": 5}

            suite.data = MagicMock()
            suite.data.get_memory_stats = MagicMock(
                return_value={"memory_usage_mb": 2.5, "bars_processed": 1000}
            )

            # Get aggregated stats
            stats = await suite.get_stats()

            # Verify stats structure
            assert isinstance(stats, dict)
            assert "orders_placed" in stats
            assert "positions_tracked" in stats
            assert "data_memory_usage_mb" in stats

            # Verify aggregation includes all components
            assert stats["orders_placed"] == 10
            assert stats["positions_tracked"] == 5
            assert stats["data_memory_usage_mb"] == 2.5

    @pytest.mark.asyncio
    async def test_stats_accessible_during_operation(self):
        """Test that statistics remain accessible during active trading operations."""
        # Create mock component
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(id=12345)
        mock_event_bus = MagicMock()

        order_manager = OrderManager(mock_client, mock_event_bus)

        # Simulate operations
        await order_manager.track_operation("test_op", 10.5, success=True)
        await order_manager.track_operation("test_op", 20.3, success=True)
        await order_manager.track_error(
            ValueError("Test error"), context="test_context"
        )

        # Verify stats are accessible
        perf_stats = await order_manager.get_performance_metrics()
        assert "operation_stats" in perf_stats
        assert "test_op" in perf_stats["operation_stats"]
        assert perf_stats["operation_stats"]["test_op"]["count"] == 2

        error_stats = await order_manager.get_error_stats()
        assert error_stats["total_errors"] == 1
        assert "ValueError" in error_stats["error_types"]

    @pytest.mark.asyncio
    async def test_stats_export_formats(self):
        """Test that statistics can be exported in different formats."""
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(id=12345)
        mock_event_bus = MagicMock()

        order_manager = OrderManager(mock_client, mock_event_bus)

        # Add some data
        await order_manager.track_operation("export_test", 15.0)

        # Test JSON export
        json_export = await order_manager.export_stats("json")
        assert isinstance(json_export, dict)
        assert "timestamp" in json_export
        assert "component" in json_export
        assert "performance" in json_export

        # Test Prometheus export
        prom_export = await order_manager.export_stats("prometheus")
        assert isinstance(prom_export, str)
        assert "TYPE" in prom_export or "HELP" in prom_export or len(prom_export) > 0

    @pytest.mark.asyncio
    async def test_memory_stats_tracking(self):
        """Test that memory statistics are properly tracked."""
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(id=12345)
        mock_event_bus = MagicMock()

        position_manager = PositionManager(mock_client, mock_event_bus)

        # Get memory stats
        mem_stats = await position_manager.get_enhanced_memory_stats()

        assert "current_memory_mb" in mem_stats
        assert "memory_trend" in mem_stats
        assert isinstance(mem_stats["current_memory_mb"], float)
        assert mem_stats["current_memory_mb"] >= 0

    @pytest.mark.asyncio
    async def test_data_quality_tracking(self):
        """Test data quality metrics tracking."""
        mock_client = MagicMock()
        mock_event_bus = MagicMock()
        mock_realtime = MagicMock()

        # Create data manager with minimal setup
        data_manager = RealtimeDataManager(
            instrument="MNQ",
            project_x=mock_client,
            realtime_client=mock_realtime,
            event_bus=mock_event_bus,
        )

        # Track data quality
        await data_manager.track_data_quality(
            total_points=1000, invalid_points=10, missing_points=5, duplicate_points=2
        )

        # Get quality stats
        quality_stats = await data_manager.get_data_quality_stats()

        assert "quality_score" in quality_stats
        assert "invalid_rate" in quality_stats
        assert quality_stats["total_data_points"] == 1000
        assert quality_stats["invalid_data_points"] == 10

    @pytest.mark.asyncio
    async def test_cross_component_metrics(self):
        """Test that cross-component metrics are calculated correctly."""
        with patch("project_x_py.trading_suite.ProjectX"):
            suite = TradingSuite(instrument="MNQ")

            # Mock components with stats
            suite.orders = MagicMock()
            suite.orders.get_performance_metrics = AsyncMock(
                return_value={
                    "network_stats": {"total_requests": 100, "successful_requests": 95}
                }
            )
            suite.orders.get_error_stats = AsyncMock(return_value={"total_errors": 5})

            suite.positions = MagicMock()
            suite.positions.get_performance_metrics = AsyncMock(
                return_value={
                    "network_stats": {"total_requests": 50, "successful_requests": 48}
                }
            )
            suite.positions.get_error_stats = AsyncMock(
                return_value={"total_errors": 2}
            )

            # Create aggregator
            from project_x_py.utils.statistics_aggregator import StatisticsAggregator

            aggregator = StatisticsAggregator(suite)

            # Get aggregated stats
            stats = await aggregator.get_aggregated_stats()

            # Verify cross-component metrics
            assert "health_score" in stats
            assert "total_operations" in stats
            assert "overall_error_rate" in stats

            # Health score should be between 0 and 100
            assert 0 <= stats["health_score"] <= 100

    @pytest.mark.asyncio
    async def test_stats_persistence_across_operations(self):
        """Test that statistics persist across multiple operations."""
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(id=12345)
        mock_event_bus = MagicMock()

        order_manager = OrderManager(mock_client, mock_event_bus)

        # Track multiple operations
        for i in range(10):
            await order_manager.track_operation(f"op_{i % 3}", float(i * 10))

        # Get stats
        perf_stats = await order_manager.get_performance_metrics()

        # Verify all operations are tracked
        assert len(perf_stats["operation_stats"]) == 3  # 3 unique operation types
        total_ops = sum(
            stats["count"] for stats in perf_stats["operation_stats"].values()
        )
        assert total_ops == 10

    @pytest.mark.asyncio
    async def test_stats_cleanup_mechanism(self):
        """Test that old statistics are properly cleaned up."""
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(id=12345)
        mock_event_bus = MagicMock()

        order_manager = OrderManager(mock_client, mock_event_bus)

        # Track operations
        for i in range(100):
            await order_manager.track_operation("cleanup_test", float(i))

        # Manually trigger cleanup
        await order_manager.cleanup_old_stats()

        # Stats should still be accessible
        perf_stats = await order_manager.get_performance_metrics()
        assert "operation_stats" in perf_stats

    @pytest.mark.asyncio
    async def test_concurrent_stats_access(self):
        """Test that statistics can be accessed concurrently without issues."""
        mock_client = MagicMock()
        mock_client.account_info = MagicMock(id=12345)
        mock_event_bus = MagicMock()

        order_manager = OrderManager(mock_client, mock_event_bus)

        async def track_operations():
            for i in range(50):
                await order_manager.track_operation(f"concurrent_{i % 5}", float(i))

        async def read_stats():
            for _ in range(50):
                stats = await order_manager.get_performance_metrics()
                assert "operation_stats" in stats
                await asyncio.sleep(0.001)

        # Run concurrently
        await asyncio.gather(track_operations(), read_stats(), read_stats())

        # Verify final state
        final_stats = await order_manager.get_performance_metrics()
        assert len(final_stats["operation_stats"]) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
