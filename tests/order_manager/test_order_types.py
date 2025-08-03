"""Tests for OrderTypesMixin helpers (market/limit/stop/trailing-stop)."""

from unittest.mock import AsyncMock

import pytest


class DummyOrderManager:
    def __init__(self):
        self.place_order = AsyncMock()


@pytest.mark.asyncio
class TestOrderTypesMixin:
    """Unit tests for OrderTypesMixin order type wrappers."""

    async def test_place_market_order(self):
        """place_market_order delegates to place_order with order_type=2."""
        dummy = DummyOrderManager()
        from project_x_py.order_manager.order_types import OrderTypesMixin

        mixin = OrderTypesMixin()
        mixin.place_order = dummy.place_order
        await mixin.place_market_order("MGC", 0, 1)
        dummy.place_order.assert_awaited_once()
        args = dummy.place_order.call_args.kwargs
        assert args["order_type"] == 2

    async def test_place_limit_order(self):
        """place_limit_order delegates to place_order with order_type=1 and passes limit_price."""
        dummy = DummyOrderManager()
        from project_x_py.order_manager.order_types import OrderTypesMixin

        mixin = OrderTypesMixin()
        mixin.place_order = dummy.place_order
        await mixin.place_limit_order("MGC", 1, 2, 2040.0)
        args = dummy.place_order.call_args.kwargs
        assert args["order_type"] == 1
        assert args["limit_price"] == 2040.0

    async def test_place_stop_order(self):
        """place_stop_order delegates to place_order with order_type=4 and passes stop_price."""
        dummy = DummyOrderManager()
        from project_x_py.order_manager.order_types import OrderTypesMixin

        mixin = OrderTypesMixin()
        mixin.place_order = dummy.place_order
        await mixin.place_stop_order("MGC", 1, 2, 2030.0)
        args = dummy.place_order.call_args.kwargs
        assert args["order_type"] == 4
        assert args["stop_price"] == 2030.0

    async def test_place_trailing_stop_order(self):
        """place_trailing_stop_order delegates to place_order with order_type=5 and passes trail_price."""
        dummy = DummyOrderManager()
        from project_x_py.order_manager.order_types import OrderTypesMixin

        mixin = OrderTypesMixin()
        mixin.place_order = dummy.place_order
        await mixin.place_trailing_stop_order("MGC", 1, 2, 5.0)
        args = dummy.place_order.call_args.kwargs
        assert args["order_type"] == 5
        assert args["trail_price"] == 5.0

    async def test_place_join_bid_order(self):
        """place_join_bid_order delegates to place_order with order_type=6 and side=0 (buy)."""
        dummy = DummyOrderManager()
        from project_x_py.order_manager.order_types import OrderTypesMixin

        mixin = OrderTypesMixin()
        mixin.place_order = dummy.place_order
        await mixin.place_join_bid_order("MGC", 2)
        args = dummy.place_order.call_args.kwargs
        assert args["order_type"] == 6
        assert args["side"] == 0  # Buy side
        assert args["size"] == 2
        assert args["contract_id"] == "MGC"

    async def test_place_join_ask_order(self):
        """place_join_ask_order delegates to place_order with order_type=7 and side=1 (sell)."""
        dummy = DummyOrderManager()
        from project_x_py.order_manager.order_types import OrderTypesMixin

        mixin = OrderTypesMixin()
        mixin.place_order = dummy.place_order
        await mixin.place_join_ask_order("MGC", 3)
        args = dummy.place_order.call_args.kwargs
        assert args["order_type"] == 7
        assert args["side"] == 1  # Sell side
        assert args["size"] == 3
        assert args["contract_id"] == "MGC"
