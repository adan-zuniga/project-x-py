"""Tests for OrderManager core API."""

from unittest.mock import AsyncMock

import pytest

from project_x_py.exceptions import ProjectXOrderError
from project_x_py.models import Order, OrderPlaceResponse


class TestOrderManagerCore:
    """Unit tests for OrderManager core public methods."""

    @pytest.mark.asyncio
    async def test_place_market_order_success(self, order_manager, make_order_response):
        """place_market_order hits /Order/place with correct payload and updates stats."""
        # Patch _make_request to return a success response
        order_manager.project_x._make_request = AsyncMock(
            return_value=make_order_response(42)
        )
        # Should increment orders_placed
        start_count = order_manager.stats["orders_placed"]
        resp = await order_manager.place_market_order("MGC", 0, 2)
        assert isinstance(resp, OrderPlaceResponse)
        assert resp.orderId == 42
        assert order_manager.project_x._make_request.call_count == 1
        call_args = order_manager.project_x._make_request.call_args[1]["data"]
        assert call_args["contractId"] == "MGC"
        assert call_args["type"] == 2
        assert call_args["side"] == 0
        assert call_args["size"] == 2
        assert order_manager.stats["orders_placed"] == start_count + 1

    @pytest.mark.asyncio
    async def test_place_order_error_raises(self, order_manager, make_order_response):
        """place_order raises ProjectXOrderError when API fails."""
        order_manager.project_x._make_request = AsyncMock(
            return_value={"success": False, "errorMessage": "Test error"}
        )
        with pytest.raises(ProjectXOrderError):
            await order_manager.place_order("MGC", 2, 0, 1)

    @pytest.mark.asyncio
    async def test_search_open_orders_populates_cache(
        self, order_manager, make_order_response
    ):
        """search_open_orders converts API dicts to Order objects and populates cache."""
        resp_order = {
            "id": 101,
            "accountId": 12345,
            "contractId": "MGC",
            "creationTimestamp": "2024-01-01T01:00:00Z",
            "updateTimestamp": None,
            "status": 1,
            "type": 1,
            "side": 0,
            "size": 2,
        }
        order_manager.project_x.account_info.id = 12345
        order_manager.project_x._make_request = AsyncMock(
            return_value={"success": True, "orders": [resp_order]}
        )
        orders = await order_manager.search_open_orders()
        assert isinstance(orders[0], Order)
        assert order_manager.tracked_orders[str(resp_order["id"])] == resp_order
        assert order_manager.order_status_cache[str(resp_order["id"])] == 1

    @pytest.mark.asyncio
    async def test_is_order_filled_cache_hit(self, order_manager):
        """is_order_filled returns True from cache and does not call _make_request if cached."""
        order_manager._realtime_enabled = True
        order_manager.order_status_cache["77"] = 2  # 2=Filled
        order_manager.project_x._make_request = AsyncMock()
        result = await order_manager.is_order_filled(77)
        assert result is True
        order_manager.project_x._make_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_is_order_filled_fallback(self, order_manager):
        """is_order_filled falls back to get_order_by_id when not cached."""
        order_manager._realtime_enabled = False
        dummy_order = Order(
            id=55,
            accountId=12345,
            contractId="CL",
            creationTimestamp="2024-01-01T01:00:00Z",
            updateTimestamp=None,
            status=2,
            type=1,
            side=0,
            size=1,
        )
        order_manager.get_order_by_id = AsyncMock(return_value=dummy_order)
        result = await order_manager.is_order_filled(55)
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_order_success_and_failure(self, order_manager):
        """cancel_order updates caches/stats on success and handles failure."""
        # Setup tracked order
        order_manager.tracked_orders["888"] = {"status": 1}
        order_manager.order_status_cache["888"] = 1
        start = order_manager.stats["orders_cancelled"]
        order_manager.project_x._make_request = AsyncMock(
            return_value={"success": True}
        )
        assert await order_manager.cancel_order(888) is True
        assert order_manager.tracked_orders["888"]["status"] == 3
        assert order_manager.order_status_cache["888"] == 3
        assert order_manager.stats["orders_cancelled"] == start + 1

        order_manager.project_x._make_request = AsyncMock(
            return_value={"success": False, "errorMessage": "fail"}
        )
        with pytest.raises(ProjectXOrderError) as exc_info:
            await order_manager.cancel_order(888)
        assert "Failed to cancel order 888: fail" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_modify_order_success_and_aligns(self, order_manager):
        """modify_order aligns prices, makes API call, returns True on success."""
        dummy_order = Order(
            id=12,
            accountId=12345,
            contractId="MGC",
            creationTimestamp="2024-01-01T01:00:00Z",
            updateTimestamp=None,
            status=1,
            type=1,
            side=0,
            size=1,
        )
        order_manager.get_order_by_id = AsyncMock(return_value=dummy_order)
        order_manager.project_x._make_request = AsyncMock(
            return_value={"success": True}
        )
        assert await order_manager.modify_order(12, limit_price=2000.5) is True

        order_manager.project_x._make_request = AsyncMock(
            return_value={"success": False, "errorMessage": "modification failed"}
        )
        with pytest.raises(ProjectXOrderError) as exc_info:
            await order_manager.modify_order(12, limit_price=2001.5)
        assert "Failed to modify order 12" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_order_statistics(self, order_manager):
        """get_order_statistics returns expected stats."""
        stats = await order_manager.get_order_statistics()
        # Check for key statistics fields
        assert "orders_placed" in stats
        assert "orders_filled" in stats
        assert "orders_cancelled" in stats
        assert "fill_rate" in stats
        assert "market_orders" in stats
        assert "limit_orders" in stats
        assert "bracket_orders" in stats
