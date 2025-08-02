"""Real-time position tracking and callback management."""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any

from project_x_py.models import Position

if TYPE_CHECKING:
    from project_x_py.position_manager.types import PositionManagerProtocol

logger = logging.getLogger(__name__)


class PositionTrackingMixin:
    """Mixin for real-time position tracking and callback functionality."""

    def __init__(self) -> None:
        """Initialize tracking attributes."""
        # Position tracking (maintains local state for business logic)
        self.tracked_positions: dict[str, Position] = {}
        self.position_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.position_callbacks: dict[str, list[Any]] = defaultdict(list)

    async def _setup_realtime_callbacks(self: "PositionManagerProtocol") -> None:
        """
        Set up callbacks for real-time position monitoring via WebSocket.

        Registers internal callback handlers with the real-time client to process
        position updates and account changes. Called automatically during initialization
        when a real-time client is provided.

        Registered callbacks:
            - position_update: Handles position size/price changes and closures
            - account_update: Handles account-level changes affecting positions

        Note:
            This is an internal method called by initialize(). Do not call directly.
        """
        if not self.realtime_client:
            return

        # Register for position events (closures are detected from position updates)
        await self.realtime_client.add_callback(
            "position_update", self._on_position_update
        )
        await self.realtime_client.add_callback(
            "account_update", self._on_account_update
        )

        self.logger.info("🔄 Real-time position callbacks registered")

    async def _on_position_update(
        self: "PositionManagerProtocol", data: dict[str, Any] | list[dict[str, Any]]
    ) -> None:
        """
        Handle real-time position updates and detect position closures.

        Processes incoming position data from the WebSocket feed, updates tracked
        positions, detects closures (size=0), and triggers appropriate callbacks.

        Args:
            data (dict): Position update data from real-time feed. Can be:
                - Single position dict with GatewayUserPosition fields
                - List of position dicts
                - Wrapped format: {"action": 1, "data": {position_data}}

        Note:
            - Position closure is detected when size == 0 (not type == 0)
            - Type 0 means "Undefined" in PositionType enum, not closed
            - Automatically triggers position_closed callbacks on closure
        """
        try:
            async with self.position_lock:
                if isinstance(data, list):
                    for position_data in data:
                        await self._process_position_data(position_data)
                elif isinstance(data, dict):
                    await self._process_position_data(data)

        except Exception as e:
            self.logger.error(f"Error processing position update: {e}")

    async def _on_account_update(
        self: "PositionManagerProtocol", data: dict[str, Any]
    ) -> None:
        """
        Handle account-level updates that may affect positions.

        Processes account update events from the real-time feed and triggers
        registered account_update callbacks for custom handling.

        Args:
            data (dict): Account update data containing balance, margin, and other
                account-level information that may impact position management
        """
        await self._trigger_callbacks("account_update", data)

    def _validate_position_payload(
        self: "PositionManagerProtocol", position_data: dict[str, Any]
    ) -> bool:
        """
        Validate that position payload matches ProjectX GatewayUserPosition format.

        Ensures incoming position data conforms to the expected schema before processing.
        This validation prevents errors from malformed data and ensures API compliance.

        Expected fields according to ProjectX docs:
            - id (int): The unique position identifier
            - accountId (int): The account associated with the position
            - contractId (string): The contract ID associated with the position
            - creationTimestamp (string): ISO timestamp when position was opened
            - type (int): PositionType enum value:
                * 0 = Undefined (not a closed position)
                * 1 = Long position
                * 2 = Short position
            - size (int): The number of contracts (0 means position is closed)
            - averagePrice (number): The weighted average entry price

        Args:
            position_data (dict): Raw position payload from ProjectX real-time feed

        Returns:
            bool: True if payload contains all required fields with valid values,
                False if validation fails

        Warning:
            Position closure is determined by size == 0, NOT type == 0.
            Type 0 means "Undefined" position type, not a closed position.
        """
        required_fields: set[str] = {
            "id",
            "accountId",
            "contractId",
            "creationTimestamp",
            "type",
            "size",
            "averagePrice",
        }

        missing_fields: set[str] = required_fields - set(position_data.keys())
        if missing_fields:
            self.logger.warning(
                f"Position payload missing required fields: {missing_fields}"
            )
            return False

        # Validate PositionType enum values
        position_type: int | None = position_data.get("type")
        if position_type not in [0, 1, 2]:  # Undefined, Long, Short
            self.logger.warning(f"Invalid position type: {position_type}")
            return False

        # Validate that size is a number
        size: int | float | None = position_data.get("size")
        if not isinstance(size, int | float):
            self.logger.warning(f"Invalid position size type: {type(size)}")
            return False

        return True

    async def _process_position_data(
        self: "PositionManagerProtocol", position_data: dict[str, Any]
    ) -> None:
        """
        Process individual position data update and detect position closures.

        Core processing method that handles position updates, maintains tracked positions,
        detects closures, triggers callbacks, and synchronizes with order management.

        ProjectX GatewayUserPosition payload structure:
            - Position is closed when size == 0 (not when type == 0)
            - type=0 means "Undefined" according to PositionType enum
            - type=1 means "Long", type=2 means "Short"

        Args:
            position_data (dict): Position data which can be:
                - Direct position dict with GatewayUserPosition fields
                - Wrapped format: {"action": 1, "data": {actual_position_data}}

        Processing flow:
            1. Extract actual position data from wrapper if needed
            2. Validate payload format
            3. Check if position is closed (size == 0)
            4. Update tracked positions or remove if closed
            5. Trigger appropriate callbacks
            6. Update position history
            7. Check position alerts
            8. Synchronize with order manager if enabled

        Side effects:
            - Updates self.tracked_positions
            - Appends to self.position_history
            - May trigger position_closed or position_update callbacks
            - May trigger position alerts
            - Updates statistics counters
        """
        try:
            # Handle wrapped position data from real-time updates
            # Real-time updates come as: {"action": 1, "data": {position_data}}
            # But direct API calls might provide raw position data
            actual_position_data: dict[str, Any] = position_data
            if "action" in position_data and "data" in position_data:
                actual_position_data = position_data["data"]
                self.logger.debug(
                    f"Extracted position data from wrapper: action={position_data.get('action')}"
                )

            # Validate payload format
            if not self._validate_position_payload(actual_position_data):
                self.logger.error(
                    f"Invalid position payload format: {actual_position_data}"
                )
                return

            contract_id = actual_position_data.get("contractId")
            if not contract_id:
                self.logger.error(f"No contract ID found in {actual_position_data}")
                return

            # Check if this is a position closure
            # Position is closed when size == 0 (not when type == 0)
            # type=0 means "Undefined" according to PositionType enum, not closed
            position_size: int = actual_position_data.get("size", 0)
            is_position_closed: bool = position_size == 0

            # Get the old position before updating
            old_position: Position | None = self.tracked_positions.get(contract_id)
            old_size: int = old_position.size if old_position else 0

            if is_position_closed:
                # Position is closed - remove from tracking and trigger closure callbacks
                if contract_id in self.tracked_positions:
                    del self.tracked_positions[contract_id]
                    self.logger.info(f"📊 Position closed: {contract_id}")
                    self.stats["positions_closed"] += 1

                # Synchronize orders - cancel related orders when position is closed
                # Note: Order synchronization methods will be added to AsyncOrderManager
                # if self._order_sync_enabled and self.order_manager:
                #     await self.order_manager.on_position_closed(contract_id)

                # Trigger position_closed callbacks with the closure data
                await self._trigger_callbacks("position_closed", actual_position_data)
            else:
                # Position is open/updated - create or update position
                # ProjectX payload structure matches our Position model fields
                position: Position = Position(**actual_position_data)
                self.tracked_positions[contract_id] = position

                # Synchronize orders - update order sizes if position size changed
                # Note: Order synchronization methods will be added to AsyncOrderManager
                # if (
                #     self._order_sync_enabled
                #     and self.order_manager
                #     and old_size != position_size
                # ):
                #     await self.order_manager.on_position_changed(
                #         contract_id, old_size, position_size
                #     )

                # Track position history
                self.position_history[contract_id].append(
                    {
                        "timestamp": datetime.now(),
                        "position": actual_position_data.copy(),
                        "size_change": position_size - old_size,
                    }
                )

                # Check alerts
                await self._check_position_alerts(contract_id, position, old_position)

        except Exception as e:
            self.logger.error(f"Error processing position data: {e}")
            self.logger.debug(f"Position data that caused error: {position_data}")

    async def _trigger_callbacks(
        self: "PositionManagerProtocol", event_type: str, data: Any
    ) -> None:
        """
        Trigger registered callbacks for position events.

        Executes all registered callback functions for a specific event type.
        Handles both sync and async callbacks, with error isolation to prevent
        one failing callback from affecting others.

        Args:
            event_type (str): The type of event to trigger callbacks for:
                - "position_update": Position changed
                - "position_closed": Position fully closed
                - "account_update": Account-level change
                - "position_alert": Alert condition met
            data (Any): Event data to pass to callbacks, typically a dict with
                event-specific information

        Note:
            - Callbacks are executed in registration order
            - Errors in callbacks are logged but don't stop other callbacks
            - Supports both sync and async callback functions
        """
        for callback in self.position_callbacks.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                self.logger.error(f"Error in {event_type} callback: {e}")

    async def add_callback(
        self: "PositionManagerProtocol",
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ) -> None:
        """
        Register a callback function for specific position events.

        Allows you to listen for position updates, closures, account changes, and alerts
        to build custom monitoring and notification systems.

        Args:
            event_type: Type of event to listen for
                - "position_update": Position size or price changes
                - "position_closed": Position fully closed (size = 0)
                - "account_update": Account-level changes
                - "position_alert": Position alert triggered
            callback: Async function to call when event occurs
                Should accept one argument: the event data dict

        Example:
            >>> async def on_position_update(data):
            ...     pos = data.get("data", {})
            ...     print(
            ...         f"Position updated: {pos.get('contractId')} size: {pos.get('size')}"
            ...     )
            >>> await position_manager.add_callback(
            ...     "position_update", on_position_update
            ... )
            >>> async def on_position_closed(data):
            ...     pos = data.get("data", {})
            ...     print(f"Position closed: {pos.get('contractId')}")
            >>> await position_manager.add_callback(
            ...     "position_closed", on_position_closed
            ... )
        """
        self.position_callbacks[event_type].append(callback)
