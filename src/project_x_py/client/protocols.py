"""Protocol definitions for client mixins."""

import datetime
import logging
from typing import TYPE_CHECKING, Any, Protocol

import httpx
import polars as pl

if TYPE_CHECKING:
    from project_x_py.client.rate_limiter import RateLimiter
    from project_x_py.models import Account, Instrument, Position, ProjectXConfig, Trade


class ProjectXClientProtocol(Protocol):
    """Protocol defining the interface that client mixins expect."""

    # Authentication attributes
    session_token: str
    token_expiry: "datetime.datetime | None"
    _authenticated: bool
    username: str
    api_key: str
    account_name: str | None
    account_info: "Account | None"
    logger: logging.Logger

    # HTTP client attributes
    _client: "httpx.AsyncClient | None"
    headers: dict[str, str]
    base_url: str
    config: "ProjectXConfig"
    rate_limiter: "RateLimiter"
    api_call_count: int

    # Cache attributes
    cache_hit_count: int
    cache_ttl: int
    last_cache_cleanup: float
    _instrument_cache: dict[str, "Instrument"]
    _instrument_cache_time: dict[str, float]
    _market_data_cache: dict[str, pl.DataFrame]
    _market_data_cache_time: dict[str, float]

    # Authentication methods
    def _should_refresh_token(self) -> bool: ...
    async def authenticate(self) -> None: ...
    async def _refresh_authentication(self) -> None: ...
    async def _ensure_authenticated(self) -> None: ...
    async def list_accounts(self) -> list["Account"]: ...

    # HTTP methods
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        retry_count: int = 0,
    ) -> Any: ...
    async def _create_client(self) -> httpx.AsyncClient: ...
    async def _ensure_client(self) -> httpx.AsyncClient: ...
    async def get_health_status(self) -> dict[str, Any]: ...

    # Cache methods
    async def _cleanup_cache(self) -> None: ...
    def get_cached_instrument(self, symbol: str) -> "Instrument | None": ...
    def cache_instrument(self, symbol: str, instrument: "Instrument") -> None: ...
    def get_cached_market_data(self, cache_key: str) -> pl.DataFrame | None: ...
    def cache_market_data(self, cache_key: str, data: pl.DataFrame) -> None: ...
    def clear_all_caches(self) -> None: ...

    # Market data methods
    async def get_instrument(self, symbol: str, live: bool = False) -> "Instrument": ...
    async def search_instruments(
        self, query: str, live: bool = False
    ) -> list["Instrument"]: ...
    async def get_bars(
        self,
        symbol: str,
        days: int = 8,
        interval: int = 5,
        unit: int = 2,
        limit: int | None = None,
        partial: bool = True,
    ) -> pl.DataFrame: ...
    def _select_best_contract(
        self, instruments: list[dict[str, Any]], search_symbol: str
    ) -> dict[str, Any]: ...

    # Trading methods
    async def get_positions(self) -> list["Position"]: ...
    async def search_open_positions(
        self, account_id: int | None = None
    ) -> list["Position"]: ...
    async def search_trades(
        self,
        start_date: "datetime.datetime | None" = None,
        end_date: "datetime.datetime | None" = None,
        contract_id: str | None = None,
        account_id: int | None = None,
        limit: int = 100,
    ) -> list["Trade"]: ...
