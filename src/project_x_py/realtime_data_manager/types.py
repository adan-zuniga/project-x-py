"""Type definitions and protocols for real-time data management."""

import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

import polars as pl
import pytz

if TYPE_CHECKING:
    from collections import defaultdict

    from project_x_py.client import ProjectXBase
    from project_x_py.realtime import ProjectXRealtimeClient


class RealtimeDataManagerProtocol(Protocol):
    """Protocol defining the interface for RealtimeDataManager components."""

    # Core attributes
    instrument: str
    project_x: "ProjectXBase"
    realtime_client: "ProjectXRealtimeClient"
    logger: Any
    timezone: pytz.tzinfo.BaseTzInfo

    # Timeframe configuration
    timeframes: dict[str, dict[str, Any]]

    # Data storage
    data: dict[str, pl.DataFrame]
    current_tick_data: list[dict[str, Any]]
    last_bar_times: dict[str, datetime]

    # Synchronization
    data_lock: asyncio.Lock
    is_running: bool
    callbacks: dict[str, list[Any]]
    indicator_cache: "defaultdict[str, dict[str, Any]]"

    # Contract and subscription
    contract_id: str | None

    # Memory management settings
    max_bars_per_timeframe: int
    tick_buffer_size: int
    cleanup_interval: float
    last_cleanup: float
    memory_stats: dict[str, Any]

    # Background tasks
    _cleanup_task: asyncio.Task[None] | None

    # Methods required by mixins
    async def _cleanup_old_data(self) -> None: ...
    async def _periodic_cleanup(self) -> None: ...
    async def _trigger_callbacks(
        self, event_type: str, data: dict[str, Any]
    ) -> None: ...
    async def _on_quote_update(self, callback_data: dict[str, Any]) -> None: ...
    async def _on_trade_update(self, callback_data: dict[str, Any]) -> None: ...
    async def _process_tick_data(self, tick: dict[str, Any]) -> None: ...
    async def _update_timeframe_data(
        self, tf_key: str, timestamp: datetime, price: float, volume: int
    ) -> None: ...
    def _calculate_bar_time(
        self, timestamp: datetime, interval: int, unit: int
    ) -> datetime: ...
    def _parse_and_validate_trade_payload(
        self, trade_data: Any
    ) -> dict[str, Any] | None: ...
    def _parse_and_validate_quote_payload(
        self, quote_data: Any
    ) -> dict[str, Any] | None: ...
    def _symbol_matches_instrument(self, symbol: str) -> bool: ...

    # Public interface methods
    async def initialize(self, initial_days: int = 1) -> bool: ...
    async def start_realtime_feed(self) -> bool: ...
    async def stop_realtime_feed(self) -> None: ...
    async def get_data(
        self, timeframe: str = "5min", bars: int | None = None
    ) -> pl.DataFrame | None: ...
    async def get_current_price(self) -> float | None: ...
    async def get_mtf_data(self) -> dict[str, pl.DataFrame]: ...
    async def add_callback(
        self,
        event_type: str,
        callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None],
    ) -> None: ...
    def get_memory_stats(self) -> dict[str, Any]: ...
    def get_realtime_validation_status(self) -> dict[str, Any]: ...
    async def cleanup(self) -> None: ...
