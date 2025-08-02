"""Tests for AsyncOrderManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from project_x_py import ProjectX
from project_x_py.exceptions import ProjectXOrderError
from project_x_py.order_manager import OrderManager


def mock_instrument(id, tick_size=0.1):
    """Helper to create a mock instrument."""
    mock = MagicMock(id=id, tickSize=tick_size)
    mock.model_dump.return_value = {"id": id, "tickSize": tick_size}
    return mock


@pytest.fixture
def mock_async_client():
    """Create a mock AsyncProjectX client."""
    client = MagicMock(spec=ProjectX)
    client.account_info = MagicMock()
    client.account_info.id = 123
    client._make_request = AsyncMock()
    client.get_instrument = AsyncMock()
    return client


@pytest.fixture
def order_manager(mock_async_client):
    """Create an AsyncOrderManager instance."""
    return OrderManager(mock_async_client)


@pytest.mark.asyncio
async def test_order_manager_initialization(mock_async_client):
    """Test AsyncOrderManager initialization."""
    manager = OrderManager(mock_async_client)

    assert manager.project_x == mock_async_client
    assert manager.realtime_client is None
    assert manager._realtime_enabled is False
    assert manager.stats["orders_placed"] == 0
    assert isinstance(manager.order_lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_place_market_order(order_manager, mock_async_client):
    """Test placing a market order."""
    # Mock instrument resolution
    mock_async_client.get_instrument.return_value = mock_instrument("MGC-123", 0.1)

    # Mock order response
    mock_response = {
        "orderId": 12345,
        "success": True,
        "errorCode": 0,
        "errorMessage": None,
    }
    mock_async_client._make_request.return_value = mock_response

    # Place market order
    response = await order_manager.place_market_order("MGC", side=0, size=1)

    assert response is not None
    assert response.orderId == 12345
    assert order_manager.stats["orders_placed"] == 1

    # Verify API call
    mock_async_client._make_request.assert_called_once_with(
        "POST",
        "/orders",
        data={
            "accountId": 123,
            "contractId": "MGC-123",
            "side": 0,
            "size": 1,
            "orderType": 1,
            "timeInForce": 2,
            "reduceOnly": False,
        },
    )


@pytest.mark.asyncio
async def test_place_limit_order_with_price_alignment(order_manager, mock_async_client):
    """Test placing a limit order with automatic price alignment."""
    # Mock instrument with tick size 0.25
    mock_async_client.get_instrument.return_value = mock_instrument("NQ-123", 0.25)

    mock_response = {
        "orderId": 12346,
        "success": True,
        "errorCode": 0,
        "errorMessage": None,
    }
    mock_async_client._make_request.return_value = mock_response

    # Place limit order with unaligned price
    response = await order_manager.place_limit_order(
        "NQ", side=1, size=2, price=15001.12
    )

    assert response is not None
    assert response.orderId == 12346

    # Verify price was aligned to tick size (15001.12 -> 15001.00)
    call_args = mock_async_client._make_request.call_args[1]["data"]
    assert call_args["price"] == 15001.0  # Aligned to nearest 0.25


@pytest.mark.asyncio
async def test_place_stop_order(order_manager, mock_async_client):
    """Test placing a stop order."""
    mock_async_client.get_instrument.return_value = mock_instrument("ES-123", 0.25)

    mock_response = {
        "orderId": 12347,
        "success": True,
        "errorCode": 0,
        "errorMessage": None,
    }
    mock_async_client._make_request.return_value = mock_response

    response = await order_manager.place_stop_order(
        "ES", side=1, size=1, stop_price=4500.0
    )

    assert response is not None
    assert response.orderId == 12347

    # Verify stop order details
    call_args = mock_async_client._make_request.call_args[1]["data"]
    assert call_args["orderType"] == 3  # Stop order
    assert call_args["stopPrice"] == 4500.0


@pytest.mark.asyncio
async def test_place_bracket_order(order_manager, mock_async_client):
    """Test placing a bracket order."""
    mock_async_client.get_instrument.return_value = mock_instrument("MGC-123", 0.1)

    # Mock responses for entry, stop, and target orders
    mock_async_client._make_request.side_effect = [
        {"orderId": 12348, "success": True, "errorCode": 0, "errorMessage": None},
        {"orderId": 12349, "success": True, "errorCode": 0, "errorMessage": None},
        {"orderId": 12350, "success": True, "errorCode": 0, "errorMessage": None},
    ]

    # Place bracket order
    response = await order_manager.place_bracket_order(
        "MGC",
        side=0,  # Buy
        size=1,
        entry_type=2,  # Limit
        entry_price=2045.0,
        stop_loss_price=2040.0,
        take_profit_price=2055.0,
    )

    assert response is not None
    assert response.entry_order_id == 12348
    assert response.stop_order_id == 12349
    assert response.target_order_id == 12350
    assert order_manager.stats["bracket_orders_placed"] == 1

    # Verify position orders tracking
    assert 12348 in order_manager.position_orders["MGC-123"]["entry_orders"]
    assert 12349 in order_manager.position_orders["MGC-123"]["stop_orders"]
    assert 12350 in order_manager.position_orders["MGC-123"]["target_orders"]


@pytest.mark.asyncio
async def test_search_open_orders(order_manager, mock_async_client):
    """Test searching for open orders."""
    mock_orders = [
        {
            "id": 12351,
            "accountId": 123,
            "contractId": "MGC-123",
            "creationTimestamp": "2023-01-01T00:00:00.000Z",
            "updateTimestamp": None,
            "status": 0,  # Open
            "type": 2,  # Limit
            "side": 0,
            "size": 1,
            "limitPrice": 2045.0,
        },
        {
            "id": 12352,
            "accountId": 123,
            "contractId": "NQ-123",
            "creationTimestamp": "2023-01-01T00:00:00.000Z",
            "updateTimestamp": None,
            "status": 0,  # Open
            "type": 2,  # Limit
            "side": 1,
            "size": 2,
            "limitPrice": 15000.0,
        },
        {
            "id": 12353,
            "accountId": 123,
            "contractId": "ES-123",
            "creationTimestamp": "2023-01-01T00:00:00.000Z",
            "updateTimestamp": None,
            "status": 100,  # Filled - should be filtered out
            "type": 2,  # Limit
            "side": 0,
            "size": 1,
            "limitPrice": 4500.0,
        },
    ]

    mock_async_client._make_request.return_value = mock_orders
    mock_async_client.get_instrument.return_value = mock_instrument("MGC-123")

    # Search all open orders
    orders = await order_manager.search_open_orders()
    assert len(orders) == 2  # Only open orders
    assert all(order.status < 100 for order in orders)

    # Search with contract filter
    mgc_orders = await order_manager.search_open_orders(contract_id="MGC")
    mock_async_client._make_request.assert_called_with(
        "GET", "/orders/search", params={"accountId": 123, "contractId": "MGC-123"}
    )


@pytest.mark.asyncio
async def test_cancel_order(order_manager, mock_async_client):
    """Test cancelling an order."""
    order_id = 12354

    # Add order to tracked orders
    order_manager.tracked_orders[str(order_id)] = {"id": order_id, "status": 0}

    mock_async_client._make_request.return_value = {"success": True}

    success = await order_manager.cancel_order(order_id)

    assert success is True
    assert order_manager.stats["orders_cancelled"] == 1
    assert order_manager.order_status_cache[str(order_id)] == 200  # Cancelled

    mock_async_client._make_request.assert_called_once_with(
        "POST", f"/orders/{order_id}/cancel"
    )


@pytest.mark.asyncio
async def test_modify_order(order_manager, mock_async_client):
    """Test modifying an order."""
    order_id = 12355

    # Add order to tracked orders
    order_manager.tracked_orders[str(order_id)] = {
        "id": order_id,
        "contractId": "MGC-123",
        "price": 2045.0,
        "size": 1,
        "status": 0,
    }

    mock_async_client.get_instrument.return_value = mock_instrument("MGC-123", 0.1)
    mock_async_client._make_request.return_value = {"success": True}

    # Modify price
    success = await order_manager.modify_order(order_id, new_price=2046.5)

    assert success is True
    assert order_manager.stats["orders_modified"] == 1

    # Verify modification request
    mock_async_client._make_request.assert_called_with(
        "PUT", f"/orders/{order_id}", data={"price": 2046.5}
    )


@pytest.mark.asyncio
async def test_price_alignment():
    """Test price alignment to tick size."""
    manager = OrderManager(MagicMock())

    # Test various alignments
    assert manager._align_price_to_tick(100.12, 0.25) == 100.0
    assert manager._align_price_to_tick(100.13, 0.25) == 100.25
    assert manager._align_price_to_tick(100.37, 0.25) == 100.25
    assert manager._align_price_to_tick(100.38, 0.25) == 100.5
    assert manager._align_price_to_tick(100.0, 0.25) == 100.0

    # Test with different tick sizes
    assert manager._align_price_to_tick(2045.12, 0.1) == 2045.1
    assert manager._align_price_to_tick(2045.16, 0.1) == 2045.2
    assert manager._align_price_to_tick(15001.12, 0.01) == 15001.12


@pytest.mark.asyncio
async def test_bracket_order_with_offsets(order_manager, mock_async_client):
    """Test placing a bracket order with offset calculations."""
    mock_async_client.get_instrument.return_value = mock_instrument("NQ-123", 0.25)

    # Mock responses for entry, stop, and target orders
    mock_async_client._make_request.side_effect = [
        {"orderId": 12356, "success": True, "errorCode": 0, "errorMessage": None},
        {"orderId": 12357, "success": True, "errorCode": 0, "errorMessage": None},
        {"orderId": 12358, "success": True, "errorCode": 0, "errorMessage": None},
    ]

    # Place bracket order with offsets
    response = await order_manager.place_bracket_order(
        "NQ",
        side=0,  # Buy
        size=1,
        entry_type=2,  # Limit
        entry_price=15000.0,
        stop_loss_offset=10.0,  # 10 points below entry
        take_profit_offset=20.0,  # 20 points above entry
    )

    assert response is not None

    # Verify stop and target calculations
    # For a buy order:
    # Stop = entry - offset = 15000 - 10 = 14990
    # Target = entry + offset = 15000 + 20 = 15020

    # Check the actual API calls
    calls = mock_async_client._make_request.call_args_list

    # Entry order
    assert calls[0][1]["data"]["price"] == 15000.0

    # Stop order (second call)
    assert calls[1][1]["data"]["stopPrice"] == 14990.0
    assert calls[1][1]["data"]["side"] == 1  # Sell stop

    # Target order (third call)
    assert calls[2][1]["data"]["price"] == 15020.0
    assert calls[2][1]["data"]["side"] == 1  # Sell limit


@pytest.mark.asyncio
async def test_order_not_found_error(order_manager, mock_async_client):
    """Test handling of order not found errors."""
    mock_async_client.get_instrument.return_value = None

    with pytest.raises(ProjectXOrderError, match="Cannot resolve contract"):
        await order_manager.place_market_order("INVALID", side=0, size=1)


@pytest.mark.asyncio
async def test_concurrent_order_placement(order_manager, mock_async_client):
    """Test concurrent order placement with proper locking."""
    mock_async_client.get_instrument.return_value = mock_instrument("MGC-123", 0.1)

    # Simply use a list of responses - AsyncMock handles async automatically
    mock_async_client._make_request.side_effect = [
        {"orderId": 12360, "success": True, "errorCode": 0, "errorMessage": None},
        {"orderId": 12361, "success": True, "errorCode": 0, "errorMessage": None},
        {"orderId": 12362, "success": True, "errorCode": 0, "errorMessage": None},
    ]

    # Place multiple orders concurrently
    tasks = [
        order_manager.place_market_order("MGC", side=0, size=1),
        order_manager.place_market_order("MGC", side=1, size=1),
        order_manager.place_limit_order("MGC", side=0, size=1, price=2045.0),
    ]

    responses = await asyncio.gather(*tasks)

    assert len(responses) == 3
    assert all(r is not None for r in responses)
    assert order_manager.stats["orders_placed"] == 3

    # Verify order IDs are unique
    order_ids = [r.orderId for r in responses]
    assert len(set(order_ids)) == 3  # All unique
