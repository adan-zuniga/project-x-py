"""
Dynamic Resource Limits for adaptive buffer sizing and memory management.

Author: @TexasCoding
Date: 2025-08-22

Overview:
    Provides dynamic resource limit management that adapts buffer sizes, cache limits,
    and concurrent task limits based on real-time system resource availability.
    Prevents OOM errors while maximizing performance through intelligent scaling.

Key Features:
    - Real-time system resource monitoring (memory, CPU)
    - Adaptive buffer sizing based on available memory
    - Memory pressure detection and graceful degradation
    - CPU-aware concurrent task limiting
    - Configurable scaling algorithms with manual overrides
    - Performance metrics and resource usage tracking

Adaptive Scaling Strategy:
    - Memory Usage:
        * Normal operation: Use 10-20% of available memory for buffers
        * Memory pressure: Scale down to 5% of available memory
        * High availability: Scale up to 30% of available memory
        * Never exceed configurable hard limits
        * Maintain minimum operational buffers
    - CPU Usage:
        * Scale concurrent tasks based on CPU core count
        * Reduce concurrency under high CPU pressure
        * Prioritize critical operations

Resource Monitoring:
    - Continuous monitoring of system memory and CPU usage
    - Pressure detection using configurable thresholds
    - Automatic adjustment of resource allocation
    - Graceful degradation under resource constraints

Example Usage:
    ```python
    # Initialize with dynamic resource management
    manager = RealtimeDataManager(
        instrument="MNQ",
        project_x=client,
        realtime_client=realtime_client,
        timeframes=["1min", "5min"],
        enable_dynamic_limits=True,
        resource_config={
            "memory_target_percent": 15.0,  # Target 15% of available memory
            "memory_pressure_threshold": 0.8,  # Pressure at 80% memory usage
            "min_buffer_size": 100,  # Minimum buffer size
            "max_buffer_size": 10000,  # Maximum buffer size
        },
    )

    # Monitor resource usage
    resource_stats = await manager.get_resource_stats()
    print(f"Memory pressure: {resource_stats['memory_pressure']:.2f}")
    print(f"Current buffer limits: {resource_stats['current_limits']}")

    # Manual override for production tuning
    await manager.override_resource_limits(
        {
            "max_bars_per_timeframe": 5000,
            "tick_buffer_size": 2000,
        }
    )
    ```

Performance Characteristics:
    - Automatic scaling prevents OOM errors
    - Resource monitoring overhead < 1% CPU
    - Adaptive limits improve performance under varying load
    - Graceful degradation maintains core functionality
    - Manual overrides allow production fine-tuning

Configuration:
    - memory_target_percent: Target percentage of available memory (default: 15.0)
    - memory_pressure_threshold: Memory pressure detection threshold (default: 0.8)
    - cpu_pressure_threshold: CPU pressure detection threshold (default: 0.8)
    - scaling_factor: Buffer scaling factor during pressure (default: 0.5)
    - monitoring_interval: Resource monitoring interval in seconds (default: 30.0)

See Also:
    - `realtime_data_manager.memory_management.MemoryManagementMixin`
    - `types.config_types.MemoryManagementConfig`
"""

import asyncio
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore[assignment]

import contextlib

from project_x_py.utils.task_management import TaskManagerMixin

if TYPE_CHECKING:
    from asyncio import Lock
    from collections.abc import Callable

    from project_x_py.utils.lock_optimization import AsyncRWLock

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Current resource limits for dynamic scaling."""

    max_bars_per_timeframe: int
    tick_buffer_size: int
    max_concurrent_tasks: int
    cache_size_limit: int
    memory_limit_mb: float

    # Scaling metadata
    memory_pressure: float = 0.0
    cpu_pressure: float = 0.0
    last_updated: float = field(default_factory=time.time)
    scaling_reason: str = "initial"


@dataclass
class SystemResources:
    """Current system resource availability."""

    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float

    cpu_count: int
    cpu_percent: float

    # Process-specific
    process_memory_mb: float
    process_cpu_percent: float

    timestamp: float = field(default_factory=time.time)


@dataclass
class ResourceConfig:
    """Configuration for dynamic resource management."""

    # Memory configuration
    memory_target_percent: float = 15.0  # Target % of available memory
    memory_pressure_threshold: float = 0.8  # Pressure detection threshold
    memory_scale_down_factor: float = 0.5  # Scale down factor under pressure
    memory_scale_up_factor: float = 1.5  # Scale up factor when abundant

    # CPU configuration
    cpu_pressure_threshold: float = 0.8  # CPU pressure threshold
    cpu_scale_down_factor: float = 0.7  # Concurrent task reduction factor

    # Buffer limits
    min_buffer_size: int = 100  # Minimum operational buffer size
    max_buffer_size: int = 50000  # Hard maximum buffer size
    min_tick_buffer: int = 50  # Minimum tick buffer size
    max_tick_buffer: int = 10000  # Hard maximum tick buffer size

    # Cache limits
    min_cache_size: int = 50  # Minimum cache entries
    max_cache_size: int = 5000  # Maximum cache entries

    # Monitoring configuration
    monitoring_interval: float = 30.0  # Resource monitoring interval
    pressure_history_size: int = 10  # Number of pressure readings to keep

    # Manual overrides
    manual_overrides: dict[str, Any] = field(default_factory=dict)
    override_expiry: float | None = None  # Override expiry timestamp


class DynamicResourceMixin(TaskManagerMixin):
    """
    Mixin for dynamic resource limit management and adaptive buffer sizing.

    Provides intelligent scaling of buffer sizes, cache limits, and concurrent task
    limits based on real-time system resource availability. Implements memory pressure
    detection and graceful degradation to prevent OOM errors while maximizing performance.
    """

    # Type hints for mypy
    if TYPE_CHECKING:
        logger: logging.Logger
        max_bars_per_timeframe: int
        tick_buffer_size: int
        memory_stats: dict[str, Any]
        data_lock: "Lock | AsyncRWLock"
        data_rw_lock: AsyncRWLock
        is_running: bool

    def __init__(self) -> None:
        """Initialize dynamic resource management."""
        super().__init__()

        # Resource monitoring
        self._resource_config = ResourceConfig()
        self._current_limits: ResourceLimits | None = None
        self._system_resources: SystemResources | None = None
        self._monitoring_task: asyncio.Task[None] | None = None

        # Resource history for trend analysis
        self._memory_pressure_history: deque[float] = deque(
            maxlen=self._resource_config.pressure_history_size
        )
        self._cpu_pressure_history: deque[float] = deque(
            maxlen=self._resource_config.pressure_history_size
        )

        # Statistics tracking
        self._resource_stats = {
            "resource_adjustments": 0,
            "pressure_events": 0,
            "scale_down_events": 0,
            "scale_up_events": 0,
            "override_events": 0,
            "monitoring_errors": 0,
        }

        # Change notification callbacks
        self._resource_change_callbacks: list[Callable[[ResourceLimits], None]] = []

        # Process reference for monitoring
        self._process = (
            psutil.Process() if PSUTIL_AVAILABLE and psutil is not None else None
        )

        # Fallback system info if psutil unavailable
        if not PSUTIL_AVAILABLE:
            self.logger.warning(
                "psutil not available - using fallback resource monitoring. "
                "Install psutil for optimal resource management."
            )

    def configure_dynamic_resources(
        self,
        memory_target_percent: float | None = None,
        memory_pressure_threshold: float | None = None,
        cpu_pressure_threshold: float | None = None,
        monitoring_interval: float | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Configure dynamic resource management parameters.

        Args:
            memory_target_percent: Target percentage of available memory to use
            memory_pressure_threshold: Memory pressure detection threshold (0-1)
            cpu_pressure_threshold: CPU pressure detection threshold (0-1)
            monitoring_interval: Resource monitoring interval in seconds
            **kwargs: Additional configuration parameters
        """
        if memory_target_percent is not None:
            self._resource_config.memory_target_percent = max(
                1.0, min(50.0, memory_target_percent)
            )

        if memory_pressure_threshold is not None:
            self._resource_config.memory_pressure_threshold = max(
                0.1, min(1.0, memory_pressure_threshold)
            )

        if cpu_pressure_threshold is not None:
            self._resource_config.cpu_pressure_threshold = max(
                0.1, min(1.0, cpu_pressure_threshold)
            )

        if monitoring_interval is not None:
            self._resource_config.monitoring_interval = max(10.0, monitoring_interval)

        # Apply additional configuration
        for key, value in kwargs.items():
            if hasattr(self._resource_config, key):
                setattr(self._resource_config, key, value)

        self.logger.info(
            f"Dynamic resource configuration updated: "
            f"memory_target={self._resource_config.memory_target_percent}%, "
            f"memory_pressure={self._resource_config.memory_pressure_threshold}, "
            f"monitoring_interval={self._resource_config.monitoring_interval}s"
        )

    async def _get_system_resources(self) -> SystemResources:
        """
        Get current system resource availability.

        Returns:
            SystemResources object with current system state
        """
        if not PSUTIL_AVAILABLE:
            return await self._get_fallback_resources()

        try:
            if not PSUTIL_AVAILABLE or psutil is None:
                raise ImportError("psutil not available")

            # System memory
            memory = psutil.virtual_memory()

            # System CPU
            cpu_count = psutil.cpu_count() or 4
            cpu_percent = psutil.cpu_percent(interval=0.1) or 0.0

            # Process-specific resources
            if self._process is not None:
                process_info = self._process.memory_info()
                process_memory_mb = process_info.rss / (1024 * 1024)
                process_cpu_percent = self._process.cpu_percent() or 0.0
            else:
                process_memory_mb = 0.0
                process_cpu_percent = 0.0

            return SystemResources(
                total_memory_mb=memory.total / (1024 * 1024),
                available_memory_mb=memory.available / (1024 * 1024),
                used_memory_mb=memory.used / (1024 * 1024),
                memory_percent=memory.percent,
                cpu_count=cpu_count,
                cpu_percent=cpu_percent,
                process_memory_mb=process_memory_mb,
                process_cpu_percent=process_cpu_percent,
            )

        except Exception as e:
            self.logger.warning(f"Error getting system resources: {e}")
            return await self._get_fallback_resources()

    async def _get_fallback_resources(self) -> SystemResources:
        """
        Get fallback resource information when psutil is unavailable.

        Returns:
            SystemResources with estimated values
        """
        # Estimate system resources based on common defaults
        estimated_memory_gb = 8  # Conservative estimate
        estimated_cpu_count = os.cpu_count() or 4

        return SystemResources(
            total_memory_mb=estimated_memory_gb * 1024,
            available_memory_mb=estimated_memory_gb * 512,  # Assume 50% available
            used_memory_mb=estimated_memory_gb * 512,
            memory_percent=50.0,
            cpu_count=estimated_cpu_count,
            cpu_percent=25.0,  # Conservative CPU usage estimate
            process_memory_mb=100.0,  # Estimate process memory
            process_cpu_percent=5.0,  # Estimate process CPU
        )

    def _calculate_memory_pressure(self, resources: SystemResources) -> float:
        """
        Calculate memory pressure based on system and process memory usage.

        Args:
            resources: Current system resources

        Returns:
            Memory pressure value (0-1, where 1 is maximum pressure)
        """
        # System memory pressure
        system_pressure = resources.memory_percent / 100.0

        # Process memory pressure (relative to available memory)
        process_pressure = min(
            1.0, resources.process_memory_mb / resources.available_memory_mb
        )

        # Combined pressure with system memory weighted more heavily
        combined_pressure = (system_pressure * 0.7) + (process_pressure * 0.3)

        return min(1.0, combined_pressure)

    def _calculate_cpu_pressure(self, resources: SystemResources) -> float:
        """
        Calculate CPU pressure based on system and process CPU usage.

        Args:
            resources: Current system resources

        Returns:
            CPU pressure value (0-1, where 1 is maximum pressure)
        """
        # System CPU pressure
        system_pressure = resources.cpu_percent / 100.0

        # Process CPU pressure (relative to single core)
        process_pressure = min(1.0, resources.process_cpu_percent / 100.0)

        # Combined pressure
        combined_pressure = max(system_pressure, process_pressure * 0.5)

        return min(1.0, combined_pressure)

    def _calculate_adaptive_limits(
        self, resources: SystemResources, memory_pressure: float, cpu_pressure: float
    ) -> ResourceLimits:
        """
        Calculate adaptive resource limits based on current system state.

        Args:
            resources: Current system resources
            memory_pressure: Current memory pressure (0-1)
            cpu_pressure: Current CPU pressure (0-1)

        Returns:
            New resource limits
        """
        config = self._resource_config

        # Base calculations
        target_memory_mb = resources.available_memory_mb * (
            config.memory_target_percent / 100.0
        )

        # Memory scaling based on pressure
        memory_scale_factor = 1.0
        scaling_reason = "normal"

        if memory_pressure > config.memory_pressure_threshold:
            # Scale down under pressure
            memory_scale_factor = config.memory_scale_down_factor
            scaling_reason = "memory_pressure"
        elif (
            memory_pressure < 0.3 and resources.available_memory_mb > 2048
        ):  # Abundant memory
            # Scale up when memory is abundant
            memory_scale_factor = config.memory_scale_up_factor
            scaling_reason = "abundant_memory"

        # Calculate buffer sizes
        scaled_memory_mb = target_memory_mb * memory_scale_factor

        # Estimate bars per MB (rough approximation)
        bars_per_mb = 1000  # Conservative estimate
        target_bars = int(scaled_memory_mb * bars_per_mb)

        # Apply limits and constraints
        max_bars = max(config.min_buffer_size, min(config.max_buffer_size, target_bars))

        # Tick buffer sizing (smaller than main buffer)
        tick_buffer = max(
            config.min_tick_buffer, min(config.max_tick_buffer, max_bars // 10)
        )

        # Concurrent task limits based on CPU
        base_concurrent_tasks = resources.cpu_count * 2
        if cpu_pressure > config.cpu_pressure_threshold:
            concurrent_tasks = max(
                1, int(base_concurrent_tasks * config.cpu_scale_down_factor)
            )
        else:
            concurrent_tasks = base_concurrent_tasks

        # Cache size based on available memory
        cache_size = max(
            config.min_cache_size,
            min(config.max_cache_size, int(scaled_memory_mb / 10)),
        )

        return ResourceLimits(
            max_bars_per_timeframe=max_bars,
            tick_buffer_size=tick_buffer,
            max_concurrent_tasks=concurrent_tasks,
            cache_size_limit=cache_size,
            memory_limit_mb=scaled_memory_mb,
            memory_pressure=memory_pressure,
            cpu_pressure=cpu_pressure,
            scaling_reason=scaling_reason,
        )

    async def _apply_resource_limits(self, new_limits: ResourceLimits) -> None:
        """
        Apply new resource limits to the component.

        Args:
            new_limits: New resource limits to apply
        """
        # Check for manual overrides
        if self._resource_config.manual_overrides:
            # Check if overrides have expired
            if (
                self._resource_config.override_expiry
                and time.time() > self._resource_config.override_expiry
            ):
                self._resource_config.manual_overrides.clear()
                self._resource_config.override_expiry = None
                self.logger.info("Manual resource overrides expired")
            else:
                # Apply manual overrides
                for key, value in self._resource_config.manual_overrides.items():
                    if hasattr(new_limits, key):
                        setattr(new_limits, key, value)
                        new_limits.scaling_reason = "manual_override"

        # Update component attributes if they exist
        if hasattr(self, "max_bars_per_timeframe"):
            old_max_bars = self.max_bars_per_timeframe
            self.max_bars_per_timeframe = new_limits.max_bars_per_timeframe

            if old_max_bars != new_limits.max_bars_per_timeframe:
                self.logger.debug(
                    f"Updated max_bars_per_timeframe: {old_max_bars} -> {new_limits.max_bars_per_timeframe}"
                )

        if hasattr(self, "tick_buffer_size"):
            old_tick_buffer = self.tick_buffer_size
            self.tick_buffer_size = new_limits.tick_buffer_size

            if old_tick_buffer != new_limits.tick_buffer_size:
                self.logger.debug(
                    f"Updated tick_buffer_size: {old_tick_buffer} -> {new_limits.tick_buffer_size}"
                )

        # Update internal limits tracking
        self._current_limits = new_limits

        # Update statistics
        self._resource_stats["resource_adjustments"] += 1

        if new_limits.scaling_reason == "memory_pressure":
            self._resource_stats["scale_down_events"] += 1
            self._resource_stats["pressure_events"] += 1
        elif new_limits.scaling_reason == "abundant_memory":
            self._resource_stats["scale_up_events"] += 1
        elif new_limits.scaling_reason == "manual_override":
            self._resource_stats["override_events"] += 1

        # Notify callbacks
        for callback in self._resource_change_callbacks:
            try:
                callback(new_limits)
            except Exception as e:
                self.logger.error(f"Error in resource change callback: {e}")

    async def _monitor_resources(self) -> None:
        """Background task for continuous resource monitoring and adjustment."""
        while self.is_running:
            try:
                # Get current system resources
                resources = await self._get_system_resources()
                self._system_resources = resources

                # Calculate pressure metrics
                memory_pressure = self._calculate_memory_pressure(resources)
                cpu_pressure = self._calculate_cpu_pressure(resources)

                # Update pressure history
                self._memory_pressure_history.append(memory_pressure)
                self._cpu_pressure_history.append(cpu_pressure)

                # Calculate new limits
                new_limits = self._calculate_adaptive_limits(
                    resources, memory_pressure, cpu_pressure
                )

                # Apply limits if they've changed significantly
                if not self._current_limits or self._should_update_limits(
                    self._current_limits, new_limits
                ):
                    await self._apply_resource_limits(new_limits)

                # Update memory stats
                if hasattr(self, "memory_stats"):
                    self.memory_stats.update(
                        {
                            "system_memory_mb": resources.total_memory_mb,
                            "available_memory_mb": resources.available_memory_mb,
                            "memory_pressure": memory_pressure,
                            "cpu_pressure": cpu_pressure,
                            "resource_scaling_active": True,
                        }
                    )

                await asyncio.sleep(self._resource_config.monitoring_interval)

            except asyncio.CancelledError:
                self.logger.debug("Resource monitoring task cancelled")
                raise
            except Exception as e:
                self.logger.error(f"Error in resource monitoring: {e}")
                self._resource_stats["monitoring_errors"] += 1
                await asyncio.sleep(self._resource_config.monitoring_interval)

    def _should_update_limits(
        self, current: ResourceLimits, new: ResourceLimits
    ) -> bool:
        """
        Check if resource limits should be updated based on change threshold.

        Args:
            current: Current resource limits
            new: New calculated resource limits

        Returns:
            True if limits should be updated
        """
        # Check for significant changes (>10% change or pressure events)
        buffer_change = (
            abs(current.max_bars_per_timeframe - new.max_bars_per_timeframe)
            / current.max_bars_per_timeframe
        )
        tick_change = (
            abs(current.tick_buffer_size - new.tick_buffer_size)
            / current.tick_buffer_size
        )

        significant_change = buffer_change > 0.1 or tick_change > 0.1
        pressure_change = (new.memory_pressure > 0.8 or new.cpu_pressure > 0.8) and (
            current.memory_pressure <= 0.8 and current.cpu_pressure <= 0.8
        )

        return (
            significant_change
            or pressure_change
            or new.scaling_reason == "manual_override"
        )

    async def override_resource_limits(
        self, overrides: dict[str, Any], duration_seconds: float | None = None
    ) -> None:
        """
        Manually override resource limits for production tuning.

        Args:
            overrides: Dictionary of resource limit overrides
            duration_seconds: How long to maintain overrides (None = permanent)
        """
        self._resource_config.manual_overrides.update(overrides)

        if duration_seconds:
            self._resource_config.override_expiry = time.time() + duration_seconds
        else:
            self._resource_config.override_expiry = None

        # Update override statistics
        self._resource_stats["override_events"] += 1

        # Apply overrides immediately
        if self._current_limits:
            new_limits = ResourceLimits(**self._current_limits.__dict__)
            for key, value in overrides.items():
                if hasattr(new_limits, key):
                    setattr(new_limits, key, value)
            new_limits.scaling_reason = "manual_override"
            await self._apply_resource_limits(new_limits)

        self.logger.info(
            f"Applied manual resource overrides: {overrides}"
            f"{f' for {duration_seconds}s' if duration_seconds else ''}"
        )

    def add_resource_change_callback(
        self, callback: "Callable[[ResourceLimits], None]"
    ) -> None:
        """
        Add callback to be notified of resource limit changes.

        Args:
            callback: Function to call when limits change
        """
        self._resource_change_callbacks.append(callback)

    def remove_resource_change_callback(
        self, callback: "Callable[[ResourceLimits], None]"
    ) -> None:
        """
        Remove resource change callback.

        Args:
            callback: Function to remove
        """
        if callback in self._resource_change_callbacks:
            self._resource_change_callbacks.remove(callback)

    async def get_resource_stats(self) -> dict[str, Any]:
        """
        Get comprehensive resource management statistics.

        Returns:
            Dictionary with resource statistics and current state
        """
        current_resources = self._system_resources
        current_limits = self._current_limits

        stats: dict[str, Any] = {
            "dynamic_limits_enabled": True,
            "psutil_available": PSUTIL_AVAILABLE,
            "resource_adjustments": self._resource_stats["resource_adjustments"],
            "pressure_events": self._resource_stats["pressure_events"],
            "scale_down_events": self._resource_stats["scale_down_events"],
            "scale_up_events": self._resource_stats["scale_up_events"],
            "override_events": self._resource_stats["override_events"],
            "monitoring_errors": self._resource_stats["monitoring_errors"],
        }

        if current_resources:
            stats["system_resources"] = {
                "total_memory_mb": current_resources.total_memory_mb,
                "available_memory_mb": current_resources.available_memory_mb,
                "memory_percent": current_resources.memory_percent,
                "cpu_count": current_resources.cpu_count,
                "cpu_percent": current_resources.cpu_percent,
                "process_memory_mb": current_resources.process_memory_mb,
                "process_cpu_percent": current_resources.process_cpu_percent,
            }

        if current_limits:
            stats["current_limits"] = {
                "max_bars_per_timeframe": current_limits.max_bars_per_timeframe,
                "tick_buffer_size": current_limits.tick_buffer_size,
                "max_concurrent_tasks": current_limits.max_concurrent_tasks,
                "cache_size_limit": current_limits.cache_size_limit,
                "memory_limit_mb": current_limits.memory_limit_mb,
                "memory_pressure": current_limits.memory_pressure,
                "cpu_pressure": current_limits.cpu_pressure,
                "scaling_reason": current_limits.scaling_reason,
                "last_updated": current_limits.last_updated,
            }

        if self._memory_pressure_history:
            stats["pressure_history"] = {
                "memory_pressure": list(self._memory_pressure_history),
                "cpu_pressure": list(self._cpu_pressure_history),
                "avg_memory_pressure": sum(self._memory_pressure_history)
                / len(self._memory_pressure_history),
                "avg_cpu_pressure": sum(self._cpu_pressure_history)
                / len(self._cpu_pressure_history),
            }

        stats["configuration"] = {
            "memory_target_percent": self._resource_config.memory_target_percent,
            "memory_pressure_threshold": self._resource_config.memory_pressure_threshold,
            "cpu_pressure_threshold": self._resource_config.cpu_pressure_threshold,
            "monitoring_interval": self._resource_config.monitoring_interval,
            "manual_overrides": self._resource_config.manual_overrides.copy(),
            "override_expiry": self._resource_config.override_expiry,
        }

        return stats

    def start_resource_monitoring(self) -> None:
        """Start the background resource monitoring task."""
        if not self._monitoring_task or self._monitoring_task.done():
            self._monitoring_task = self._create_task(
                self._monitor_resources(), name="resource_monitoring", persistent=True
            )
            self.logger.info("Started dynamic resource monitoring")

    async def stop_resource_monitoring(self) -> None:
        """Stop the background resource monitoring task."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitoring_task
            self._monitoring_task = None
            self.logger.info("Stopped dynamic resource monitoring")
