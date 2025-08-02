"""OrderManager test-specific fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from project_x_py.models import Account, OrderPlaceResponse
from project_x_py.order_manager.core import OrderManager

@pytest.fixture
def order_manager(initialized_client):
    """
    Fixture for an OrderManager wired to a mocked ProjectX client.
    Also patches align_price_to_tick_size to return the input price for determinism.
    """
    # Patch align_price_to_tick_size globally for all tests in this module
    patcher = patch(
        "project_x_py.order_manager.utils.align_price_to_tick_size",
        new=AsyncMock(side_effect=lambda price, *_args, **_kwargs: price),
    )
    patcher.start()

    # Set up a dummy account
    initialized_client.account_info = Account(
        id=12345,
        name="Test Account",
        balance=100000.0,
        canTrade=True,
        isVisible=True,
        simulated=True,
    )

    om = OrderManager(initialized_client)
    yield om

    patcher.stop()


@pytest.fixture
def make_order_response():
    """
    Helper to build a dict compatible with OrderPlaceResponse.
    """
    def _make(order_id, success=True, error_code=0, error_msg=None):
        return {
            "orderId": order_id,
            "success": success,
            "errorCode": error_code,
            "errorMessage": error_msg,
        }
    return _make