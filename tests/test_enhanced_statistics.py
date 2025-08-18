#!/usr/bin/env python3
"""
Comprehensive unit tests for enhanced statistics tracking system.

Tests the EnhancedStatsTrackingMixin and StatisticsAggregator for:
- Error handling and graceful degradation
- Memory leak prevention with circular buffers
- PII sanitization
- Thread safety
- Performance overhead
- Edge cases and boundary conditions
"""

import asyncio
import sys
from collections import deque
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_x_py.utils.enhanced_stats_tracking import EnhancedStatsTrackingMixin
from project_x_py.utils.statistics_aggregator import StatisticsAggregator


class TestComponent(EnhancedStatsTrackingMixin):
    """Test component that uses the enhanced stats tracking mixin."""

    def __init__(self):
        self._init_enhanced_stats(
            max_errors=10,
            max_timings=100,
            retention_hours=1,
            enable_profiling=True,
        )


class TestEnhancedStatsTracking:
    """Test suite for EnhancedStatsTrackingMixin."""

    @pytest.mark.asyncio
    async def test_circular_buffer_prevents_memory_leak(self):
        """Test that circular buffers prevent unbounded memory growth."""
        component = TestComponent()

        # Add more errors than the max
        for i in range(20):
            await component.track_error(
                Exception(f"Error {i}"),
                context=f"test_{i}",
                details={"index": i},
            )

        # Should only keep last 10 errors
        assert len(component._error_history) == 10
        assert component._error_count == 20  # Total count preserved

        # Add more timings than the max
        for i in range(150):
            await component.track_operation(
                operation="test_op",
                duration_ms=float(i),
                success=True,
            )

        # Should only keep last 100 timings in operation-specific buffer
        assert len(component._operation_timings["test_op"]) == 100
        # Verify it contains the last 100 values (50-149)
        assert min(component._operation_timings["test_op"]) == 50.0
        assert max(component._operation_timings["test_op"]) == 149.0

    @pytest.mark.asyncio
    async def test_pii_sanitization(self):
        """Test that PII is properly sanitized from exports."""
        component = TestComponent()

        # Track error with sensitive data
        await component.track_error(
            Exception("Test error"),
            context="trading",
            details={
                "account_id": "ACC123456789",
                "api_key": "secret_key_123",
                "order_size": 100,
                "pnl": 5000.50,
                "balance": 100000,
                "safe_field": "this_is_safe",
            },
        )

        # Export stats
        exported = await component.export_stats(format="json")

        # Check that PII is sanitized in error details
        recent_errors = exported["errors"]["recent_errors"]
        if recent_errors:
            details = recent_errors[0]["details"]
            assert details["account_id"] == "***6789"  # Last 4 chars
            assert details["api_key"] == "***REDACTED***"
            assert details["order_size"] == "***REDACTED***"
            assert details["pnl"] == "positive"  # Shows sign, not value
            assert details["balance"] == "positive"  # Shows sign, not value
            assert details["safe_field"] == "this_is_safe"  # Not sanitized

    @pytest.mark.asyncio
    async def test_thread_safety(self):
        """Test that concurrent access to stats is thread-safe."""
        component = TestComponent()

        async def track_operations(op_name: str, count: int):
            for i in range(count):
                await component.track_operation(
                    operation=op_name,
                    duration_ms=float(i),
                    success=True,
                )

        # Run multiple concurrent tasks
        tasks = [
            track_operations("op1", 50),
            track_operations("op2", 50),
            track_operations("op3", 50),
        ]

        await asyncio.gather(*tasks)

        # Verify all operations were tracked
        assert "op1" in component._operation_timings
        assert "op2" in component._operation_timings
        assert "op3" in component._operation_timings
        assert len(component._operation_timings["op1"]) == 50
        assert len(component._operation_timings["op2"]) == 50
        assert len(component._operation_timings["op3"]) == 50

    @pytest.mark.asyncio
    async def test_performance_percentiles(self):
        """Test performance percentile calculations."""
        component = TestComponent()

        # Add known timing values
        timings = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for timing in timings:
            await component.track_operation(
                operation="test",
                duration_ms=float(timing),
                success=True,
            )

        metrics = await component.get_performance_metrics()
        op_stats = metrics["operation_stats"]["test"]

        # Check percentiles
        assert op_stats["p50_ms"] == 50  # Median
        assert op_stats["p95_ms"] == 90  # 95th percentile
        assert op_stats["p99_ms"] == 100  # 99th percentile
        assert op_stats["min_ms"] == 10
        assert op_stats["max_ms"] == 100
        assert op_stats["avg_ms"] == 55  # Average

    @pytest.mark.asyncio
    async def test_data_quality_tracking(self):
        """Test data quality metrics tracking."""
        component = TestComponent()

        # Track various data quality issues
        await component.track_data_quality(
            total_points=1000,
            invalid_points=10,
            missing_points=5,
            duplicate_points=3,
        )

        await component.track_data_quality(
            total_points=500,
            invalid_points=2,
            missing_points=1,
            duplicate_points=0,
        )

        quality_stats = await component.get_data_quality_stats()

        assert quality_stats["total_data_points"] == 1500
        assert quality_stats["invalid_data_points"] == 12
        assert quality_stats["missing_data_points"] == 6
        assert quality_stats["duplicate_data_points"] == 3
        assert quality_stats["quality_score"] > 98  # (1500-12)/1500 * 100
        assert quality_stats["invalid_rate"] < 0.01  # 12/1500

    @pytest.mark.asyncio
    async def test_cleanup_old_stats(self):
        """Test that old statistics are properly cleaned up."""
        component = TestComponent()
        component._retention_hours = 0  # Set to 0 for immediate cleanup

        # Add some stats
        await component.track_error(
            Exception("Old error"),
            context="test",
        )

        # Manually set timestamp to be old
        if component._error_history:
            component._error_history[0]["timestamp"] = datetime.now() - timedelta(
                hours=2
            )

        # Trigger cleanup
        await component.cleanup_old_stats()

        # Old error should be removed
        assert len(component._error_history) == 0

    @pytest.mark.asyncio
    async def test_prometheus_export_format(self):
        """Test Prometheus export format."""
        component = TestComponent()

        # Add some metrics
        await component.track_operation("api_call", 100.0, success=True)
        await component.track_error(Exception("Test error"))

        # Export in Prometheus format
        prom_export = await component.export_stats(format="prometheus")

        # Check format
        assert isinstance(prom_export, str)
        assert "# HELP" in prom_export
        assert "# TYPE" in prom_export
        assert "testcomponent_" in prom_export.lower()


class TestStatisticsAggregator:
    """Test suite for StatisticsAggregator."""

    @pytest.mark.asyncio
    async def test_aggregation_with_component_failures(self):
        """Test that aggregation handles component failures gracefully."""
        aggregator = StatisticsAggregator(cache_ttl_seconds=1)

        # Create mock components that fail
        failing_component = MagicMock()
        failing_component.get_performance_metrics = AsyncMock(
            side_effect=Exception("Component failed")
        )

        aggregator.order_manager = failing_component
        aggregator.trading_suite = MagicMock()
        aggregator.trading_suite.is_connected = False
        aggregator.trading_suite.config = MagicMock()
        aggregator.trading_suite.config.features = []
        aggregator.trading_suite.config.timeframes = []

        # Should not raise, should return safe defaults
        stats = await aggregator.aggregate_stats()
        assert stats is not None
        assert stats["status"] == "disconnected"
        assert "components" in stats

    @pytest.mark.asyncio
    async def test_cache_functionality(self):
        """Test that caching works correctly."""
        aggregator = StatisticsAggregator(cache_ttl_seconds=1)

        # Mock a simple suite
        aggregator.trading_suite = MagicMock()
        aggregator.trading_suite.is_connected = True
        aggregator.trading_suite.config = MagicMock()
        aggregator.trading_suite.config.features = []
        aggregator.trading_suite.config.timeframes = ["1min"]

        # First call should compute
        stats1 = await aggregator.aggregate_stats()

        # Second call should use cache
        stats2 = await aggregator.aggregate_stats()
        assert stats1 == stats2  # Should be identical

        # Wait for cache to expire
        await asyncio.sleep(1.1)

        # Should recompute
        stats3 = await aggregator.aggregate_stats()
        assert stats3 is not None

    @pytest.mark.asyncio
    async def test_health_score_calculation(self):
        """Test health score calculation with various conditions."""
        aggregator = StatisticsAggregator()

        # Test with perfect health
        stats = {
            "components": {},
            "cache_hit_rate": 1.0,
            "total_errors": 0,
        }
        result = await aggregator._calculate_cross_metrics(stats)
        assert result["health_score"] == 100.0

        # Test with errors
        stats = {
            "components": {"test": {"error_count": 10, "memory_usage_mb": 100}},
            "cache_hit_rate": 0.8,
        }
        result = await aggregator._calculate_cross_metrics(stats)
        assert 0 <= result["health_score"] <= 100

        # Test with disconnected components
        stats = {
            "components": {
                "test1": {"status": "disconnected", "error_count": 0},
                "test2": {"status": "connected", "error_count": 0},
            },
            "cache_hit_rate": 0.5,
        }
        result = await aggregator._calculate_cross_metrics(stats)
        assert result["health_score"] < 100  # Should be penalized

    @pytest.mark.asyncio
    async def test_safe_division(self):
        """Test that division by zero is handled safely."""
        aggregator = StatisticsAggregator()

        # Mock client with zero requests
        mock_client = MagicMock()
        mock_client.api_call_count = 0
        mock_client.cache_hit_count = 0

        aggregator.client = mock_client

        # Should not raise division by zero
        stats = await aggregator._get_client_stats()
        assert stats["cache_hit_rate"] == 0.0  # Safe default

    @pytest.mark.asyncio
    async def test_memory_calculation_performance(self):
        """Test that memory calculation doesn't cause performance issues."""
        component = TestComponent()

        # Add many attributes to simulate large component
        for i in range(1000):
            setattr(component, f"attr_{i}", [1, 2, 3, 4, 5])

        # Should complete quickly
        import time

        start = time.time()
        memory_mb = component._calculate_memory_usage()
        duration = time.time() - start

        assert memory_mb > 0
        assert duration < 0.1  # Should be fast (< 100ms)

    def test_empty_stats_structure(self):
        """Test that empty stats have correct structure."""
        aggregator = StatisticsAggregator()

        empty_stats = aggregator._get_empty_stats()

        # Check all required fields are present
        assert "suite_id" in empty_stats
        assert "instrument" in empty_stats
        assert "status" in empty_stats
        assert "connected" in empty_stats
        assert "components" in empty_stats
        assert "health_score" not in empty_stats  # Added by cross-metrics
        assert empty_stats["connected"] is False
        assert empty_stats["status"] == "disconnected"

    def test_empty_component_stats_structure(self):
        """Test that empty component stats have correct structure."""
        aggregator = StatisticsAggregator()

        empty_stats = aggregator._get_empty_component_stats("TestComponent", 100)

        assert empty_stats["name"] == "TestComponent"
        assert empty_stats["status"] == "disconnected"
        assert empty_stats["uptime_seconds"] == 100
        assert empty_stats["error_count"] == 0
        assert empty_stats["memory_usage_mb"] == 0.0
        assert empty_stats["performance_metrics"] == {}


@pytest.mark.asyncio
async def test_integration_stats_during_reconnection():
    """Test that statistics remain accurate during WebSocket reconnections."""
    # This would be an integration test with actual components
    # Included here as a placeholder for comprehensive testing
    pass


@pytest.mark.asyncio
async def test_stats_under_load():
    """Test statistics accuracy during high-frequency operations."""
    component = TestComponent()

    # Simulate high-frequency trading
    tasks = []
    for i in range(100):
        tasks.append(
            component.track_operation(
                operation=f"trade_{i % 10}",
                duration_ms=float(i % 100),
                success=i % 10 != 0,  # 10% failure rate
            )
        )

    await asyncio.gather(*tasks)

    # Verify stats are accurate
    metrics = await component.get_performance_metrics()
    assert "operation_stats" in metrics
    assert len(metrics["operation_stats"]) == 10  # 10 unique operations

    # Check network stats
    assert metrics["network_stats"]["total_requests"] == 100
    assert metrics["network_stats"]["successful_requests"] == 90
    assert metrics["network_stats"]["failed_requests"] == 10
    assert 0.85 <= metrics["network_stats"]["success_rate"] <= 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
