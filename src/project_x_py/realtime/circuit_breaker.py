"""
Circuit Breaker pattern for event processing in the project-x-py SDK realtime module.

Author: @TexasCoding
Date: 2025-08-22

Overview:
    Implements a comprehensive Circuit Breaker pattern to protect against cascading failures
    in event processing. The circuit breaker monitors event handler performance and
    automatically fails fast when thresholds are exceeded, providing fallback mechanisms
    and automatic recovery.

Key Features:
    - Three-state circuit breaker: CLOSED, OPEN, HALF_OPEN
    - Configurable failure thresholds and time windows
    - Exponential backoff for recovery attempts
    - Async-first design with proper task management
    - Integration with EventBus and existing event handling
    - Comprehensive metrics and health monitoring
    - Fallback handlers for graceful degradation
    - Protection against various failure modes

Circuit States:
    - CLOSED: Normal operation, events processed normally
    - OPEN: Circuit is tripped, events are blocked or redirected to fallback
    - HALF_OPEN: Testing recovery, limited events allowed through

Failure Protection:
    - Event handler exceptions (uncaught errors)
    - Slow event processing (configurable timeouts)
    - Resource exhaustion (memory, connection limits)
    - Downstream service failures
    - High frequency failure patterns

Example Usage:
    ```python
    # Basic usage with mixin
    class MyRealtimeClient(CircuitBreakerMixin):
        def __init__(self):
            super().__init__()
            # Configure circuit breaker
            await self.configure_circuit_breaker(
                failure_threshold=5,
                time_window_seconds=60,
                timeout_seconds=5.0,
                recovery_timeout=30,
            )


    # Register fallback handlers
    async def fallback_handler(event_type: str, data: dict) -> None:
        logger.warning(f"Circuit open, using fallback for {event_type}")


    await client.set_circuit_breaker_fallback("quote_update", fallback_handler)

    # Check circuit state
    state = await client.get_circuit_breaker_state()
    metrics = await client.get_circuit_breaker_metrics()
    ```

Integration:
    - Works with existing EventHandlingMixin
    - Integrates with TaskManagerMixin for task tracking
    - Compatible with EventBus system
    - Maintains backward compatibility

See Also:
    - `realtime.event_handling.EventHandlingMixin`
    - `utils.task_management.TaskManagerMixin`
    - `event_bus.EventBus`
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable, Coroutine
from enum import Enum
from typing import TYPE_CHECKING, Any

from project_x_py.exceptions import ProjectXError
from project_x_py.utils.task_management import TaskManagerMixin

if TYPE_CHECKING:
    pass


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is tripped, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(ProjectXError):
    """Circuit breaker specific errors."""


class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    def __init__(
        self,
        failure_threshold: int = 5,
        time_window_seconds: float = 60.0,
        timeout_seconds: float = 5.0,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        exponential_backoff_multiplier: float = 2.0,
        max_recovery_time: float = 300.0,
        slow_call_threshold: float = 2.0,
    ):
        """
        Initialize circuit breaker configuration.

        Args:
            failure_threshold: Number of failures to trigger circuit opening
            time_window_seconds: Time window for counting failures (sliding window)
            timeout_seconds: Maximum time to wait for event handler completion
            recovery_timeout: Initial timeout before attempting recovery (seconds)
            half_open_max_calls: Maximum calls allowed in half-open state
            exponential_backoff_multiplier: Multiplier for exponential backoff
            max_recovery_time: Maximum recovery timeout (caps exponential backoff)
            slow_call_threshold: Threshold for considering a call "slow" (seconds)
        """
        self.failure_threshold = failure_threshold
        self.time_window_seconds = time_window_seconds
        self.timeout_seconds = timeout_seconds
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.exponential_backoff_multiplier = exponential_backoff_multiplier
        self.max_recovery_time = max_recovery_time
        self.slow_call_threshold = slow_call_threshold


class CircuitBreakerMetrics:
    """Metrics tracking for circuit breaker."""

    def __init__(self, time_window_seconds: float = 60.0):
        """Initialize metrics with sliding time window."""
        self.time_window_seconds = time_window_seconds

        # Sliding window for failures
        self.failures: deque[float] = deque()
        self.successes: deque[float] = deque()
        self.slow_calls: deque[float] = deque()
        self.timeouts: deque[float] = deque()

        # Counters
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_timeouts = 0
        self.total_slow_calls = 0

        # State tracking
        self.circuit_opened_count = 0
        self.last_failure_time: float | None = None
        self.last_success_time: float | None = None
        self.state_changes: list[tuple[float, CircuitState]] = []

        # Performance metrics
        self.avg_response_time = 0.0
        self.max_response_time = 0.0
        self.min_response_time = float("inf")

    def _clean_old_entries(self, queue: deque[float], current_time: float) -> None:
        """Remove entries older than time window."""
        cutoff_time = current_time - self.time_window_seconds
        while queue and queue[0] < cutoff_time:
            queue.popleft()

    def record_success(self, response_time: float) -> None:
        """Record a successful event processing."""
        current_time = time.time()
        self.successes.append(current_time)
        self._clean_old_entries(self.successes, current_time)

        self.total_calls += 1
        self.total_successes += 1
        self.last_success_time = current_time

        # Update response time metrics
        self._update_response_time_metrics(response_time)

    def record_failure(self, response_time: float | None = None) -> None:
        """Record a failed event processing."""
        current_time = time.time()
        self.failures.append(current_time)
        self._clean_old_entries(self.failures, current_time)

        self.total_calls += 1
        self.total_failures += 1
        self.last_failure_time = current_time

        if response_time is not None:
            self._update_response_time_metrics(response_time)

    def record_timeout(self) -> None:
        """Record a timeout event."""
        current_time = time.time()
        self.timeouts.append(current_time)
        self._clean_old_entries(self.timeouts, current_time)

        self.total_timeouts += 1
        self.record_failure()  # Timeouts are failures

    def record_slow_call(self, response_time: float) -> None:
        """Record a slow call."""
        current_time = time.time()
        self.slow_calls.append(current_time)
        self._clean_old_entries(self.slow_calls, current_time)

        self.total_slow_calls += 1
        self._update_response_time_metrics(response_time)

    def record_state_change(self, new_state: CircuitState) -> None:
        """Record a circuit state change."""
        current_time = time.time()
        self.state_changes.append((current_time, new_state))

        if new_state == CircuitState.OPEN:
            self.circuit_opened_count += 1

    def _update_response_time_metrics(self, response_time: float) -> None:
        """Update response time statistics."""
        self.max_response_time = max(self.max_response_time, response_time)
        self.min_response_time = min(self.min_response_time, response_time)

        # Calculate moving average
        if self.total_calls > 0:
            self.avg_response_time = (
                self.avg_response_time * (self.total_calls - 1) + response_time
            ) / self.total_calls

    def get_failure_rate(self) -> float:
        """Get current failure rate in the time window."""
        current_time = time.time()
        self._clean_old_entries(self.failures, current_time)
        self._clean_old_entries(self.successes, current_time)

        total_calls = len(self.failures) + len(self.successes)
        if total_calls == 0:
            return 0.0

        return len(self.failures) / total_calls

    def get_slow_call_rate(self) -> float:
        """Get current slow call rate in the time window."""
        current_time = time.time()
        self._clean_old_entries(self.slow_calls, current_time)
        self._clean_old_entries(self.successes, current_time)

        total_calls = len(self.slow_calls) + len(self.successes)
        if total_calls == 0:
            return 0.0

        return len(self.slow_calls) / total_calls

    def get_current_window_failures(self) -> int:
        """Get number of failures in current time window."""
        current_time = time.time()
        self._clean_old_entries(self.failures, current_time)
        return len(self.failures)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for export."""
        return {
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_timeouts": self.total_timeouts,
            "total_slow_calls": self.total_slow_calls,
            "circuit_opened_count": self.circuit_opened_count,
            "failure_rate": self.get_failure_rate(),
            "slow_call_rate": self.get_slow_call_rate(),
            "current_window_failures": self.get_current_window_failures(),
            "avg_response_time": self.avg_response_time,
            "max_response_time": self.max_response_time,
            "min_response_time": self.min_response_time
            if self.min_response_time != float("inf")
            else 0.0,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
        }


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting event processing.

    Implements the Circuit Breaker pattern with three states:
    - CLOSED: Normal operation
    - OPEN: Failures detected, circuit is open
    - HALF_OPEN: Testing recovery
    """

    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the circuit for logging and identification
            config: Circuit breaker configuration
            logger: Logger instance for this circuit
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.logger = logger or logging.getLogger(f"{__name__}.{name}")

        # State management
        self.state = CircuitState.CLOSED
        self.last_failure_time: float | None = None
        self.recovery_attempts = 0
        self.half_open_calls = 0

        # Metrics
        self.metrics = CircuitBreakerMetrics(self.config.time_window_seconds)

        # Fallback handlers
        self.fallback_handlers: dict[str, Callable[..., Coroutine[Any, Any, None]]] = {}

        # Locks for thread safety
        self._state_lock = asyncio.Lock()

    async def call(
        self,
        event_type: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function with circuit breaker protection.

        Args:
            event_type: Type of event being processed
            func: Async function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerError: If circuit is open and no fallback available
        """
        async with self._state_lock:
            # Check if circuit allows calls
            if not await self._can_execute():
                return await self._handle_open_circuit(event_type, *args, **kwargs)

            # Mark as half-open call if needed
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1

        # Execute the function with timeout and metrics
        start_time = time.time()
        try:
            # Execute with timeout protection
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.config.timeout_seconds
            )

            if result is None:
                # Handle case where function doesn't return a value
                pass

            response_time = time.time() - start_time

            # Record success and check if slow
            if response_time > self.config.slow_call_threshold:
                self.metrics.record_slow_call(response_time)
                self.logger.warning(
                    f"Circuit {self.name}: Slow call detected for {event_type} "
                    f"({response_time:.2f}s > {self.config.slow_call_threshold}s)"
                )
            else:
                self.metrics.record_success(response_time)

            # Handle successful call in half-open state
            if self.state == CircuitState.HALF_OPEN:
                await self._handle_half_open_success()

            return result

        except TimeoutError:
            response_time = time.time() - start_time
            self.metrics.record_timeout()
            self.logger.error(
                f"Circuit {self.name}: Timeout processing {event_type} "
                f"after {self.config.timeout_seconds}s"
            )
            await self._handle_failure(event_type, "timeout")
            raise CircuitBreakerError(
                f"Event processing timeout for {event_type} "
                f"after {self.config.timeout_seconds}s"
            ) from None

        except Exception as e:
            response_time = time.time() - start_time
            self.metrics.record_failure(response_time)
            self.logger.error(
                f"Circuit {self.name}: Error processing {event_type}: {e}",
                exc_info=True,
            )
            await self._handle_failure(event_type, str(e))
            raise

    async def _can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            # Check if recovery time has passed
            if self.last_failure_time is None:
                return False

            recovery_timeout = self._get_recovery_timeout()
            if time.time() - self.last_failure_time >= recovery_timeout:
                await self._transition_to_half_open()
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self.half_open_calls < self.config.half_open_max_calls
        else:
            # This should never happen, but handle it defensively
            return False

    async def _handle_open_circuit(
        self, event_type: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Handle requests when circuit is open."""
        # Try fallback handler
        if event_type in self.fallback_handlers:
            try:
                return await self.fallback_handlers[event_type](*args, **kwargs)
            except Exception as e:
                self.logger.error(
                    f"Circuit {self.name}: Fallback handler failed for {event_type}: {e}"
                )

        # No fallback available, raise error
        raise CircuitBreakerError(
            f"Circuit breaker {self.name} is OPEN for {event_type}. "
            f"Recovery timeout: {self._get_recovery_timeout():.1f}s"
        )

    async def _handle_failure(self, _event_type: str, _error: str) -> None:
        """Handle a failure and potentially trip the circuit."""
        self.last_failure_time = time.time()

        # Check if we should trip the circuit
        if (
            self.state == CircuitState.CLOSED
            and self.metrics.get_current_window_failures()
            >= self.config.failure_threshold
        ):
            await self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state trips the circuit
            await self._transition_to_open()

    async def _handle_half_open_success(self) -> None:
        """Handle a successful call in half-open state."""
        if self.half_open_calls >= self.config.half_open_max_calls:
            # All test calls succeeded, close the circuit
            await self._transition_to_closed()

    async def _transition_to_open(self) -> None:
        """Transition circuit to OPEN state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.recovery_attempts += 1
        self.metrics.record_state_change(self.state)

        self.logger.warning(
            f"Circuit {self.name}: {old_state.value} -> OPEN "
            f"(failures: {self.metrics.get_current_window_failures()}, "
            f"threshold: {self.config.failure_threshold})"
        )

    async def _transition_to_half_open(self) -> None:
        """Transition circuit to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.metrics.record_state_change(self.state)

        self.logger.info(
            f"Circuit {self.name}: {old_state.value} -> HALF_OPEN "
            f"(attempt {self.recovery_attempts})"
        )

    async def _transition_to_closed(self) -> None:
        """Transition circuit to CLOSED state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.recovery_attempts = 0
        self.half_open_calls = 0
        self.metrics.record_state_change(self.state)

        self.logger.info(
            f"Circuit {self.name}: {old_state.value} -> CLOSED (recovery successful)"
        )

    def _get_recovery_timeout(self) -> float:
        """Calculate recovery timeout with exponential backoff."""
        base_timeout = self.config.recovery_timeout
        backoff_timeout = base_timeout * (
            self.config.exponential_backoff_multiplier ** (self.recovery_attempts - 1)
        )
        return min(backoff_timeout, self.config.max_recovery_time)

    def set_fallback_handler(
        self, event_type: str, handler: Callable[..., Coroutine[Any, Any, None]]
    ) -> None:
        """Set a fallback handler for a specific event type."""
        self.fallback_handlers[event_type] = handler
        self.logger.debug(f"Set fallback handler for {event_type}")

    def remove_fallback_handler(self, event_type: str) -> None:
        """Remove fallback handler for an event type."""
        if event_type in self.fallback_handlers:
            del self.fallback_handlers[event_type]
            self.logger.debug(f"Removed fallback handler for {event_type}")

    async def force_open(self) -> None:
        """Manually force circuit to OPEN state."""
        async with self._state_lock:
            await self._transition_to_open()
            self.logger.warning(f"Circuit {self.name}: Manually forced to OPEN state")

    async def force_closed(self) -> None:
        """Manually force circuit to CLOSED state."""
        async with self._state_lock:
            await self._transition_to_closed()
            self.logger.info(f"Circuit {self.name}: Manually forced to CLOSED state")

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_metrics(self) -> dict[str, Any]:
        """Get comprehensive circuit breaker metrics."""
        base_metrics = self.metrics.to_dict()
        base_metrics.update(
            {
                "name": self.name,
                "state": self.state.value,
                "recovery_attempts": self.recovery_attempts,
                "half_open_calls": self.half_open_calls,
                "recovery_timeout": self._get_recovery_timeout(),
                "fallback_handlers": list(self.fallback_handlers.keys()),
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "time_window_seconds": self.config.time_window_seconds,
                    "timeout_seconds": self.config.timeout_seconds,
                    "recovery_timeout": self.config.recovery_timeout,
                    "half_open_max_calls": self.config.half_open_max_calls,
                },
            }
        )
        return base_metrics


class CircuitBreakerMixin(TaskManagerMixin):
    """
    Mixin to add circuit breaker functionality to event handling classes.

    Provides circuit breaker protection for event processing with configurable
    failure thresholds, timeouts, and fallback mechanisms. Integrates seamlessly
    with existing event handling mixins and the EventBus system.
    """

    # Type hints for attributes expected from main class
    if TYPE_CHECKING:
        logger: logging.Logger
        callbacks: dict[str, list[Callable[..., Any]]]

        async def _trigger_callbacks(
            self, _event_type: str, _data: dict[str, Any]
        ) -> None: ...

    def __init__(self) -> None:
        """Initialize circuit breaker functionality."""
        super().__init__()

        # Circuit breakers per event type
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

        # Global circuit breaker for all events
        self._global_circuit_breaker: CircuitBreaker | None = None

        # Configuration
        self._circuit_breaker_config = CircuitBreakerConfig()

        # Enabled state
        self._circuit_breaker_enabled = False

        # Lock for circuit breaker management
        self._circuit_breaker_lock = asyncio.Lock()

    async def configure_circuit_breaker(
        self,
        failure_threshold: int = 5,
        time_window_seconds: float = 60.0,
        timeout_seconds: float = 5.0,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3,
        exponential_backoff_multiplier: float = 2.0,
        max_recovery_time: float = 300.0,
        slow_call_threshold: float = 2.0,
        enable_global_circuit: bool = True,
        enable_per_event_circuits: bool = True,
    ) -> None:
        """
        Configure circuit breaker settings.

        Args:
            failure_threshold: Number of failures to trigger circuit opening
            time_window_seconds: Time window for counting failures
            timeout_seconds: Maximum time to wait for event handler completion
            recovery_timeout: Initial timeout before attempting recovery
            half_open_max_calls: Maximum calls allowed in half-open state
            exponential_backoff_multiplier: Multiplier for exponential backoff
            max_recovery_time: Maximum recovery timeout
            slow_call_threshold: Threshold for considering a call "slow"
            enable_global_circuit: Enable global circuit breaker for all events
            enable_per_event_circuits: Enable per-event-type circuit breakers
        """
        self._circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            time_window_seconds=time_window_seconds,
            timeout_seconds=timeout_seconds,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
            exponential_backoff_multiplier=exponential_backoff_multiplier,
            max_recovery_time=max_recovery_time,
            slow_call_threshold=slow_call_threshold,
        )

        # Initialize global circuit breaker
        if enable_global_circuit:
            self._global_circuit_breaker = CircuitBreaker(
                "global", self._circuit_breaker_config, self.logger
            )

        self._circuit_breaker_enabled = True
        self.logger.info("Circuit breaker configured and enabled")

    async def enable_circuit_breaker(self) -> None:
        """Enable circuit breaker protection."""
        self._circuit_breaker_enabled = True
        self.logger.info("Circuit breaker protection enabled")

    async def disable_circuit_breaker(self) -> None:
        """Disable circuit breaker protection."""
        self._circuit_breaker_enabled = False
        self.logger.info("Circuit breaker protection disabled")

    async def _get_or_create_circuit_breaker(self, event_type: str) -> CircuitBreaker:
        """Get or create a circuit breaker for an event type."""
        async with self._circuit_breaker_lock:
            if event_type not in self._circuit_breakers:
                self._circuit_breakers[event_type] = CircuitBreaker(
                    f"event_{event_type}", self._circuit_breaker_config, self.logger
                )
            return self._circuit_breakers[event_type]

    async def _trigger_callbacks_with_circuit_breaker(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """
        Trigger callbacks with circuit breaker protection.

        This method wraps the original _trigger_callbacks method with circuit breaker
        protection, providing fault tolerance and automatic recovery.
        """
        if not self._circuit_breaker_enabled:
            # Circuit breaker disabled, use original method
            await self._trigger_callbacks(event_type, data)
            return

        # Use global circuit breaker if available
        if self._global_circuit_breaker:
            try:
                await self._global_circuit_breaker.call(
                    event_type, self._trigger_callbacks, event_type, data
                )
                return
            except CircuitBreakerError:
                self.logger.warning(
                    f"Global circuit breaker blocked {event_type} event processing"
                )
                return

        # Use per-event circuit breaker
        circuit_breaker = await self._get_or_create_circuit_breaker(event_type)
        try:
            await circuit_breaker.call(
                event_type, self._trigger_callbacks, event_type, data
            )
        except CircuitBreakerError:
            self.logger.warning(
                f"Circuit breaker blocked {event_type} event processing"
            )

    async def set_circuit_breaker_fallback(
        self,
        event_type: str,
        fallback_handler: Callable[..., Coroutine[Any, Any, None]],
    ) -> None:
        """
        Set a fallback handler for when circuit breaker is open.

        Args:
            event_type: Event type to set fallback for
            fallback_handler: Async function to call when circuit is open
        """
        circuit_breaker = await self._get_or_create_circuit_breaker(event_type)
        circuit_breaker.set_fallback_handler(event_type, fallback_handler)

        if self._global_circuit_breaker:
            self._global_circuit_breaker.set_fallback_handler(
                event_type, fallback_handler
            )

        self.logger.info(f"Set fallback handler for {event_type}")

    async def remove_circuit_breaker_fallback(self, event_type: str) -> None:
        """Remove fallback handler for an event type."""
        if event_type in self._circuit_breakers:
            self._circuit_breakers[event_type].remove_fallback_handler(event_type)

        if self._global_circuit_breaker:
            self._global_circuit_breaker.remove_fallback_handler(event_type)

        self.logger.info(f"Removed fallback handler for {event_type}")

    async def force_circuit_breaker_open(self, event_type: str | None = None) -> None:
        """
        Manually force circuit breaker to OPEN state.

        Args:
            event_type: Specific event type circuit to open, or None for global
        """
        if event_type is None and self._global_circuit_breaker:
            await self._global_circuit_breaker.force_open()
        elif event_type and event_type in self._circuit_breakers:
            await self._circuit_breakers[event_type].force_open()
        else:
            circuit_breaker = await self._get_or_create_circuit_breaker(
                event_type or "global"
            )
            await circuit_breaker.force_open()

    async def force_circuit_breaker_closed(self, event_type: str | None = None) -> None:
        """
        Manually force circuit breaker to CLOSED state.

        Args:
            event_type: Specific event type circuit to close, or None for global
        """
        if event_type is None and self._global_circuit_breaker:
            await self._global_circuit_breaker.force_closed()
        elif event_type and event_type in self._circuit_breakers:
            await self._circuit_breakers[event_type].force_closed()
        else:
            circuit_breaker = await self._get_or_create_circuit_breaker(
                event_type or "global"
            )
            await circuit_breaker.force_closed()

    async def get_circuit_breaker_state(
        self, event_type: str | None = None
    ) -> CircuitState:
        """
        Get current circuit breaker state.

        Args:
            event_type: Specific event type circuit, or None for global

        Returns:
            Current circuit state
        """
        if event_type is None and self._global_circuit_breaker:
            return self._global_circuit_breaker.get_state()
        elif event_type and event_type in self._circuit_breakers:
            return self._circuit_breakers[event_type].get_state()
        else:
            return CircuitState.CLOSED  # Default state

    async def get_circuit_breaker_metrics(
        self, event_type: str | None = None
    ) -> dict[str, Any]:
        """
        Get circuit breaker metrics.

        Args:
            event_type: Specific event type circuit, or None for global

        Returns:
            Dictionary containing circuit breaker metrics
        """
        if event_type is None and self._global_circuit_breaker:
            return self._global_circuit_breaker.get_metrics()
        elif event_type and event_type in self._circuit_breakers:
            return self._circuit_breakers[event_type].get_metrics()
        else:
            # Return empty metrics for non-existent circuits
            return {
                "name": event_type or "global",
                "state": CircuitState.CLOSED.value,
                "total_calls": 0,
                "total_failures": 0,
                "failure_rate": 0.0,
                "enabled": self._circuit_breaker_enabled,
            }

    async def get_all_circuit_breaker_metrics(self) -> dict[str, Any]:
        """Get metrics for all circuit breakers."""
        metrics: dict[str, Any] = {
            "enabled": self._circuit_breaker_enabled,
            "global": None,
            "per_event": {},
        }

        # Global circuit breaker metrics
        if self._global_circuit_breaker:
            metrics["global"] = self._global_circuit_breaker.get_metrics()

        # Per-event circuit breaker metrics
        for event_type, circuit_breaker in self._circuit_breakers.items():
            metrics["per_event"][event_type] = circuit_breaker.get_metrics()

        return metrics

    async def _cleanup_circuit_breakers(self) -> None:
        """Clean up circuit breaker resources."""
        async with self._circuit_breaker_lock:
            self._circuit_breakers.clear()
            self._global_circuit_breaker = None

        self.logger.info("Circuit breaker resources cleaned up")


# Circuit breaker integration can be enabled by subclassing both
# EventHandlingMixin and CircuitBreakerMixin in the same class.
# This provides circuit breaker protection while maintaining
# backward compatibility.
