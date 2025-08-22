"""
Example: Circuit Breaker Protection for Event Processing

This example demonstrates how to use the Circuit Breaker pattern to protect
event processing in the project-x-py SDK against cascading failures.

Features demonstrated:
- Circuit breaker configuration for event handling
- Failure thresholds and automatic recovery
- Fallback handlers for graceful degradation
- Metrics monitoring and state management
- Integration with the realtime event system

The circuit breaker provides resilience against:
- Event handler exceptions
- Slow event processing (timeouts)
- Resource exhaustion
- Downstream service failures
"""

import asyncio
import logging
from typing import Any

from project_x_py.realtime.circuit_breaker import (
    CircuitBreakerError,
    CircuitBreakerMixin,
)
from project_x_py.realtime.event_handling import EventHandlingMixin

# Configure logging to see circuit breaker activity
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class ProtectedEventHandler(EventHandlingMixin, CircuitBreakerMixin):
    """
    Event handler with circuit breaker protection.

    This class combines the standard EventHandlingMixin with CircuitBreakerMixin
    to provide fault-tolerant event processing. It demonstrates how to integrate
    circuit breaker protection into existing event handling code.
    """

    def __init__(self):
        super().__init__()
        self.logger = logger
        self.callbacks = {}

        # Statistics for demonstration
        self.events_processed = 0
        self.events_failed = 0
        self.events_blocked = 0

        # Simulate some problematic event handlers for demo
        self.failure_simulation = {
            "quote_update": False,
            "order_update": False,
            "position_update": False,
        }

    async def _trigger_callbacks(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Custom callback triggering with simulated failures for demonstration.

        In a real implementation, this would be the actual callback processing
        that might fail due to various reasons (network issues, processing errors, etc.).
        """
        self.events_processed += 1

        # Simulate occasional failures for demonstration
        if self.failure_simulation.get(event_type, False):
            self.events_failed += 1
            # Simulate different types of failures
            if event_type == "quote_update":
                await asyncio.sleep(0.1)  # Simulate slow processing
                raise Exception(f"Simulated network timeout processing {event_type}")
            elif event_type == "order_update":
                raise Exception(f"Simulated database connection error for {event_type}")
            else:
                raise Exception(f"Simulated processing error for {event_type}")

        # Normal processing
        logger.info(f"Successfully processed {event_type} event: {data}")

    async def process_event_with_protection(
        self, event_type: str, data: dict[str, Any]
    ) -> None:
        """
        Process an event with circuit breaker protection.

        This method uses the circuit breaker to protect against failures in event processing.
        """
        try:
            await self._trigger_callbacks_with_circuit_breaker(event_type, data)
        except CircuitBreakerError:
            self.events_blocked += 1
            logger.warning(f"Circuit breaker blocked {event_type} processing")
        except Exception as e:
            self.events_failed += 1
            logger.error(f"Event processing failed: {e}")

    def get_processing_stats(self) -> dict[str, Any]:
        """Get event processing statistics."""
        return {
            "events_processed": self.events_processed,
            "events_failed": self.events_failed,
            "events_blocked": self.events_blocked,
            "success_rate": (
                (self.events_processed - self.events_failed)
                / max(self.events_processed, 1)
            )
            * 100,
        }


async def setup_fallback_handlers(handler: ProtectedEventHandler) -> None:
    """
    Set up fallback handlers for when circuit breaker is open.

    Fallback handlers provide graceful degradation by handling events
    in a simplified way when the main processing is failing.
    """

    async def quote_fallback(*_args, **_kwargs) -> None:
        """Fallback handler for quote updates - just log the event."""
        logger.info("FALLBACK: Quote update processed with minimal logging")

    async def order_fallback(*_args, **_kwargs) -> None:
        """Fallback handler for order updates - cache for later processing."""
        logger.info("FALLBACK: Order update cached for later processing")

    async def position_fallback(*_args, **_kwargs) -> None:
        """Fallback handler for position updates - send alert only."""
        logger.warning("FALLBACK: Position update - sending alert to monitoring system")

    # Register fallback handlers
    await handler.set_circuit_breaker_fallback("quote_update", quote_fallback)
    await handler.set_circuit_breaker_fallback("order_update", order_fallback)
    await handler.set_circuit_breaker_fallback("position_update", position_fallback)

    logger.info("Fallback handlers configured for all event types")


async def demonstrate_circuit_breaker() -> None:
    """
    Demonstrate circuit breaker functionality with various failure scenarios.
    """
    logger.info("=== Circuit Breaker Protection Demo ===")

    # Create protected event handler
    handler = ProtectedEventHandler()

    # Configure circuit breaker with aggressive settings for demo
    await handler.configure_circuit_breaker(
        failure_threshold=3,  # Open circuit after 3 failures
        time_window_seconds=30.0,  # Count failures in 30-second window
        timeout_seconds=2.0,  # Timeout individual events after 2 seconds
        recovery_timeout=5.0,  # Try recovery after 5 seconds
        half_open_max_calls=2,  # Allow 2 test calls in half-open state
        enable_global_circuit=True,  # Enable global circuit breaker
    )

    # Set up fallback handlers
    await setup_fallback_handlers(handler)

    logger.info("Circuit breaker configured with aggressive settings for demonstration")

    # Phase 1: Normal operation
    logger.info("\n--- Phase 1: Normal Operation ---")
    for i in range(5):
        await handler.process_event_with_protection(
            "quote_update", {"symbol": "MNQ", "bid": 18500 + i, "ask": 18501 + i}
        )
        await asyncio.sleep(0.1)

    # Show circuit state and stats
    state = await handler.get_circuit_breaker_state()
    stats = handler.get_processing_stats()
    metrics = await handler.get_circuit_breaker_metrics()

    logger.info(f"Circuit State: {state}")
    logger.info(f"Processing Stats: {stats}")
    logger.info(f"Circuit Metrics: Success Rate = {metrics.get('failure_rate', 0):.2%}")

    # Phase 2: Introduce failures
    logger.info("\n--- Phase 2: Introducing Failures ---")
    handler.failure_simulation["quote_update"] = True  # Start failing quote updates

    # Process events that will fail and trigger circuit breaker
    for i in range(5):
        await handler.process_event_with_protection(
            "quote_update", {"symbol": "MNQ", "bid": 18505 + i, "ask": 18506 + i}
        )
        await asyncio.sleep(0.1)

    # Check circuit state after failures
    state = await handler.get_circuit_breaker_state()
    stats = handler.get_processing_stats()
    metrics = await handler.get_circuit_breaker_metrics()

    logger.info(f"Circuit State After Failures: {state}")
    logger.info(f"Processing Stats: {stats}")
    logger.info(f"Circuit Metrics: Total Failures = {metrics.get('total_failures', 0)}")

    # Phase 3: Circuit is open - fallback handling
    logger.info("\n--- Phase 3: Circuit Open - Fallback Mode ---")
    handler.failure_simulation["quote_update"] = False  # Fix the issue

    # These events should be handled by fallback since circuit is open
    for i in range(3):
        await handler.process_event_with_protection(
            "quote_update", {"symbol": "MNQ", "bid": 18510 + i, "ask": 18511 + i}
        )
        await asyncio.sleep(0.1)

    stats = handler.get_processing_stats()
    logger.info(f"Processing Stats During Circuit Open: {stats}")

    # Phase 4: Wait for recovery
    logger.info("\n--- Phase 4: Waiting for Circuit Recovery ---")
    logger.info("Waiting for recovery timeout (5 seconds)...")
    await asyncio.sleep(6)  # Wait longer than recovery timeout

    # Phase 5: Recovery testing (half-open state)
    logger.info("\n--- Phase 5: Circuit Recovery Testing ---")

    # These events should trigger half-open state and test recovery
    for i in range(3):
        await handler.process_event_with_protection(
            "quote_update", {"symbol": "MNQ", "bid": 18515 + i, "ask": 18516 + i}
        )

        state = await handler.get_circuit_breaker_state()
        logger.info(f"Circuit State During Recovery: {state}")
        await asyncio.sleep(0.5)

    # Final stats
    logger.info("\n--- Final Results ---")
    state = await handler.get_circuit_breaker_state()
    stats = handler.get_processing_stats()
    all_metrics = await handler.get_all_circuit_breaker_metrics()

    logger.info(f"Final Circuit State: {state}")
    logger.info(f"Final Processing Stats: {stats}")
    logger.info(f"Final Success Rate: {stats['success_rate']:.1f}%")

    # Show detailed circuit breaker metrics
    global_metrics = all_metrics.get("global")
    if global_metrics:
        logger.info("Circuit Breaker Metrics:")
        logger.info(f"  - Total Calls: {global_metrics.get('total_calls', 0)}")
        logger.info(f"  - Total Failures: {global_metrics.get('total_failures', 0)}")
        logger.info(f"  - Total Timeouts: {global_metrics.get('total_timeouts', 0)}")
        logger.info(
            f"  - Circuit Opened Count: {global_metrics.get('circuit_opened_count', 0)}"
        )
        logger.info(
            f"  - Recovery Attempts: {global_metrics.get('recovery_attempts', 0)}"
        )

    # Cleanup
    await handler._cleanup_circuit_breakers()
    logger.info("Circuit breaker demonstration completed successfully!")


async def demonstrate_per_event_circuits() -> None:
    """
    Demonstrate per-event-type circuit breakers working independently.
    """
    logger.info("\n=== Per-Event Circuit Breaker Demo ===")

    handler = ProtectedEventHandler()

    # Configure with per-event circuits (no global circuit)
    await handler.configure_circuit_breaker(
        failure_threshold=2,
        time_window_seconds=10.0,
        enable_global_circuit=False,
    )

    logger.info("Configured per-event circuit breakers")

    # Make quote_update fail but keep order_update working
    handler.failure_simulation["quote_update"] = True

    # Process mixed events - quotes should fail, orders should succeed
    events = [
        ("quote_update", {"symbol": "MNQ", "bid": 18500, "ask": 18501}),
        ("order_update", {"order_id": "123", "status": "filled"}),
        ("quote_update", {"symbol": "ES", "bid": 4500, "ask": 4501}),
        ("order_update", {"order_id": "124", "status": "pending"}),
        (
            "quote_update",
            {"symbol": "MNQ", "bid": 18502, "ask": 18503},
        ),  # This should trigger circuit
        (
            "order_update",
            {"order_id": "125", "status": "filled"},
        ),  # This should still work
    ]

    for event_type, data in events:
        await handler.process_event_with_protection(event_type, data)

        # Check individual circuit states
        quote_state = await handler.get_circuit_breaker_state("quote_update")
        order_state = await handler.get_circuit_breaker_state("order_update")

        logger.info(f"Circuit States - Quote: {quote_state}, Order: {order_state}")
        await asyncio.sleep(0.2)

    # Show final isolation
    stats = handler.get_processing_stats()
    all_metrics = await handler.get_all_circuit_breaker_metrics()

    logger.info(f"Per-Event Circuit Demo Stats: {stats}")
    logger.info("Per-event circuit isolation successful!")

    # Show metrics for each event type
    for event_type, metrics in all_metrics.get("per_event", {}).items():
        logger.info(
            f"  {event_type}: {metrics.get('total_calls', 0)} calls, "
            f"{metrics.get('total_failures', 0)} failures, "
            f"state: {metrics.get('state', 'unknown')}"
        )


async def demonstrate_real_world_integration():
    """
    Demonstrate how circuit breaker would integrate with TradingSuite.

    Note: This is a conceptual demonstration. In practice, you would
    subclass the realtime client to include circuit breaker protection.
    """
    logger.info("\n=== Real-World Integration Concept ===")

    # This shows how you might integrate circuit breaker protection
    # in a real trading application

    class ProtectedTradingHandler(CircuitBreakerMixin):
        """Example of how to add circuit breaker to a trading handler."""

        def __init__(self):
            super().__init__()
            self.logger = logger
            self.position_updates = []
            self.order_updates = []

        async def _trigger_callbacks(
            self, event_type: str, data: dict[str, Any]
        ) -> None:
            """Simulate real trading event processing."""
            if event_type == "position_update":
                # Simulate position processing that might fail
                contract_id = data.get("contractId", "unknown")
                position = data.get("netPos", 0)

                # Simulate occasional database connection failures
                if contract_id == "error_contract":
                    raise Exception("Database connection failed")

                self.position_updates.append((contract_id, position))
                logger.info(f"Processed position update: {contract_id} = {position}")

            elif event_type == "order_update":
                # Simulate order processing
                order_id = data.get("orderId", "unknown")
                status = data.get("status", "unknown")

                # Simulate occasional order system failures
                if status == "error_status":
                    raise Exception("Order management system error")

                self.order_updates.append((order_id, status))
                logger.info(f"Processed order update: {order_id} = {status}")

    # Create and configure protected handler
    handler = ProtectedTradingHandler()
    await handler.configure_circuit_breaker(
        failure_threshold=3,
        timeout_seconds=1.0,
        enable_global_circuit=True,
    )

    # Set up fallback for position updates
    async def position_fallback(_event_type: str, data: dict[str, Any]) -> None:
        logger.warning(f"FALLBACK: Position update queued for retry: {data}")

    await handler.set_circuit_breaker_fallback("position_update", position_fallback)

    logger.info("Real-world trading handler configured with circuit breaker protection")

    # Simulate mixed successful and failing events
    test_events = [
        ("position_update", {"contractId": "MNQ", "netPos": 2}),
        ("order_update", {"orderId": "123", "status": "filled"}),
        ("position_update", {"contractId": "error_contract", "netPos": 1}),  # Will fail
        ("position_update", {"contractId": "ES", "netPos": -1}),
        ("order_update", {"orderId": "124", "status": "error_status"}),  # Will fail
        ("position_update", {"contractId": "MNQ", "netPos": 3}),
    ]

    for event_type, data in test_events:
        try:
            await handler._trigger_callbacks_with_circuit_breaker(event_type, data)
        except Exception as e:
            logger.error(f"Event processing failed: {e}")

        await asyncio.sleep(0.1)

    # Show results
    logger.info(f"Position updates processed: {len(handler.position_updates)}")
    logger.info(f"Order updates processed: {len(handler.order_updates)}")

    await handler.get_all_circuit_breaker_metrics()
    logger.info("Real-world integration demo completed!")

    return handler


async def main() -> None:
    """
    Main demonstration function.

    This example shows various aspects of circuit breaker protection
    for event processing in trading applications.
    """
    try:
        logger.info("Starting Circuit Breaker Protection Examples")

        # Demonstrate basic circuit breaker functionality
        await demonstrate_circuit_breaker()

        # Wait between demos
        await asyncio.sleep(2)

        # Demonstrate per-event circuit isolation
        await demonstrate_per_event_circuits()

        # Wait between demos
        await asyncio.sleep(2)

        # Demonstrate real-world integration concept
        await demonstrate_real_world_integration()

        logger.info("\n🎉 All circuit breaker demonstrations completed successfully!")

        # Summary of benefits
        logger.info("\n=== Circuit Breaker Benefits Summary ===")
        logger.info("✅ Prevents cascading failures in event processing")
        logger.info("✅ Provides automatic recovery with exponential backoff")
        logger.info("✅ Supports fallback handlers for graceful degradation")
        logger.info("✅ Offers comprehensive metrics and monitoring")
        logger.info("✅ Isolates failures per event type when needed")
        logger.info("✅ Integrates seamlessly with existing event handling")
        logger.info("✅ Protects against timeouts and slow processing")
        logger.info("✅ Maintains system stability under load")

    except Exception as e:
        logger.error(f"Demo failed with error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())
