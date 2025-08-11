"""
Async instrument search, selection, and historical bar data for ProjectX clients.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides async methods for instrument discovery, smart contract selection, and retrieval
    of historical OHLCV bar data, with Polars DataFrame output for high-performance analysis.
    Integrates in-memory caching for both instrument and bar queries, minimizing redundant
    API calls and ensuring data consistency. Designed to support trading and analytics flows
    requiring timely and accurate market data.

Key Features:
    - Symbol/name instrument search with live/active filtering
    - Sophisticated contract selection logic (front month, micro, etc.)
    - Historical bar data retrieval (OHLCV) with timezone handling
    - Transparent, per-query caching for both instrument and bars
    - Data returned as Polars DataFrame (timestamp, open, high, low, close, volume)
    - Utilities for cache management and periodic cleanup

Example Usage:
    ```python
    import asyncio
    from project_x_py import ProjectX


    async def main():
        # V3: Async market data retrieval with Polars DataFrames
        async with ProjectX.from_env() as client:
            await client.authenticate()

            # Get instrument details with smart contract selection
            instrument = await client.get_instrument("ES")
            print(f"Trading: {instrument.name} ({instrument.id})")
            print(f"Tick size: {instrument.tick_size}")

            # Fetch historical bars (returns Polars DataFrame)
            bars = await client.get_bars("ES", days=3, interval=15)
            print(f"Retrieved {len(bars)} 15-minute bars")
            print(bars.head())

            # V3: Can also search by contract ID directly
            mnq_sept = await client.get_instrument("CON.F.US.MNQ.U25")
            print(f"Contract: {mnq_sept.symbol}")


    asyncio.run(main())
    ```

See Also:
    - `project_x_py.client.cache.CacheMixin`
    - `project_x_py.client.base.ProjectXBase`
    - `project_x_py.client.trading.TradingMixin`
"""

import datetime
import re
import time
from typing import TYPE_CHECKING, Any

import polars as pl
import pytz

from project_x_py.exceptions import ProjectXInstrumentError
from project_x_py.models import Instrument
from project_x_py.utils import (
    ErrorMessages,
    LogContext,
    LogMessages,
    ProjectXLogger,
    format_error_message,
    handle_errors,
    validate_response,
)

if TYPE_CHECKING:
    from project_x_py.types import ProjectXClientProtocol

logger = ProjectXLogger.get_logger(__name__)


class MarketDataMixin:
    """Mixin class providing market data functionality."""

    @handle_errors("get instrument")
    @validate_response(required_fields=["success", "contracts"])
    async def get_instrument(
        self: "ProjectXClientProtocol", symbol: str, live: bool = False
    ) -> Instrument:
        """
        Get detailed instrument information with caching.

        Args:
            symbol: Trading symbol (e.g., 'NQ', 'ES', 'MGC') or full contract ID
                   (e.g., 'CON.F.US.MNQ.U25')
            live: If True, only return live/active contracts (default: False)

        Returns:
            Instrument object with complete contract details

        Example:
            >>> # V3: Get instrument with automatic contract selection
            >>> instrument = await client.get_instrument("NQ")
            >>> print(f"Trading {instrument.symbol} - {instrument.name}")
            >>> print(f"Contract ID: {instrument.id}")
            >>> print(f"Tick size: {instrument.tick_size}")
            >>> print(f"Tick value: ${instrument.tick_value}")
            >>> # V3: Get specific contract by full ID
            >>> mnq_contract = await client.get_instrument("CON.F.US.MNQ.U25")
            >>> print(f"Specific contract: {mnq_contract.symbol}")
        """
        with LogContext(
            logger,
            operation="get_instrument",
            symbol=symbol,
            live=live,
        ):
            await self._ensure_authenticated()

            # Check cache first
            cached_instrument = self.get_cached_instrument(symbol)
            if cached_instrument:
                logger.debug(LogMessages.CACHE_HIT, extra={"symbol": symbol})
                return cached_instrument

            logger.debug(LogMessages.CACHE_MISS, extra={"symbol": symbol})

            # Check if this is a full contract ID (e.g., CON.F.US.MNQ.U25)
            # If so, extract the base symbol for searching
            search_symbol = symbol
            is_contract_id = False
            if symbol.startswith("CON.") and symbol.count(".") >= 3:
                is_contract_id = True
                # Extract base symbol from contract ID
                # CON.F.US.MNQ.U25 -> MNQ
                parts = symbol.split(".")
                if len(parts) >= 4:
                    search_symbol = parts[3]
                    # Remove any month/year suffix (e.g., U25 -> base symbol)
                    futures_pattern = re.compile(r"^(.+?)([FGHJKMNQUVXZ]\d{1,2})$")
                    match = futures_pattern.match(search_symbol)
                    if match:
                        search_symbol = match.group(1)

            # Search for instrument
            payload = {"searchText": search_symbol, "live": live}
            response = await self._make_request(
                "POST", "/Contract/search", data=payload
            )

            if not response or not response.get("success", False):
                raise ProjectXInstrumentError(
                    format_error_message(
                        ErrorMessages.INSTRUMENT_NOT_FOUND, symbol=symbol
                    )
                )

            contracts_data = response.get("contracts", [])
            if not contracts_data:
                raise ProjectXInstrumentError(
                    format_error_message(
                        ErrorMessages.INSTRUMENT_NOT_FOUND, symbol=symbol
                    )
                )

            # Select best match
            if is_contract_id:
                # If searching by contract ID, try to find exact match
                best_match = None
                for contract in contracts_data:
                    if contract.get("id") == symbol:
                        best_match = contract
                        break

                # If no exact match by ID, use the selection logic with search_symbol
                if best_match is None:
                    best_match = self._select_best_contract(
                        contracts_data, search_symbol
                    )
            else:
                best_match = self._select_best_contract(contracts_data, symbol)

            instrument = Instrument(**best_match)

            # Cache the result
            self.cache_instrument(symbol, instrument)
            logger.debug(LogMessages.CACHE_UPDATE, extra={"symbol": symbol})

            # Periodic cache cleanup
            if time.time() - self.last_cache_cleanup > 3600:  # Every hour
                await self._cleanup_cache()

            return instrument

    def _select_best_contract(
        self: "ProjectXClientProtocol",
        instruments: list[dict[str, Any]],
        search_symbol: str,
    ) -> dict[str, Any]:
        """
        Select the best matching contract from search results.

        This method implements smart contract selection logic for futures and other
        instruments, ensuring the most appropriate contract is selected based on
        the search criteria. The selection algorithm follows these priorities:

        1. Exact symbol match (case-insensitive)
        2. For futures contracts:
           - Identifies the base symbol (e.g., "ES" from "ESM23")
           - Groups contracts by base symbol
           - Selects the front month contract (chronologically closest expiration)
        3. For micro contracts, ensures proper matching (e.g., "MNQ" for micro Nasdaq)
        4. Falls back to the first result if no better match is found

        The futures month codes follow CME convention: F(Jan), G(Feb), H(Mar), J(Apr),
        K(May), M(Jun), N(Jul), Q(Aug), U(Sep), V(Oct), X(Nov), Z(Dec)

        Args:
            instruments: List of instrument dictionaries from search results
            search_symbol: Original search symbol provided by the user

        Returns:
            dict[str, Any]: Best matching instrument dictionary with complete contract details

        Raises:
            ProjectXInstrumentError: If no instruments are found for the given symbol
        """
        if not instruments:
            raise ProjectXInstrumentError(f"No instruments found for: {search_symbol}")

        search_upper = search_symbol.upper()

        # First try exact match
        for inst in instruments:
            if inst.get("symbol", "").upper() == search_upper:
                return inst

        # For futures, try to find the front month
        # Extract base symbol and find all contracts
        futures_pattern = re.compile(r"^(.+?)([FGHJKMNQUVXZ]\d{1,2})$")
        base_symbols: dict[str, list[dict[str, Any]]] = {}

        for inst in instruments:
            symbol = inst.get("symbol", "").upper()
            match = futures_pattern.match(symbol)
            if match:
                base = match.group(1)
                if base not in base_symbols:
                    base_symbols[base] = []
                base_symbols[base].append(inst)

        # Find contracts matching our search
        matching_base = None
        for base in base_symbols:
            if base == search_upper or search_upper.startswith(base):
                matching_base = base
                break

        if matching_base and base_symbols[matching_base]:
            # Sort by symbol to get front month (alphabetical = chronological for futures)
            sorted_contracts = sorted(
                base_symbols[matching_base], key=lambda x: x.get("symbol", "")
            )
            return sorted_contracts[0]

        # Default to first result
        return instruments[0]

    @handle_errors("search instruments")
    @validate_response(required_fields=["success", "contracts"])
    async def search_instruments(
        self: "ProjectXClientProtocol", query: str, live: bool = False
    ) -> list[Instrument]:
        """
        Search for instruments by symbol or name.

        Args:
            query: Search query (symbol or partial name)
            live: If True, search only live/active instruments

        Returns:
            List of Instrument objects matching the query

        Example:
            >>> # V3: Search for instruments by symbol or name
            >>> instruments = await client.search_instruments("gold")
            >>> for inst in instruments:
            >>>     print(f"{inst.symbol}: {inst.name}")
            >>>     print(f"  Contract ID: {inst.id}")
            >>>     print(f"  Description: {inst.description}")
            >>>     print(f"  Exchange: {inst.exchange}")
        """
        with LogContext(
            logger,
            operation="search_instruments",
            query=query,
            live=live,
        ):
            await self._ensure_authenticated()

            logger.debug(LogMessages.DATA_FETCH, extra={"query": query})

            payload = {"searchText": query, "live": live}
            response = await self._make_request(
                "POST", "/Contract/search", data=payload
            )

            if not response or not response.get("success", False):
                return []

            contracts_data = response.get("contracts", [])
            instruments = [Instrument(**contract) for contract in contracts_data]

            logger.debug(
                LogMessages.DATA_RECEIVED,
                extra={"count": len(instruments), "query": query},
            )

            return instruments

    @handle_errors("get bars")
    async def get_bars(
        self: "ProjectXClientProtocol",
        symbol: str,
        days: int = 8,
        interval: int = 5,
        unit: int = 2,
        limit: int | None = None,
        partial: bool = True,
        start_time: datetime.datetime | None = None,
        end_time: datetime.datetime | None = None,
    ) -> pl.DataFrame:
        """
        Retrieve historical OHLCV bar data for an instrument.

        This method fetches historical market data with intelligent caching and
        timezone handling. The data is returned as a Polars DataFrame optimized
        for financial analysis and technical indicator calculations.

        Args:
            symbol: Symbol of the instrument (e.g., "MGC", "MNQ", "ES")
            days: Number of days of historical data (default: 8, ignored if start_time/end_time provided)
            interval: Interval between bars in the specified unit (default: 5)
            unit: Time unit for the interval (default: 2 for minutes)
                  1=Second, 2=Minute, 3=Hour, 4=Day, 5=Week, 6=Month
            limit: Maximum number of bars to retrieve (auto-calculated if None)
            partial: Include incomplete/partial bars (default: True)
            start_time: Optional start datetime (overrides days if provided)
            end_time: Optional end datetime (defaults to now if not provided)

        Returns:
            pl.DataFrame: DataFrame with OHLCV data and timezone-aware timestamps
                Columns: timestamp, open, high, low, close, volume
                Timezone: Converted to your configured timezone (default: US/Central)

        Raises:
            ProjectXInstrumentError: If instrument not found or invalid
            ProjectXDataError: If data retrieval fails or invalid response

        Example:
            >>> # V3: Get historical OHLCV data as Polars DataFrame
            >>> # Get 5 days of 15-minute gold data
            >>> data = await client.get_bars("MGC", days=5, interval=15)
            >>> print(f"Retrieved {len(data)} bars")
            >>> print(f"Columns: {data.columns}")
            >>> print(
            ...     f"Date range: {data['timestamp'].min()} to {data['timestamp'].max()}"
            ... )
            >>> # V3: Process with Polars operations
            >>> daily_highs = data.group_by_dynamic("timestamp", every="1d").agg(
            ...     pl.col("high").max()
            ... )
            >>> print(f"Daily highs: {daily_highs}")
            >>> # V3: Different time units available
            >>> # unit=1 (seconds), 2 (minutes), 3 (hours), 4 (days)
            >>> hourly_data = await client.get_bars("ES", days=1, interval=1, unit=3)
            >>> # V3: Use specific time range
            >>> from datetime import datetime
            >>> start = datetime(2025, 1, 1, 9, 30)
            >>> end = datetime(2025, 1, 1, 16, 0)
            >>> data = await client.get_bars("ES", start_time=start, end_time=end)
        """
        with LogContext(
            logger,
            operation="get_bars",
            symbol=symbol,
            days=days,
            interval=interval,
            unit=unit,
            partial=partial,
        ):
            await self._ensure_authenticated()

            # Calculate date range
            from datetime import timedelta

            if start_time is not None or end_time is not None:
                # Use provided time range
                if start_time is not None:
                    # Ensure timezone awareness
                    if start_time.tzinfo is None:
                        start_date = pytz.UTC.localize(start_time)
                    else:
                        start_date = start_time.astimezone(pytz.UTC)
                else:
                    # Default to days parameter ago if only end_time provided
                    start_date = datetime.datetime.now(pytz.UTC) - timedelta(days=days)

                if end_time is not None:
                    # Ensure timezone awareness
                    if end_time.tzinfo is None:
                        end_date = pytz.UTC.localize(end_time)
                    else:
                        end_date = end_time.astimezone(pytz.UTC)
                else:
                    # Default to now if only start_time provided
                    end_date = datetime.datetime.now(pytz.UTC)

                # Calculate days for cache key (approximate)
                days_calc = int((end_date - start_date).total_seconds() / 86400)
                cache_key = f"{symbol}_{start_date.isoformat()}_{end_date.isoformat()}_{interval}_{unit}_{partial}"
            else:
                # Use days parameter
                start_date = datetime.datetime.now(pytz.UTC) - timedelta(days=days)
                end_date = datetime.datetime.now(pytz.UTC)
                days_calc = days
                cache_key = f"{symbol}_{days}_{interval}_{unit}_{partial}"

            # Check market data cache
            cached_data = self.get_cached_market_data(cache_key)
            if cached_data is not None:
                logger.debug(LogMessages.CACHE_HIT, extra={"cache_key": cache_key})
                return cached_data

            logger.debug(
                LogMessages.DATA_FETCH,
                extra={"symbol": symbol, "days": days_calc, "interval": interval},
            )

            # Lookup instrument
            instrument = await self.get_instrument(symbol)

        # Calculate limit based on unit type
        if limit is None:
            if unit == 1:  # Seconds
                total_seconds = int((end_date - start_date).total_seconds())
                limit = int(total_seconds / interval)
            elif unit == 2:  # Minutes
                total_minutes = int((end_date - start_date).total_seconds() / 60)
                limit = int(total_minutes / interval)
            elif unit == 3:  # Hours
                total_hours = int((end_date - start_date).total_seconds() / 3600)
                limit = int(total_hours / interval)
            else:  # Days or other units
                total_minutes = int((end_date - start_date).total_seconds() / 60)
                limit = int(total_minutes / interval)

        # Prepare payload
        payload = {
            "contractId": instrument.id,
            "live": False,
            "startTime": start_date.isoformat(),
            "endTime": end_date.isoformat(),
            "unit": unit,
            "unitNumber": interval,
            "limit": limit,
            "includePartialBar": partial,
        }

        # Fetch data using correct endpoint
        response = await self._make_request(
            "POST", "/History/retrieveBars", data=payload
        )

        if not response:
            return pl.DataFrame()

        # Handle the response format
        if not response.get("success", False):
            error_msg = response.get("errorMessage", "Unknown error")
            self.logger.error(
                LogMessages.DATA_ERROR,
                extra={"operation": "get_history", "error": error_msg},
            )
            return pl.DataFrame()

        bars_data = response.get("bars", [])
        if not bars_data:
            return pl.DataFrame()

        # Convert to DataFrame and process
        data = (
            pl.DataFrame(bars_data)
            .sort("t")
            .rename(
                {
                    "t": "timestamp",
                    "o": "open",
                    "h": "high",
                    "l": "low",
                    "c": "close",
                    "v": "volume",
                }
            )
            .with_columns(
                # Optimized datetime conversion with cached timezone
                pl.col("timestamp")
                .str.to_datetime()
                .dt.replace_time_zone("UTC")
                .dt.convert_time_zone(self.config.timezone)
            )
        )

        if data.is_empty():
            return data

        # Sort by timestamp
        data = data.sort("timestamp")

        # Cache the result
        self.cache_market_data(cache_key, data)

        # Cleanup cache periodically
        if time.time() - self.last_cache_cleanup > 3600:
            await self._cleanup_cache()

        return data
