"""Direct position operations (close, partial close, etc.)."""

import logging
from typing import TYPE_CHECKING, Any

from project_x_py.exceptions import ProjectXError

if TYPE_CHECKING:
    from project_x_py.position_manager.types import PositionManagerProtocol

logger = logging.getLogger(__name__)


class PositionOperationsMixin:
    """Mixin for direct position operations."""

    async def close_position_direct(
        self: "PositionManagerProtocol",
        contract_id: str,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Close an entire position using the direct position close API.

        Sends a market order to close the full position immediately at the current
        market price. This is the fastest way to exit a position completely.

        Args:
            contract_id (str): Contract ID of the position to close (e.g., "MGC")
            account_id (int, optional): Account ID holding the position.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: API response containing:
                - success (bool): True if closure was successful
                - orderId (str): Order ID of the closing order (if successful)
                - errorMessage (str): Error description (if failed)
                - error (str): Additional error details

        Raises:
            ProjectXError: If no account information is available

        Side effects:
            - Removes position from tracked_positions on success
            - Increments positions_closed counter
            - May trigger order synchronization if enabled

        Example:
            >>> # Close entire Gold position
            >>> result = await position_manager.close_position_direct("MGC")
            >>> if result["success"]:
            ...     print(f"Position closed with order: {result.get('orderId')}")
            ... else:
            ...     print(f"Failed: {result.get('errorMessage')}")
            >>> # Close position in specific account
            >>> result = await position_manager.close_position_direct(
            ...     "NQ", account_id=12345
            ... )

        Note:
            - Uses market order for immediate execution
            - No price control - executes at current market price
            - For partial closes, use partially_close_position()
        """
        await self.project_x._ensure_authenticated()

        if account_id is None:
            if not self.project_x.account_info:
                raise ProjectXError("No account information available")
            account_id = self.project_x.account_info.id

        url = "/Position/closeContract"
        payload = {
            "accountId": account_id,
            "contractId": contract_id,
        }

        try:
            response = await self.project_x._make_request("POST", url, data=payload)

            if response:
                success = response.get("success", False)

                if success:
                    self.logger.info(f"✅ Position {contract_id} closed successfully")
                    # Remove from tracked positions if present
                    async with self.position_lock:
                        positions_to_remove = [
                            contract_id
                            for contract_id, pos in self.tracked_positions.items()
                            if pos.contractId == contract_id
                        ]
                        for contract_id in positions_to_remove:
                            del self.tracked_positions[contract_id]

                    # Synchronize orders - cancel related orders when position is closed
                    # Note: Order synchronization methods will be added to AsyncOrderManager
                    # if self._order_sync_enabled and self.order_manager:
                    #     await self.order_manager.on_position_closed(contract_id)

                    self.stats["positions_closed"] += 1
                else:
                    error_msg = response.get("errorMessage", "Unknown error")
                    self.logger.error(f"❌ Position closure failed: {error_msg}")

                return dict(response)

            return {"success": False, "error": "No response from server"}

        except Exception as e:
            self.logger.error(f"❌ Position closure request failed: {e}")
            return {"success": False, "error": str(e)}

    async def partially_close_position(
        self: "PositionManagerProtocol",
        contract_id: str,
        close_size: int,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Partially close a position by reducing its size.

        Sends a market order to close a specified number of contracts from an
        existing position, allowing for gradual position reduction or profit taking.

        Args:
            contract_id (str): Contract ID of the position to partially close
            close_size (int): Number of contracts to close. Must be positive and
                less than the current position size.
            account_id (int, optional): Account ID holding the position.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: API response containing:
                - success (bool): True if partial closure was successful
                - orderId (str): Order ID of the closing order (if successful)
                - errorMessage (str): Error description (if failed)
                - error (str): Additional error details

        Raises:
            ProjectXError: If no account information available or close_size <= 0

        Side effects:
            - Triggers position refresh on success to update sizes
            - Increments positions_partially_closed counter
            - May trigger order synchronization if enabled

        Example:
            >>> # Take profit on half of a 10 contract position
            >>> result = await position_manager.partially_close_position("MGC", 5)
            >>> if result["success"]:
            ...     print(f"Partially closed with order: {result.get('orderId')}")
            >>> # Scale out of position in steps
            >>> for size in [3, 2, 1]:
            ...     result = await position_manager.partially_close_position("NQ", size)
            ...     if not result["success"]:
            ...         break
            ...     await asyncio.sleep(60)  # Wait between scales

        Note:
            - Uses market order for immediate execution
            - Remaining position continues with same average price
            - Close size must not exceed current position size
        """
        await self.project_x._ensure_authenticated()

        if account_id is None:
            if not self.project_x.account_info:
                raise ProjectXError("No account information available")
            account_id = self.project_x.account_info.id

        # Validate close size
        if close_size <= 0:
            raise ProjectXError("Close size must be positive")

        url = "/Position/partialCloseContract"
        payload = {
            "accountId": account_id,
            "contractId": contract_id,
            "closeSize": close_size,
        }

        try:
            response = await self.project_x._make_request("POST", url, data=payload)

            if response:
                success = response.get("success", False)

                if success:
                    self.logger.info(
                        f"✅ Position {contract_id} partially closed: {close_size} contracts"
                    )
                    # Trigger position refresh to get updated sizes
                    await self.refresh_positions(account_id=account_id)

                    # Synchronize orders - update order sizes after partial close
                    # Note: Order synchronization methods will be added to AsyncOrderManager
                    # if self._order_sync_enabled and self.order_manager:
                    #     await self.order_manager.sync_orders_with_position(
                    #         contract_id, account_id
                    #     )

                    self.stats["positions_partially_closed"] += 1
                else:
                    error_msg = response.get("errorMessage", "Unknown error")
                    self.logger.error(
                        f"❌ Partial position closure failed: {error_msg}"
                    )

                return dict(response)

            return {"success": False, "error": "No response from server"}

        except Exception as e:
            self.logger.error(f"❌ Partial position closure request failed: {e}")
            return {"success": False, "error": str(e)}

    async def close_all_positions(
        self: "PositionManagerProtocol",
        contract_id: str | None = None,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Close all positions, optionally filtered by contract.

        Iterates through open positions and closes each one individually.
        Useful for emergency exits, end-of-day flattening, or closing all
        positions in a specific contract.

        Args:
            contract_id (str, optional): If provided, only closes positions
                in this specific contract. If None, closes all positions.
                Defaults to None.
            account_id (int, optional): Account ID to close positions for.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Bulk operation results containing:
                - total_positions (int): Number of positions attempted
                - closed (int): Number successfully closed
                - failed (int): Number that failed to close
                - errors (list[str]): Error messages for failed closures

        Example:
            >>> # Emergency close all positions
            >>> result = await position_manager.close_all_positions()
            >>> print(
            ...     f"Closed {result['closed']}/{result['total_positions']} positions"
            ... )
            >>> if result["errors"]:
            ...     for error in result["errors"]:
            ...         print(f"Error: {error}")
            >>> # Close all Gold positions only
            >>> result = await position_manager.close_all_positions(contract_id="MGC")
            >>> # Close positions in specific account
            >>> result = await position_manager.close_all_positions(account_id=12345)

        Warning:
            - Uses market orders - no price control
            - Processes positions sequentially, not in parallel
            - Continues attempting remaining positions even if some fail
        """
        positions = await self.get_all_positions(account_id=account_id)

        # Filter by contract if specified
        if contract_id:
            positions = [pos for pos in positions if pos.contractId == contract_id]

        results: dict[str, Any] = {
            "total_positions": len(positions),
            "closed": 0,
            "failed": 0,
            "errors": [],
        }

        for position in positions:
            try:
                close_result = await self.close_position_direct(
                    position.contractId, account_id
                )
                if close_result.get("success", False):
                    results["closed"] += 1
                else:
                    results["failed"] += 1
                    error_msg = close_result.get("errorMessage", "Unknown error")
                    results["errors"].append(
                        f"Position {position.contractId}: {error_msg}"
                    )
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Position {position.contractId}: {e!s}")

        self.logger.info(
            f"✅ Closed {results['closed']}/{results['total_positions']} positions"
        )
        return results

    async def close_position_by_contract(
        self: "PositionManagerProtocol",
        contract_id: str,
        close_size: int | None = None,
        account_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Close position by contract ID (full or partial).

        Convenience method that automatically determines whether to use full or
        partial position closure based on the requested size.

        Args:
            contract_id (str): Contract ID of position to close (e.g., "MGC")
            close_size (int, optional): Number of contracts to close.
                If None or >= position size, closes entire position.
                If less than position size, closes partially.
                Defaults to None (full close).
            account_id (int, optional): Account ID holding the position.
                If None, uses the default account from authentication.
                Defaults to None.

        Returns:
            dict[str, Any]: Closure response containing:
                - success (bool): True if closure was successful
                - orderId (str): Order ID (if successful)
                - errorMessage (str): Error description (if failed)
                - error (str): Error details or "No open position found"

        Example:
            >>> # Close entire position (auto-detect size)
            >>> result = await position_manager.close_position_by_contract("MGC")
            >>> # Close specific number of contracts
            >>> result = await position_manager.close_position_by_contract(
            ...     "MGC", close_size=3
            ... )
            >>> # Smart scaling - close half of any position
            >>> position = await position_manager.get_position("NQ")
            >>> if position:
            ...     half_size = position.size // 2
            ...     result = await position_manager.close_position_by_contract(
            ...         "NQ", close_size=half_size
            ...     )

        Note:
            - Returns error if no position exists for the contract
            - Automatically chooses between full and partial close
            - Uses market orders for immediate execution
        """
        # Find the position
        position = await self.get_position(contract_id, account_id)
        if not position:
            return {
                "success": False,
                "error": f"No open position found for {contract_id}",
            }

        # Determine if full or partial close
        if close_size is None or close_size >= position.size:
            # Full close
            return await self.close_position_direct(position.contractId, account_id)
        else:
            # Partial close
            return await self.partially_close_position(
                position.contractId, close_size, account_id
            )
