"""Tests for BracketOrderMixin (validation and successful flows)."""

from unittest.mock import AsyncMock

import pytest

from project_x_py.exceptions import ProjectXOrderError
from project_x_py.models import BracketOrderResponse, OrderPlaceResponse


@pytest.mark.asyncio
class TestBracketOrderMixin:
    """Unit tests for BracketOrderMixin bracket order placement."""

    @pytest.mark.parametrize(
        "side, entry, stop, target, err",
        [
            (0, 100.0, 101.0, 102.0, "stop loss (101.0) must be below entry (100.0)"),
            (0, 100.0, 99.0, 99.0, "take profit (99.0) must be above entry (100.0)"),
            (1, 100.0, 99.0, 98.0, "stop loss (99.0) must be above entry (100.0)"),
            (1, 100.0, 101.0, 101.0, "take profit (101.0) must be below entry (100.0)"),
        ],
    )
    async def test_bracket_order_validation_fails(self, side, entry, stop, target, err):
        """BracketOrderMixin validates stop/take_profit price relationships."""
        from project_x_py.order_manager.bracket_orders import BracketOrderMixin

        mixin = BracketOrderMixin()
        mixin.place_market_order = AsyncMock()
        mixin.place_limit_order = AsyncMock()
        mixin.place_stop_order = AsyncMock()
        mixin.position_orders = {
            "FOO": {"entry_orders": [], "stop_orders": [], "target_orders": []}
        }
        mixin.stats = {"bracket_orders": 0}
        with pytest.raises(ProjectXOrderError) as exc:
            await mixin.place_bracket_order(
                "FOO", side, 1, entry, stop, target, entry_type="limit"
            )
        assert err in str(exc.value)

    async def test_bracket_order_success_flow(self):
        """Successful bracket order path places all three orders and updates stats/caches."""
        from project_x_py.order_manager.bracket_orders import BracketOrderMixin

        mixin = BracketOrderMixin()
        mixin.place_market_order = AsyncMock(
            return_value=OrderPlaceResponse(
                orderId=1, success=True, errorCode=0, errorMessage=None
            )
        )
        mixin.place_limit_order = AsyncMock(
            side_effect=[
                OrderPlaceResponse(
                    orderId=2, success=True, errorCode=0, errorMessage=None
                ),
                OrderPlaceResponse(
                    orderId=3, success=True, errorCode=0, errorMessage=None
                ),
            ]
        )
        mixin.place_stop_order = AsyncMock(
            return_value=OrderPlaceResponse(
                orderId=4, success=True, errorCode=0, errorMessage=None
            )
        )
        mixin.position_orders = {
            "BAR": {"entry_orders": [], "stop_orders": [], "target_orders": []}
        }
        mixin.stats = {"bracket_orders": 0}

        # Entry type = limit
        resp = await mixin.place_bracket_order(
            "BAR", 0, 2, 100.0, 99.0, 103.0, entry_type="limit"
        )
        assert isinstance(resp, BracketOrderResponse)
        assert resp.success
        assert resp.entry_order_id == 2
        assert resp.stop_order_id == 4
        assert resp.target_order_id == 3
        assert mixin.position_orders["BAR"]["entry_orders"][-1] == 2
        assert mixin.position_orders["BAR"]["stop_orders"][-1] == 4
        assert mixin.position_orders["BAR"]["target_orders"][-1] == 3
        assert mixin.stats["bracket_orders"] == 1
