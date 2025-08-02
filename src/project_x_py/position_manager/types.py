"""Type definitions and protocols for position management."""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import asyncio

    from project_x_py.client import ProjectXBase
    from project_x_py.models import Position
    from project_x_py.order_manager import OrderManager
    from project_x_py.realtime import ProjectXRealtimeClient


class PositionManagerProtocol(Protocol):
    """Protocol defining the interface that mixins expect from PositionManager."""

    project_x: "ProjectXBase"
    logger: Any
    position_lock: "asyncio.Lock"
    realtime_client: "ProjectXRealtimeClient | None"
    _realtime_enabled: bool
    order_manager: "OrderManager | None"
    _order_sync_enabled: bool
    tracked_positions: dict[str, "Position"]
    position_history: dict[str, list[dict[str, Any]]]
    position_callbacks: dict[str, list[Any]]
    _monitoring_active: bool
    _monitoring_task: "asyncio.Task[None] | None"
    position_alerts: dict[str, dict[str, Any]]
    stats: dict[str, Any]
    risk_settings: dict[str, float]

    # Methods needed by mixins
    async def get_all_positions(
        self, account_id: int | None = None
    ) -> list["Position"]: ...

    async def get_position(
        self, contract_id: str, account_id: int | None = None
    ) -> "Position | None": ...

    async def refresh_positions(self, account_id: int | None = None) -> bool: ...

    async def _trigger_callbacks(self, event_type: str, data: Any) -> None: ...

    async def _process_position_data(self, position_data: dict[str, Any]) -> None: ...

    async def _check_position_alerts(
        self,
        contract_id: str,
        current_position: "Position",
        old_position: "Position | None",
    ) -> None: ...

    def _validate_position_payload(self, position_data: dict[str, Any]) -> bool: ...

    def _generate_risk_warnings(
        self,
        positions: list["Position"],
        portfolio_risk: float,
        largest_position_risk: float,
    ) -> list[str]: ...

    def _generate_sizing_warnings(
        self, risk_percentage: float, size: int
    ) -> list[str]: ...

    async def _on_position_update(
        self, data: dict[str, Any] | list[dict[str, Any]]
    ) -> None: ...

    async def _on_account_update(self, data: dict[str, Any]) -> None: ...

    async def _setup_realtime_callbacks(self) -> None: ...

    async def calculate_position_pnl(
        self,
        position: "Position",
        current_price: float,
        point_value: float | None = None,
    ) -> dict[str, Any]: ...

    async def _monitoring_loop(self, refresh_interval: int) -> None: ...

    async def close_position_direct(
        self, contract_id: str, account_id: int | None = None
    ) -> dict[str, Any]: ...

    async def partially_close_position(
        self, contract_id: str, close_size: int, account_id: int | None = None
    ) -> dict[str, Any]: ...

    async def get_portfolio_pnl(self) -> dict[str, Any]: ...

    async def get_risk_metrics(self) -> dict[str, Any]: ...

    def get_position_statistics(self) -> dict[str, Any]: ...
