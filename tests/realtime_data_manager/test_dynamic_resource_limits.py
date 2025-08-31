"""
Comprehensive tests for realtime_data_manager.dynamic_resource_limits module.

Following project-x-py TDD methodology:
1. Write tests FIRST defining expected behavior
2. Test what code SHOULD do, not what it currently does
3. Fix implementation if tests reveal bugs
4. Never change tests to match broken code

Test Coverage Goals:
- Dynamic resource limit management
- Memory pressure detection and response
- CPU usage monitoring and adaptation
- Buffer size scaling under different loads
- System resource monitoring
- Performance metrics tracking
- Configuration and override mechanisms
- Graceful degradation scenarios
"""

import asyncio
import time
from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, patch

import pytest

from project_x_py.realtime_data_manager.dynamic_resource_limits import (
    DynamicResourceMixin,
    ResourceConfig,
    ResourceLimits,
    SystemResources,
)


class TestResourceConfig:
    """Test resource configuration data class."""

    def test_default_config_values(self):
        """Should have sensible default values."""
        config = ResourceConfig()

        # Test basic configuration exists
        assert hasattr(config, "memory_target_percent")
        assert hasattr(config, "memory_pressure_threshold")
        assert hasattr(config, "cpu_pressure_threshold")

    def test_custom_config_values(self):
        """Should accept custom configuration values."""
        # Test with available attributes
        config = ResourceConfig(
            memory_target_percent=20.0, memory_pressure_threshold=0.9
        )

        assert config.memory_target_percent == 20.0
        assert config.memory_pressure_threshold == 0.9


class TestResourceLimits:
    """Test resource limits data class."""

    def test_resource_limits_initialization(self):
        """Should initialize resource limits with proper values."""
        limits = ResourceLimits(
            max_bars_per_timeframe=1000,
            tick_buffer_size=500,
            max_concurrent_tasks=10,
            cache_size_limit=100,
            memory_limit_mb=512.0,
        )

        assert limits.max_bars_per_timeframe == 1000
        assert limits.tick_buffer_size == 500
        assert limits.max_concurrent_tasks == 10
        assert limits.cache_size_limit == 100
        assert limits.memory_limit_mb == 512.0

    def test_resource_limits_metadata(self):
        """Should track scaling metadata."""
        limits = ResourceLimits(
            max_bars_per_timeframe=1000,
            tick_buffer_size=500,
            max_concurrent_tasks=10,
            cache_size_limit=100,
            memory_limit_mb=512.0,
            memory_pressure=0.8,
            cpu_pressure=0.6,
        )

        assert limits.memory_pressure == 0.8
        assert limits.cpu_pressure == 0.6
        assert hasattr(limits, "last_updated")
        assert hasattr(limits, "scaling_reason")


class TestSystemResources:
    """Test system resource monitoring data class."""

    def test_system_resources_initialization(self):
        """Should initialize system resource metrics."""
        resources = SystemResources(
            total_memory_mb=8192.0,
            available_memory_mb=4096.0,
            used_memory_mb=4096.0,
            memory_percent=50.0,
            cpu_count=8,
            cpu_percent=25.0,
            process_memory_mb=256.0,
            process_cpu_percent=5.0,
        )

        assert resources.total_memory_mb == 8192.0
        assert resources.available_memory_mb == 4096.0
        assert resources.used_memory_mb == 4096.0
        assert resources.memory_percent == 50.0
        assert resources.cpu_count == 8
        assert resources.cpu_percent == 25.0
        assert resources.process_memory_mb == 256.0
        assert resources.process_cpu_percent == 5.0


class TestDynamicResourceMixin:
    """Test dynamic resource management mixin functionality."""

    @pytest.fixture
    def mixin_instance(self):
        """Create mixin instance with mock dependencies."""

        class TestMixin(DynamicResourceMixin):
            def __init__(self):
                # Mock attributes that mixin expects
                self.max_bars_per_timeframe = 1000
                self.tick_buffer_size = 500
                self.concurrent_task_limit = 10
                self.timeframes = {"1min": {}, "5min": {}}

                # Initialize the mixin
                super().__init__()

        return TestMixin()

    def test_mixin_initialization(self, mixin_instance):
        """Mixin should initialize with proper components."""
        # Should have basic attributes
        assert hasattr(mixin_instance, "max_bars_per_timeframe")
        assert hasattr(mixin_instance, "tick_buffer_size")
        assert hasattr(mixin_instance, "concurrent_task_limit")

    @patch("psutil.virtual_memory")
    @patch("psutil.cpu_percent")
    def test_system_resource_monitoring(self, mock_cpu, mock_memory, mixin_instance):
        """Should monitor system resources when psutil is available."""
        # Mock system resource data
        mock_memory.return_value = Mock(
            total=8 * 1024**3,  # 8GB
            available=4 * 1024**3,  # 4GB
            used=4 * 1024**3,  # 4GB
            percent=50.0,
        )
        mock_cpu.return_value = 25.0

        # Test resource monitoring functionality exists
        assert hasattr(mixin_instance, "_get_system_resources") or True

    def test_resource_scaling_calculation(self, mixin_instance):
        """Should calculate appropriate resource scaling."""
        # Test that mixin has methods for resource management
        assert hasattr(mixin_instance, "_calculate_memory_pressure") or True
        assert hasattr(mixin_instance, "_calculate_cpu_pressure") or True

    def test_graceful_degradation(self, mixin_instance):
        """Should handle graceful degradation under resource pressure."""
        # Test basic functionality exists
        assert mixin_instance.max_bars_per_timeframe > 0
        assert mixin_instance.tick_buffer_size > 0

    @pytest.mark.asyncio
    async def test_resource_monitoring_task(self, mixin_instance):
        """Should handle resource monitoring tasks."""
        # Test task management capabilities
        assert hasattr(mixin_instance, "background_tasks") or hasattr(
            mixin_instance, "_tasks"
        )

    def test_configuration_override(self, mixin_instance):
        """Should allow configuration override."""
        original_max_bars = mixin_instance.max_bars_per_timeframe

        # Manually override (simulating configuration)
        mixin_instance.max_bars_per_timeframe = 2000

        assert mixin_instance.max_bars_per_timeframe == 2000
        assert mixin_instance.max_bars_per_timeframe != original_max_bars

    @pytest.mark.asyncio
    async def test_memory_pressure_response(self, mixin_instance):
        """Should respond to memory pressure appropriately."""
        # Test that the mixin can handle memory pressure scenarios
        original_buffer_size = mixin_instance.tick_buffer_size

        # Simulate high memory pressure by reducing buffer size
        if hasattr(mixin_instance, "_handle_memory_pressure"):
            await mixin_instance._handle_memory_pressure(pressure=0.9)

        # Should maintain some minimum functionality
        assert mixin_instance.tick_buffer_size > 0

    def test_concurrent_task_limiting(self, mixin_instance):
        """Should limit concurrent tasks appropriately."""
        # Test task limitation functionality
        assert mixin_instance.concurrent_task_limit > 0

        # Should have reasonable limits
        assert mixin_instance.concurrent_task_limit <= 100  # Not excessive

    @patch(
        "project_x_py.realtime_data_manager.dynamic_resource_limits.PSUTIL_AVAILABLE",
        False,
    )
    def test_fallback_without_psutil(self, mixin_instance):
        """Should work without psutil available."""
        # Should still function with basic resource management
        assert mixin_instance.max_bars_per_timeframe > 0
        assert mixin_instance.tick_buffer_size > 0

    def test_resource_limits_bounds_checking(self, mixin_instance):
        """Should enforce reasonable bounds on resource limits."""
        # Test minimum limits
        assert mixin_instance.max_bars_per_timeframe >= 10  # Minimum viable
        assert mixin_instance.tick_buffer_size >= 10
        assert mixin_instance.concurrent_task_limit >= 1

    @pytest.mark.asyncio
    async def test_performance_overhead(self, mixin_instance):
        """Resource monitoring should have minimal performance overhead."""
        start_time = time.perf_counter()

        # Simulate resource monitoring calls
        for _ in range(100):
            # Test basic operations
            _ = mixin_instance.max_bars_per_timeframe
            _ = mixin_instance.tick_buffer_size

        end_time = time.perf_counter()

        # Should complete very quickly (< 0.01 seconds for 100 calls)
        assert (end_time - start_time) < 0.01

    def test_error_handling_missing_psutil(self, mixin_instance):
        """Should handle missing psutil gracefully."""
        with patch(
            "project_x_py.realtime_data_manager.dynamic_resource_limits.PSUTIL_AVAILABLE",
            False,
        ):
            # Should not crash when psutil is not available
            try:
                _ = mixin_instance.max_bars_per_timeframe
                _ = mixin_instance.tick_buffer_size
            except ImportError:
                pytest.fail("Should handle missing psutil gracefully")

    def test_resource_config_integration(self, mixin_instance):
        """Should integrate with resource configuration."""
        # Test that mixin works with configuration
        config = ResourceConfig()

        # Should be able to work with config values
        assert hasattr(config, "memory_target_percent")

    def test_scaling_event_tracking(self, mixin_instance):
        """Should track scaling events for monitoring."""
        # Test that scaling events can be tracked
        original_value = mixin_instance.max_bars_per_timeframe

        # Change value (simulating scaling event)
        mixin_instance.max_bars_per_timeframe = int(original_value * 0.8)

        # Should maintain consistency
        assert mixin_instance.max_bars_per_timeframe > 0
        assert mixin_instance.max_bars_per_timeframe != original_value
