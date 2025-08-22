"""
Error recovery and transaction management for OrderManager.

Author: @TexasCoding
Date: 2025-01-22

Overview:
    Provides comprehensive error recovery mechanisms for complex order operations
    that can partially fail, leaving the system in an inconsistent state. Implements
    transaction-like semantics with rollback capabilities and state tracking.

Key Features:
    - Transaction-like semantics for multi-step operations
    - Comprehensive rollback mechanisms for partial failures
    - Operation state tracking and recovery
    - Cleanup for failed operations
    - Retry logic with state recovery
    - Circuit breaker patterns for repeated failures
    - Logging and monitoring of recovery attempts

Recovery Scenarios:
    - Bracket order protective orders fail after entry fills
    - OCO linking failures with orphaned orders
    - Position-based order partial failures
    - Background task failures and cleanup
    - Network failures during multi-step operations

The recovery system ensures that even in the face of partial failures,
the system maintains consistency and provides clear recovery paths.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from project_x_py.models import OrderPlaceResponse
from project_x_py.utils import ProjectXLogger

if TYPE_CHECKING:
    from project_x_py.types import OrderManagerProtocol

logger = ProjectXLogger.get_logger(__name__)


class OperationType(Enum):
    """Types of complex operations that require recovery support."""

    BRACKET_ORDER = "bracket_order"
    OCO_PAIR = "oco_pair"
    POSITION_CLOSE = "position_close"
    BULK_CANCEL = "bulk_cancel"
    ORDER_MODIFICATION = "order_modification"


class OperationState(Enum):
    """States of a complex operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class OrderReference:
    """Reference to an order that was placed during an operation."""

    order_id: int | None = None
    response: OrderPlaceResponse | None = None
    contract_id: str = ""
    side: int = 0
    size: int = 0
    order_type: str = ""
    price: float | None = None
    placed_successfully: bool = False
    cancel_attempted: bool = False
    cancel_successful: bool = False
    error_message: str | None = None


@dataclass
class RecoveryOperation:
    """Tracks a complex operation that may need recovery."""

    operation_id: str = field(default_factory=lambda: str(uuid4()))
    operation_type: OperationType = OperationType.BRACKET_ORDER
    state: OperationState = OperationState.PENDING
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    # Orders involved in this operation
    orders: list[OrderReference] = field(default_factory=list)

    # OCO relationships to establish
    oco_pairs: list[tuple[int, int]] = field(default_factory=list)

    # Position tracking relationships
    position_tracking: dict[str, list[int]] = field(default_factory=dict)

    # Recovery actions to take if operation fails
    rollback_actions: list[Callable[..., Any]] = field(default_factory=list)

    # Error information
    errors: list[str] = field(default_factory=list)
    last_error: str | None = None

    # Retry configuration
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0

    # Success criteria
    required_orders: int = 0
    successful_orders: int = 0


class OperationRecoveryManager:
    """
    Manages error recovery for complex multi-step operations.

    Provides transaction-like semantics for operations that involve multiple
    order placements or modifications, ensuring system consistency even when
    partial failures occur.
    """

    def __init__(self, order_manager: "OrderManagerProtocol"):
        self.order_manager = order_manager
        self.logger = ProjectXLogger.get_logger(__name__)

        # Track active operations
        self.active_operations: dict[str, RecoveryOperation] = {}

        # Completed operations history (for debugging)
        self.operation_history: list[RecoveryOperation] = []
        self.max_history = 100

        # Recovery statistics
        self.recovery_stats = {
            "operations_started": 0,
            "operations_completed": 0,
            "operations_failed": 0,
            "operations_rolled_back": 0,
            "recovery_attempts": 0,
            "successful_recoveries": 0,
        }

    async def start_operation(
        self,
        operation_type: OperationType,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> RecoveryOperation:
        """
        Start a new recoverable operation.

        Args:
            operation_type: Type of operation being performed
            max_retries: Maximum retry attempts for recovery
            retry_delay: Base delay between retry attempts

        Returns:
            RecoveryOperation object to track the operation
        """
        operation = RecoveryOperation(
            operation_type=operation_type,
            state=OperationState.PENDING,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        self.active_operations[operation.operation_id] = operation
        self.recovery_stats["operations_started"] += 1

        self.logger.info(
            f"Started recoverable operation {operation.operation_id} "
            f"of type {operation_type.value}"
        )

        return operation

    async def add_order_to_operation(
        self,
        operation: RecoveryOperation,
        contract_id: str,
        side: int,
        size: int,
        order_type: str,
        price: float | None = None,
    ) -> OrderReference:
        """
        Add an order reference to track within an operation.

        Args:
            operation: The operation to add the order to
            contract_id: Contract ID for the order
            side: Order side (0=Buy, 1=Sell)
            size: Order size
            order_type: Type of order (entry, stop, target, etc.)
            price: Order price if applicable

        Returns:
            OrderReference object to track this order
        """
        order_ref = OrderReference(
            contract_id=contract_id,
            side=side,
            size=size,
            order_type=order_type,
            price=price,
        )

        operation.orders.append(order_ref)
        operation.required_orders += 1

        self.logger.debug(
            f"Added {order_type} order reference to operation {operation.operation_id}"
        )

        return order_ref

    async def record_order_success(
        self,
        operation: RecoveryOperation,
        order_ref: OrderReference,
        response: OrderPlaceResponse,
    ) -> None:
        """
        Record successful order placement within an operation.

        Args:
            operation: The operation containing this order
            order_ref: The order reference to update
            response: The successful order placement response
        """
        order_ref.order_id = response.orderId
        order_ref.response = response
        order_ref.placed_successfully = True

        operation.successful_orders += 1

        self.logger.info(
            f"Order {response.orderId} placed successfully in operation "
            f"{operation.operation_id} ({operation.successful_orders}/"
            f"{operation.required_orders})"
        )

    async def record_order_failure(
        self,
        operation: RecoveryOperation,
        order_ref: OrderReference,
        error: str,
    ) -> None:
        """
        Record failed order placement within an operation.

        Args:
            operation: The operation containing this order
            order_ref: The order reference to update
            error: Error message describing the failure
        """
        order_ref.placed_successfully = False
        order_ref.error_message = error

        operation.errors.append(error)
        operation.last_error = error

        self.logger.error(
            f"Order placement failed in operation {operation.operation_id}: {error}"
        )

    async def add_oco_pair(
        self,
        operation: RecoveryOperation,
        order1_ref: OrderReference,
        order2_ref: OrderReference,
    ) -> None:
        """
        Add an OCO pair relationship to establish after orders are placed.

        Args:
            operation: The operation to add the OCO pair to
            order1_ref: First order in the OCO pair
            order2_ref: Second order in the OCO pair
        """
        if order1_ref.order_id and order2_ref.order_id:
            operation.oco_pairs.append((order1_ref.order_id, order2_ref.order_id))

            self.logger.debug(
                f"Added OCO pair ({order1_ref.order_id}, {order2_ref.order_id}) "
                f"to operation {operation.operation_id}"
            )

    async def add_position_tracking(
        self,
        operation: RecoveryOperation,
        contract_id: str,
        order_ref: OrderReference,
        tracking_type: str,
    ) -> None:
        """
        Add position tracking relationship to establish after order placement.

        Args:
            operation: The operation to add tracking to
            contract_id: Contract ID for position tracking
            order_ref: Order reference to track
            tracking_type: Type of tracking (entry, stop, target)
        """
        if order_ref.order_id:
            if contract_id not in operation.position_tracking:
                operation.position_tracking[contract_id] = []

            operation.position_tracking[contract_id].append(order_ref.order_id)

            self.logger.debug(
                f"Added position tracking for order {order_ref.order_id} "
                f"({tracking_type}) in operation {operation.operation_id}"
            )

    async def complete_operation(self, operation: RecoveryOperation) -> bool:
        """
        Mark an operation as completed and establish all relationships.

        Args:
            operation: The operation to complete

        Returns:
            True if operation completed successfully, False otherwise
        """
        try:
            operation.state = OperationState.IN_PROGRESS

            # Check if all required orders were successful
            if operation.successful_orders < operation.required_orders:
                await self._handle_partial_failure(operation)
                return False

            # Establish OCO relationships
            for order1_id, order2_id in operation.oco_pairs:
                try:
                    self.order_manager._link_oco_orders(order1_id, order2_id)
                    self.logger.info(
                        f"Established OCO link: {order1_id} <-> {order2_id}"
                    )
                except Exception as e:
                    operation.errors.append(f"Failed to link OCO orders: {e}")
                    self.logger.error(f"Failed to establish OCO link: {e}")

            # Establish position tracking
            for contract_id, order_ids in operation.position_tracking.items():
                for order_id in order_ids:
                    try:
                        # Determine tracking type based on order reference
                        order_ref = next(
                            (
                                ref
                                for ref in operation.orders
                                if ref.order_id == order_id
                            ),
                            None,
                        )
                        if order_ref:
                            await self.order_manager.track_order_for_position(
                                contract_id, order_id, order_ref.order_type
                            )
                            self.logger.debug(
                                f"Established position tracking for order {order_id}"
                            )
                    except Exception as e:
                        operation.errors.append(
                            f"Failed to track order {order_id}: {e}"
                        )
                        self.logger.error(f"Failed to track order {order_id}: {e}")

            operation.state = OperationState.COMPLETED
            operation.completed_at = time.time()

            # Move to history
            self._move_to_history(operation)

            self.recovery_stats["operations_completed"] += 1

            self.logger.info(
                f"Operation {operation.operation_id} completed successfully "
                f"with {operation.successful_orders} orders"
            )

            return True

        except Exception as e:
            operation.errors.append(f"Failed to complete operation: {e}")
            operation.last_error = str(e)
            operation.state = OperationState.FAILED

            self.logger.error(
                f"Failed to complete operation {operation.operation_id}: {e}"
            )

            await self._handle_operation_failure(operation)
            return False

    async def _handle_partial_failure(self, operation: RecoveryOperation) -> None:
        """
        Handle partial failure of an operation.

        Args:
            operation: The partially failed operation
        """
        operation.state = OperationState.PARTIALLY_COMPLETED

        self.logger.warning(
            f"Operation {operation.operation_id} partially failed: "
            f"{operation.successful_orders}/{operation.required_orders} orders successful"
        )

        # Try to recover or rollback
        if operation.retry_count < operation.max_retries:
            await self._attempt_recovery(operation)
        else:
            await self._rollback_operation(operation)

    async def _attempt_recovery(self, operation: RecoveryOperation) -> None:
        """
        Attempt to recover a partially failed operation.

        Args:
            operation: The operation to recover
        """
        operation.retry_count += 1
        self.recovery_stats["recovery_attempts"] += 1

        self.logger.info(
            f"Attempting recovery for operation {operation.operation_id} "
            f"(attempt {operation.retry_count}/{operation.max_retries})"
        )

        try:
            # Calculate delay with exponential backoff
            delay = operation.retry_delay * (2 ** (operation.retry_count - 1))
            await asyncio.sleep(delay)

            # Try to place failed orders
            recovery_successful = True

            for order_ref in operation.orders:
                if not order_ref.placed_successfully:
                    try:
                        # Determine order placement method based on type
                        response = await self._place_recovery_order(order_ref)

                        if response and response.success:
                            await self.record_order_success(
                                operation, order_ref, response
                            )
                        else:
                            recovery_successful = False
                            error_msg = (
                                response.errorMessage
                                if response
                                and hasattr(response, "errorMessage")
                                and response.errorMessage
                                else "Unknown error"
                            )
                            await self.record_order_failure(
                                operation, order_ref, error_msg
                            )

                    except Exception as e:
                        recovery_successful = False
                        await self.record_order_failure(operation, order_ref, str(e))

            if (
                recovery_successful
                and operation.successful_orders >= operation.required_orders
            ):
                # Recovery successful, complete the operation
                await self.complete_operation(operation)
                self.recovery_stats["successful_recoveries"] += 1
            else:
                # Recovery failed, try again or rollback
                if operation.retry_count < operation.max_retries:
                    await self._attempt_recovery(operation)
                else:
                    await self._rollback_operation(operation)

        except Exception as e:
            operation.errors.append(f"Recovery attempt failed: {e}")
            self.logger.error(f"Recovery attempt failed: {e}")
            await self._rollback_operation(operation)

    async def _place_recovery_order(
        self, order_ref: OrderReference
    ) -> OrderPlaceResponse | None:
        """
        Place an order during recovery attempt.

        Args:
            order_ref: Order reference to place

        Returns:
            OrderPlaceResponse if successful, None otherwise
        """
        try:
            if order_ref.order_type == "entry":
                if order_ref.price:
                    return await self.order_manager.place_limit_order(
                        order_ref.contract_id,
                        order_ref.side,
                        order_ref.size,
                        order_ref.price,
                    )
                else:
                    return await self.order_manager.place_market_order(
                        order_ref.contract_id, order_ref.side, order_ref.size
                    )
            elif order_ref.order_type == "stop":
                return await self.order_manager.place_stop_order(
                    order_ref.contract_id,
                    order_ref.side,
                    order_ref.size,
                    order_ref.price or 0.0,
                )
            elif order_ref.order_type == "target":
                return await self.order_manager.place_limit_order(
                    order_ref.contract_id,
                    order_ref.side,
                    order_ref.size,
                    order_ref.price or 0.0,
                )
            else:
                self.logger.error(
                    f"Unknown order type for recovery: {order_ref.order_type}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Failed to place recovery order: {e}")
            return None

    async def _rollback_operation(self, operation: RecoveryOperation) -> None:
        """
        Rollback a failed operation by canceling successful orders.

        Args:
            operation: The operation to rollback
        """
        operation.state = OperationState.ROLLING_BACK
        self.recovery_stats["operations_rolled_back"] += 1

        self.logger.warning(
            f"Rolling back operation {operation.operation_id} "
            f"after {operation.retry_count} failed recovery attempts"
        )

        rollback_errors = []

        # Cancel successfully placed orders
        for order_ref in operation.orders:
            if (
                order_ref.placed_successfully
                and order_ref.order_id
                and not order_ref.cancel_attempted
            ):
                try:
                    order_ref.cancel_attempted = True
                    success = await self.order_manager.cancel_order(order_ref.order_id)
                    order_ref.cancel_successful = success

                    if success:
                        self.logger.info(
                            f"Cancelled order {order_ref.order_id} during rollback"
                        )
                    else:
                        rollback_errors.append(
                            f"Failed to cancel order {order_ref.order_id}"
                        )

                except Exception as e:
                    rollback_errors.append(
                        f"Error canceling order {order_ref.order_id}: {e}"
                    )
                    self.logger.error(
                        f"Error during rollback of order {order_ref.order_id}: {e}"
                    )

        # Clean up OCO relationships
        for order1_id, order2_id in operation.oco_pairs:
            try:
                if order1_id in self.order_manager.oco_groups:
                    del self.order_manager.oco_groups[order1_id]
                if order2_id in self.order_manager.oco_groups:
                    del self.order_manager.oco_groups[order2_id]
            except Exception as e:
                rollback_errors.append(
                    f"Error cleaning OCO pair ({order1_id}, {order2_id}): {e}"
                )

        # Clean up position tracking
        for _contract_id, order_ids in operation.position_tracking.items():
            for order_id in order_ids:
                try:
                    # Check if untrack_order method exists (might not be present in mixins)
                    if hasattr(self.order_manager, "untrack_order"):
                        self.order_manager.untrack_order(order_id)
                    else:
                        logger.debug(
                            f"Skipping untrack_order for {order_id} - method not available"
                        )
                except Exception as e:
                    rollback_errors.append(f"Error untracking order {order_id}: {e}")

        operation.state = OperationState.ROLLED_BACK
        operation.completed_at = time.time()
        operation.errors.extend(rollback_errors)

        # Move to history
        self._move_to_history(operation)

        if rollback_errors:
            self.logger.error(
                f"Rollback of operation {operation.operation_id} completed with errors: "
                f"{'; '.join(rollback_errors)}"
            )
        else:
            self.logger.info(
                f"Operation {operation.operation_id} rolled back successfully"
            )

    async def _handle_operation_failure(self, operation: RecoveryOperation) -> None:
        """
        Handle complete operation failure.

        Args:
            operation: The failed operation
        """
        self.recovery_stats["operations_failed"] += 1

        self.logger.error(
            f"Operation {operation.operation_id} failed completely. "
            f"Errors: {'; '.join(operation.errors)}"
        )

        # Attempt cleanup
        await self._rollback_operation(operation)

    def _move_to_history(self, operation: RecoveryOperation) -> None:
        """
        Move a completed operation to history.

        Args:
            operation: The operation to move to history
        """
        if operation.operation_id in self.active_operations:
            del self.active_operations[operation.operation_id]

        self.operation_history.append(operation)

        # Maintain history size limit
        if len(self.operation_history) > self.max_history:
            self.operation_history = self.operation_history[-self.max_history :]

    async def force_rollback_operation(self, operation_id: str) -> bool:
        """
        Force rollback of an active operation.

        Args:
            operation_id: ID of the operation to rollback

        Returns:
            True if rollback was initiated, False if operation not found
        """
        if operation_id not in self.active_operations:
            self.logger.warning(
                f"Operation {operation_id} not found for forced rollback"
            )
            return False

        operation = self.active_operations[operation_id]

        self.logger.warning(
            f"Forcing rollback of operation {operation_id} "
            f"(current state: {operation.state.value})"
        )

        await self._rollback_operation(operation)
        return True

    def get_operation_status(self, operation_id: str) -> dict[str, Any] | None:
        """
        Get status of an operation.

        Args:
            operation_id: ID of the operation to check

        Returns:
            Dictionary with operation status or None if not found
        """
        operation = None

        # Check active operations first
        if operation_id in self.active_operations:
            operation = self.active_operations[operation_id]
        else:
            # Check history
            for hist_op in self.operation_history:
                if hist_op.operation_id == operation_id:
                    operation = hist_op
                    break

        if not operation:
            return None

        return {
            "operation_id": operation.operation_id,
            "operation_type": operation.operation_type.value,
            "state": operation.state.value,
            "started_at": operation.started_at,
            "completed_at": operation.completed_at,
            "required_orders": operation.required_orders,
            "successful_orders": operation.successful_orders,
            "retry_count": operation.retry_count,
            "max_retries": operation.max_retries,
            "errors": operation.errors,
            "last_error": operation.last_error,
            "orders": [
                {
                    "order_id": ref.order_id,
                    "contract_id": ref.contract_id,
                    "side": ref.side,
                    "size": ref.size,
                    "order_type": ref.order_type,
                    "price": ref.price,
                    "placed_successfully": ref.placed_successfully,
                    "cancel_attempted": ref.cancel_attempted,
                    "cancel_successful": ref.cancel_successful,
                    "error_message": ref.error_message,
                }
                for ref in operation.orders
            ],
            "oco_pairs": operation.oco_pairs,
            "position_tracking": operation.position_tracking,
        }

    def get_recovery_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive recovery statistics.

        Returns:
            Dictionary with recovery statistics and system health
        """
        active_count = len(self.active_operations)
        history_count = len(self.operation_history)

        # Calculate success rates
        total_operations = self.recovery_stats["operations_started"]
        success_rate = (
            self.recovery_stats["operations_completed"] / total_operations
            if total_operations > 0
            else 0.0
        )

        recovery_success_rate = (
            self.recovery_stats["successful_recoveries"]
            / self.recovery_stats["recovery_attempts"]
            if self.recovery_stats["recovery_attempts"] > 0
            else 0.0
        )

        return {
            **self.recovery_stats,
            "active_operations": active_count,
            "history_operations": history_count,
            "success_rate": success_rate,
            "recovery_success_rate": recovery_success_rate,
            "active_operation_ids": list(self.active_operations.keys()),
        }

    async def cleanup_stale_operations(self, max_age_hours: float = 24.0) -> int:
        """
        Clean up stale operations that have been active too long.

        Args:
            max_age_hours: Maximum age in hours for active operations

        Returns:
            Number of operations cleaned up
        """
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        cleanup_count = 0

        stale_operations = []
        for operation_id, operation in self.active_operations.items():
            if current_time - operation.started_at > max_age_seconds:
                stale_operations.append((operation_id, operation))

        for operation_id, operation in stale_operations:
            self.logger.warning(
                f"Cleaning up stale operation {operation_id} "
                f"(age: {(current_time - operation.started_at) / 3600:.1f} hours)"
            )

            try:
                await self._rollback_operation(operation)
                cleanup_count += 1
            except Exception as e:
                self.logger.error(
                    f"Error cleaning up stale operation {operation_id}: {e}"
                )

        return cleanup_count
