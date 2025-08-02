"""Tests for PositionOrderMixin helpers and tracking."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from project_x_py.models import OrderPlaceResponse
from project_x_py.order_manager.position_orders import PositionOrderMixin


@pytest.mark.asyncio
class TestPositionOrderMixin:
    """Unit tests for PositionOrderMixin helpers (track, untrack, add_stop_loss, add_take_profit)."""

    async def test_track_and_untrack_order(self):
        """track_order_for_position and untrack_order mutate position_orders/order_to_position correctly."""
        mixin = PositionOrderMixin()
        mixin.order_lock = asyncio.Lock()
        mixin.position_orders = {}
        mixin.order_to_position = {}

        await mixin.track_order_for_position("BAZ", 1001, "entry")
        assert 1001 in mixin.order_to_position
        assert mixin.order_to_position[1001] == "BAZ"
        assert mixin.position_orders["BAZ"]["entry_orders"] == [1001]

        mixin.untrack_order(1001)
        assert 1001 not in mixin.order_to_position
        assert mixin.position_orders["BAZ"]["entry_orders"] == []

    async def test_add_stop_loss_success(self):
        """add_stop_loss places stop order and tracks it."""
        mixin = PositionOrderMixin()
        mixin.project_x = MagicMock()
        position = MagicMock(contractId="QWE", size=2)
        mixin.project_x.search_open_positions = AsyncMock(return_value=[position])
        mixin.place_stop_order = AsyncMock(
            return_value=OrderPlaceResponse(
                orderId=201, success=True, errorCode=0, errorMessage=None
            )
        )
        mixin.track_order_for_position = AsyncMock()
        resp = await mixin.add_stop_loss("QWE", 99.0)
        assert resp.orderId == 201
        mixin.track_order_for_position.assert_awaited_once_with(
            "QWE", 201, "stop", None
        )

    async def test_add_stop_loss_no_position(self):
        """add_stop_loss returns None if no position found."""
        mixin = PositionOrderMixin()
        mixin.project_x = MagicMock()
        mixin.project_x.search_open_positions = AsyncMock(return_value=[])
        mixin.place_stop_order = AsyncMock()
        resp = await mixin.add_stop_loss("AAA", 100.0)
        assert resp is None

    async def test_add_take_profit_success(self):
        """add_take_profit places limit order and tracks it."""
        mixin = PositionOrderMixin()
        mixin.project_x = MagicMock()
        position = MagicMock(contractId="ZXC", size=3)
        mixin.project_x.search_open_positions = AsyncMock(return_value=[position])
        mixin.place_limit_order = AsyncMock(
            return_value=OrderPlaceResponse(
                orderId=301, success=True, errorCode=0, errorMessage=None
            )
        )
        mixin.track_order_for_position = AsyncMock()
        resp = await mixin.add_take_profit("ZXC", 120.0)
        assert resp.orderId == 301
        mixin.track_order_for_position.assert_awaited_once_with(
            "ZXC", 301, "target", None
        )

    async def test_add_take_profit_no_position(self):
        """add_take_profit returns None if no position found."""
        mixin = PositionOrderMixin()
        mixin.project_x = MagicMock()
        mixin.project_x.search_open_positions = AsyncMock(return_value=[])
        mixin.place_limit_order = AsyncMock()
        resp = await mixin.add_take_profit("TUV", 55.0)
        assert resp is None
