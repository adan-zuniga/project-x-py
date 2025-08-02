"""Subscription management for real-time client."""

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from project_x_py.realtime.types import ProjectXRealtimeClientProtocol


class SubscriptionsMixin:
    """Mixin for subscription management functionality."""

    async def subscribe_user_updates(self: "ProjectXRealtimeClientProtocol") -> bool:
        """
        Subscribe to all user-specific real-time updates.

        Enables real-time streaming of account-specific events including positions,
        orders, trades, and account balance changes. Must be connected to user hub.

        Subscriptions:
            - Account updates: Balance, buying power, margin changes
            - Position updates: New positions, size changes, closures
            - Order updates: New orders, fills, cancellations, modifications
            - Trade executions: Individual fills with prices and timestamps

        Returns:
            bool: True if all subscriptions successful, False otherwise

        Example:
            >>> # Basic subscription
            >>> if await client.connect():
            ...     if await client.subscribe_user_updates():
            ...         print("Subscribed to user events")
            >>> # With callbacks
            >>> async def on_position_update(data):
            ...     print(f"Position update: {data}")
            >>> await client.add_callback("position_update", on_position_update)
            >>> await client.subscribe_user_updates()
            >>> # Multiple accounts (if supported)
            >>> client1 = ProjectXRealtimeClient(jwt, "12345")
            >>> client2 = ProjectXRealtimeClient(jwt, "67890")
            >>> await client1.connect()
            >>> await client2.connect()
            >>> await client1.subscribe_user_updates()  # Account 12345 events
            >>> await client2.subscribe_user_updates()  # Account 67890 events

        ProjectX Methods Called:
            - SubscribeAccounts: General account updates
            - SubscribeOrders: Order lifecycle events
            - SubscribePositions: Position changes
            - SubscribeTrades: Trade executions

        Note:
            - Account ID is converted to int for ProjectX API
            - All subscriptions are account-specific
            - Must re-subscribe after reconnection
        """
        if not self.user_connected:
            self.logger.error("❌ User hub not connected")
            return False

        try:
            self.logger.info(f"📡 Subscribing to user updates for {self.account_id}")
            if self.user_connection is None:
                self.logger.error("❌ User connection not available")
                return False
            # ProjectX Gateway expects Subscribe method with account ID
            loop = asyncio.get_event_loop()

            # Subscribe to account updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribeAccounts",
                [],  # Empty list for accounts subscription
            )

            # Subscribe to order updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribeOrders",
                [int(self.account_id)],  # List with int account ID
            )

            # Subscribe to position updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribePositions",
                [int(self.account_id)],  # List with int account ID
            )

            # Subscribe to trade updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "SubscribeTrades",
                [int(self.account_id)],  # List with int account ID
            )

            self.logger.info("✅ Subscribed to user updates")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to subscribe to user updates: {e}")
            return False

    async def subscribe_market_data(
        self: "ProjectXRealtimeClientProtocol", contract_ids: list[str]
    ) -> bool:
        """
        Subscribe to market data for specific contracts.

        Enables real-time streaming of quotes, trades, and market depth for specified
        contracts. Each contract receives all three data types automatically.

        Args:
            contract_ids (list[str]): List of ProjectX contract IDs to subscribe.
                Can be symbol names or full contract IDs.
                Examples: ["MGC", "NQ"] or ["CON.F.US.MGC.M25", "CON.F.US.NQ.M25"]

        Returns:
            bool: True if all subscriptions successful, False otherwise

        Data Types Subscribed:
            - Quotes: Bid/ask prices, sizes, and timestamps
            - Trades: Executed trades with price, size, and aggressor
            - Market Depth: Full order book with multiple price levels

        Example:
            >>> # Subscribe to single contract
            >>> await client.subscribe_market_data(["MGC"])
            >>>
            >>> # Subscribe to multiple contracts
            >>> contracts = ["MGC", "NQ", "ES", "YM"]
            >>> if await client.subscribe_market_data(contracts):
            ...     print(f"Subscribed to {len(contracts)} contracts")
            >>> # With data handling
            >>> async def on_quote(data):
            ...     contract = data["contract_id"]
            ...     quote = data["data"]
            ...     print(f"{contract}: {quote['bid']} x {quote['ask']}")
            >>> await client.add_callback("quote_update", on_quote)
            >>> await client.subscribe_market_data(["MGC"])
            >>> # Add contracts dynamically
            >>> await client.subscribe_market_data(["ES"])  # Adds to existing

        ProjectX Methods Called:
            - SubscribeContractQuotes: Real-time bid/ask
            - SubscribeContractTrades: Executed trades
            - SubscribeContractMarketDepth: Order book

        Side Effects:
            - Adds contracts to self._subscribed_contracts for reconnection
            - Triggers immediate data flow for liquid contracts

        Note:
            - Subscriptions are additive - doesn't unsubscribe existing
            - Duplicate subscriptions are filtered automatically
            - Contract IDs are case-sensitive
        """
        if not self.market_connected:
            self.logger.error("❌ Market hub not connected")
            return False

        try:
            self.logger.info(
                f"📊 Subscribing to market data for {len(contract_ids)} contracts"
            )

            # Store for reconnection (avoid duplicates)
            for contract_id in contract_ids:
                if contract_id not in self._subscribed_contracts:
                    self._subscribed_contracts.append(contract_id)

            # Subscribe using ProjectX Gateway methods (same as sync client)
            loop = asyncio.get_event_loop()
            for contract_id in contract_ids:
                # Subscribe to quotes
                if self.market_connection is None:
                    self.logger.error("❌ Market connection not available")
                    return False
                await loop.run_in_executor(
                    None,
                    self.market_connection.send,
                    "SubscribeContractQuotes",
                    [contract_id],
                )
                # Subscribe to trades
                await loop.run_in_executor(
                    None,
                    self.market_connection.send,
                    "SubscribeContractTrades",
                    [contract_id],
                )
                # Subscribe to market depth
                await loop.run_in_executor(
                    None,
                    self.market_connection.send,
                    "SubscribeContractMarketDepth",
                    [contract_id],
                )

            self.logger.info(f"✅ Subscribed to {len(contract_ids)} contracts")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to subscribe to market data: {e}")
            return False

    async def unsubscribe_user_updates(self: "ProjectXRealtimeClientProtocol") -> bool:
        """
        Unsubscribe from all user-specific real-time updates.

        Stops real-time streaming of account-specific events. Useful for reducing
        bandwidth or switching accounts. Callbacks remain registered.

        Returns:
            bool: True if unsubscription successful, False otherwise

        Example:
            >>> # Temporary pause
            >>> await client.unsubscribe_user_updates()
            >>> # ... do something else ...
            >>> await client.subscribe_user_updates()  # Re-enable
            >>>
            >>> # Clean shutdown
            >>> await client.unsubscribe_user_updates()
            >>> await client.disconnect()

        Note:
            - Does not remove registered callbacks
            - Can re-subscribe without re-registering callbacks
            - Stops events for: accounts, positions, orders, trades
        """
        if not self.user_connected:
            self.logger.error("❌ User hub not connected")
            return False

        if self.user_connection is None:
            self.logger.error("❌ User connection not available")
            return False

        try:
            loop = asyncio.get_event_loop()

            # Unsubscribe from account updates
            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribeAccounts",
                self.account_id,
            )

            # Unsubscribe from order updates

            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribeOrders",
                [self.account_id],
            )

            # Unsubscribe from position updates

            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribePositions",
                self.account_id,
            )

            # Unsubscribe from trade updates

            await loop.run_in_executor(
                None,
                self.user_connection.send,
                "UnsubscribeTrades",
                self.account_id,
            )

            self.logger.info("✅ Unsubscribed from user updates")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to unsubscribe from user updates: {e}")
            return False

    async def unsubscribe_market_data(
        self: "ProjectXRealtimeClientProtocol", contract_ids: list[str]
    ) -> bool:
        """
        Unsubscribe from market data for specific contracts.

        Stops real-time streaming for specified contracts. Other subscribed
        contracts continue to stream. Useful for dynamic subscription management.

        Args:
            contract_ids (list[str]): List of contract IDs to unsubscribe.
                Should match the IDs used in subscribe_market_data().

        Returns:
            bool: True if unsubscription successful, False otherwise

        Example:
            >>> # Unsubscribe specific contracts
            >>> await client.unsubscribe_market_data(["MGC", "SI"])
            >>>
            >>> # Dynamic subscription management
            >>> active_contracts = ["ES", "NQ", "YM", "RTY"]
            >>> await client.subscribe_market_data(active_contracts)
            >>> # Later, reduce to just ES and NQ
            >>> await client.unsubscribe_market_data(["YM", "RTY"])
            >>>
            >>> # Unsubscribe all tracked contracts
            >>> all_contracts = client._subscribed_contracts.copy()
            >>> await client.unsubscribe_market_data(all_contracts)

        Side Effects:
            - Removes contracts from self._subscribed_contracts
            - Stops quotes, trades, and depth for specified contracts

        Note:
            - Only affects specified contracts
            - Callbacks remain registered for future subscriptions
            - Safe to call with non-subscribed contracts
        """
        if not self.market_connected:
            self.logger.error("❌ Market hub not connected")
            return False

        try:
            self.logger.info(f"🛑 Unsubscribing from {len(contract_ids)} contracts")

            # Remove from stored contracts
            for contract_id in contract_ids:
                if contract_id in self._subscribed_contracts:
                    self._subscribed_contracts.remove(contract_id)

            # ProjectX Gateway expects Unsubscribe method
            loop = asyncio.get_event_loop()
            if self.market_connection is None:
                self.logger.error("❌ Market connection not available")
                return False

            # Unsubscribe from quotes
            await loop.run_in_executor(
                None,
                self.market_connection.send,
                "UnsubscribeContractQuotes",
                [contract_ids],
            )

            # Unsubscribe from trades
            await loop.run_in_executor(
                None,
                self.market_connection.send,
                "UnsubscribeContractTrades",
                [contract_ids],
            )

            # Unsubscribe from market depth
            await loop.run_in_executor(
                None,
                self.market_connection.send,
                "UnsubscribeContractMarketDepth",
                [contract_ids],
            )

            self.logger.info(f"✅ Unsubscribed from {len(contract_ids)} contracts")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to unsubscribe from market data: {e}")
            return False
