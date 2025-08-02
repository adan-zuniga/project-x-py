"""Protocol definitions for order manager mixins."""

import asyncio
from typing import TYPE_CHECKING, Any, Protocol

from project_x_py.models import Order, OrderPlaceResponse

if TYPE_CHECKING:
    from project_x_py.client import ProjectXBase
    from project_x_py.order_manager.types import OrderStats
    from project_x_py.realtime import ProjectXRealtimeClient


class OrderManagerProtocol(Protocol):
    """Protocol defining the interface that mixins expect from OrderManager."""

    project_x: "ProjectXBase"
    realtime_client: "ProjectXRealtimeClient | None"
    order_lock: asyncio.Lock
    _realtime_enabled: bool
    stats: "OrderStats"

    # From tracking mixin
    tracked_orders: dict[str, dict[str, Any]]
    order_status_cache: dict[str, int]
    order_callbacks: dict[str, list[Any]]
    position_orders: dict[str, dict[str, list[int]]]
    order_to_position: dict[int, str]

    # Methods that mixins need
    async def place_order(
        self,
        contract_id: str,
        order_type: int,
        side: int,
        size: int,
        limit_price: float | None = None,
        stop_price: float | None = None,
        trail_price: float | None = None,
        custom_tag: str | None = None,
        linked_order_id: int | None = None,
        account_id: int | None = None,
    ) -> OrderPlaceResponse: ...

    async def place_market_order(
        self, contract_id: str, side: int, size: int, account_id: int | None = None
    ) -> OrderPlaceResponse: ...

    async def place_limit_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        limit_price: float,
        account_id: int | None = None,
    ) -> OrderPlaceResponse: ...

    async def place_stop_order(
        self,
        contract_id: str,
        side: int,
        size: int,
        stop_price: float,
        account_id: int | None = None,
    ) -> OrderPlaceResponse: ...

    async def get_order_by_id(self, order_id: int) -> Order | None: ...

    async def cancel_order(
        self, order_id: int, account_id: int | None = None
    ) -> bool: ...

    async def modify_order(
        self,
        order_id: int,
        limit_price: float | None = None,
        stop_price: float | None = None,
        size: int | None = None,
    ) -> bool: ...

    async def get_tracked_order_status(
        self, order_id: str, wait_for_cache: bool = False
    ) -> dict[str, Any] | None: ...

    async def track_order_for_position(
        self,
        contract_id: str,
        order_id: int,
        order_type: str = "entry",
        account_id: int | None = None,
    ) -> None: ...

    def untrack_order(self, order_id: int) -> None: ...

    def get_position_orders(self, contract_id: str) -> dict[str, list[int]]: ...

    async def _on_order_update(
        self, order_data: dict[str, Any] | list[Any]
    ) -> None: ...

    async def _on_trade_execution(
        self, trade_data: dict[str, Any] | list[Any]
    ) -> None: ...

    async def cancel_position_orders(
        self,
        contract_id: str,
        order_types: list[str] | None = None,
        account_id: int | None = None,
    ) -> dict[str, int]: ...

    async def update_position_order_sizes(
        self, contract_id: str, new_size: int, account_id: int | None = None
    ) -> dict[str, Any]: ...

    async def sync_orders_with_position(
        self,
        contract_id: str,
        target_size: int,
        cancel_orphaned: bool = True,
        account_id: int | None = None,
    ) -> dict[str, Any]: ...

    async def on_position_closed(
        self, contract_id: str, account_id: int | None = None
    ) -> None: ...
