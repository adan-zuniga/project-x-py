"""Tests for AsyncPositionManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from project_x_py import ProjectX
from project_x_py.models import Position
from project_x_py.position_manager import PositionManager


def mock_position(contract_id, size, avg_price, position_type=1):
    """Helper to create a mock position."""
    return Position(
        id=123,
        accountId=1,
        contractId=contract_id,
        creationTimestamp="2023-01-01T00:00:00.000Z",
        type=position_type,  # 1=Long, 2=Short
        size=size,
        averagePrice=avg_price,
    )


@pytest.fixture
def mock_async_client():
    """Create a mock AsyncProjectX client."""
    client = MagicMock(spec=ProjectX)
    client.account_info = MagicMock()
    client.account_info.id = 123
    client.account_info.balance = 10000.0
    client._make_request = AsyncMock()
    client.search_open_positions = AsyncMock()
    client.get_instrument = AsyncMock()
    client.get_account_info = AsyncMock(return_value=client.account_info)
    client._ensure_authenticated = AsyncMock()
    client._authenticated = True
    return client


@pytest.fixture
def position_manager(mock_async_client):
    """Create an AsyncPositionManager instance."""
    return PositionManager(mock_async_client)


@pytest.mark.asyncio
async def test_position_manager_initialization(mock_async_client):
    """Test AsyncPositionManager initialization."""
    manager = PositionManager(mock_async_client)

    assert manager.project_x == mock_async_client
    assert manager.realtime_client is None
    assert manager._realtime_enabled is False
    assert manager.tracked_positions == {}
    assert isinstance(manager.position_lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_initialize_without_realtime(position_manager, mock_async_client):
    """Test initialization without real-time client."""
    mock_async_client.search_open_positions.return_value = []

    result = await position_manager.initialize()

    assert result is True
    assert position_manager._realtime_enabled is False
    mock_async_client.search_open_positions.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_positions(position_manager, mock_async_client):
    """Test getting all positions."""
    mock_positions = [
        mock_position("MGC", 5, 2045.0),
        mock_position("NQ", 2, 15000.0),
    ]
    mock_async_client.search_open_positions.return_value = mock_positions

    positions = await position_manager.get_all_positions()

    assert len(positions) == 2
    assert positions[0].contractId == "MGC"
    assert positions[1].contractId == "NQ"
    assert position_manager.stats["positions_tracked"] == 2


@pytest.mark.asyncio
async def test_get_position(position_manager, mock_async_client):
    """Test getting a specific position."""
    mock_positions = [
        mock_position("MGC", 5, 2045.0),
        mock_position("NQ", 2, 15000.0),
    ]
    mock_async_client.search_open_positions.return_value = mock_positions

    position = await position_manager.get_position("MGC")

    assert position is not None
    assert position.contractId == "MGC"
    assert position.size == 5


@pytest.mark.asyncio
async def test_calculate_position_pnl_long(position_manager):
    """Test P&L calculation for long position."""
    position = mock_position("MGC", 5, 2045.0, position_type=1)  # Long

    pnl = await position_manager.calculate_position_pnl(position, 2050.0)

    assert pnl["unrealized_pnl"] == 25.0  # (2050 - 2045) * 5
    assert pnl["pnl_per_contract"] == 5.0
    assert pnl["direction"] == "LONG"


@pytest.mark.asyncio
async def test_calculate_position_pnl_short(position_manager):
    """Test P&L calculation for short position."""
    position = mock_position("MGC", 5, 2045.0, position_type=2)  # Short

    pnl = await position_manager.calculate_position_pnl(position, 2040.0)

    assert pnl["unrealized_pnl"] == 25.0  # (2045 - 2040) * 5
    assert pnl["pnl_per_contract"] == 5.0
    assert pnl["direction"] == "SHORT"


@pytest.mark.asyncio
async def test_calculate_portfolio_pnl(position_manager, mock_async_client):
    """Test portfolio P&L calculation."""
    mock_positions = [
        mock_position("MGC", 5, 2045.0, position_type=1),  # Long
        mock_position("NQ", 2, 15000.0, position_type=2),  # Short
    ]
    mock_async_client.search_open_positions.return_value = mock_positions

    current_prices = {"MGC": 2050.0, "NQ": 14950.0}
    pnl = await position_manager.calculate_portfolio_pnl(current_prices)

    assert pnl["total_pnl"] == 125.0  # MGC: +25, NQ: +100
    assert pnl["positions_count"] == 2
    assert pnl["positions_with_prices"] == 2


@pytest.mark.asyncio
async def test_position_size_calculation(position_manager, mock_async_client):
    """Test position size calculation based on risk."""
    mock_instrument = MagicMock()
    mock_instrument.contractMultiplier = 10.0
    mock_async_client.get_instrument.return_value = mock_instrument

    sizing = await position_manager.calculate_position_size(
        "MGC",
        risk_amount=100.0,
        entry_price=2045.0,
        stop_price=2040.0,
        account_balance=10000.0,
    )

    assert sizing["suggested_size"] == 2  # 100 / (5 * 10)
    assert sizing["risk_per_contract"] == 50.0  # 5 points * 10 multiplier
    assert sizing["risk_percentage"] == 1.0  # 100 / 10000 * 100


@pytest.mark.asyncio
async def test_close_position_direct(position_manager, mock_async_client):
    """Test closing a position directly."""
    mock_async_client._make_request.return_value = {
        "success": True,
        "orderId": 12345,
    }

    # Add position to tracked positions
    position_manager.tracked_positions["MGC"] = mock_position("MGC", 5, 2045.0)

    result = await position_manager.close_position_direct("MGC")

    assert result["success"] is True
    assert "MGC" not in position_manager.tracked_positions
    assert position_manager.stats["positions_closed"] == 1

    mock_async_client._make_request.assert_called_once_with(
        "POST",
        "/Position/closeContract",
        data={"accountId": 123, "contractId": "MGC"},
    )


@pytest.mark.asyncio
async def test_partially_close_position(position_manager, mock_async_client):
    """Test partially closing a position."""
    mock_async_client._make_request.return_value = {
        "success": True,
        "orderId": 12346,
    }
    mock_async_client.search_open_positions.return_value = []

    result = await position_manager.partially_close_position("MGC", close_size=3)

    assert result["success"] is True
    assert position_manager.stats["positions_partially_closed"] == 1

    mock_async_client._make_request.assert_called_with(
        "POST",
        "/Position/partialCloseContract",
        data={"accountId": 123, "contractId": "MGC", "closeSize": 3},
    )


@pytest.mark.asyncio
async def test_add_position_alert(position_manager):
    """Test adding position alerts."""
    await position_manager.add_position_alert("MGC", max_loss=-500.0)

    assert "MGC" in position_manager.position_alerts
    assert position_manager.position_alerts["MGC"]["max_loss"] == -500.0
    assert position_manager.position_alerts["MGC"]["triggered"] is False


@pytest.mark.asyncio
async def test_monitoring_start_stop(position_manager):
    """Test starting and stopping position monitoring."""
    await position_manager.start_monitoring(refresh_interval=1)

    assert position_manager._monitoring_active is True
    assert position_manager._monitoring_task is not None

    await position_manager.stop_monitoring()

    assert position_manager._monitoring_active is False
    assert position_manager._monitoring_task is None


@pytest.mark.asyncio
async def test_get_risk_metrics(position_manager, mock_async_client):
    """Test portfolio risk metrics calculation."""
    mock_positions = [
        mock_position("MGC", 5, 2045.0),
        mock_position("NQ", 2, 15000.0),
    ]
    mock_async_client.search_open_positions.return_value = mock_positions

    risk = await position_manager.get_risk_metrics()

    assert risk["position_count"] == 2
    assert risk["total_exposure"] == 40225.0  # (5 * 2045) + (2 * 15000)
    assert risk["largest_position_risk"] == pytest.approx(0.7456, rel=1e-3)


@pytest.mark.asyncio
async def test_process_position_data_closure(position_manager):
    """Test processing position data for closure detection."""
    # Set up a tracked position
    position_manager.tracked_positions["MGC"] = mock_position("MGC", 5, 2045.0)

    # Process closure update (size = 0)
    closure_data = {
        "id": 123,
        "accountId": 1,
        "contractId": "MGC",
        "creationTimestamp": "2023-01-01T00:00:00.000Z",
        "type": 1,  # Still Long, but closed
        "size": 0,  # Closed position
        "averagePrice": 2045.0,
    }

    await position_manager._process_position_data(closure_data)

    assert "MGC" not in position_manager.tracked_positions
    assert position_manager.stats["positions_closed"] == 1


@pytest.mark.asyncio
async def test_validate_position_payload(position_manager):
    """Test position payload validation."""
    valid_payload = {
        "id": 123,
        "accountId": 1,
        "contractId": "MGC",
        "creationTimestamp": "2023-01-01T00:00:00.000Z",
        "type": 1,
        "size": 5,
        "averagePrice": 2045.0,
    }

    assert position_manager._validate_position_payload(valid_payload) is True

    # Missing field
    invalid_payload = valid_payload.copy()
    del invalid_payload["contractId"]
    assert position_manager._validate_position_payload(invalid_payload) is False

    # Invalid type
    invalid_payload = valid_payload.copy()
    invalid_payload["type"] = 5  # Invalid position type
    assert position_manager._validate_position_payload(invalid_payload) is False


@pytest.mark.asyncio
async def test_export_portfolio_report(position_manager, mock_async_client):
    """Test exporting portfolio report."""
    mock_positions = [mock_position("MGC", 5, 2045.0)]
    mock_async_client.search_open_positions.return_value = mock_positions

    report = await position_manager.export_portfolio_report()

    assert "report_timestamp" in report
    assert report["portfolio_summary"]["total_positions"] == 1
    assert "positions" in report
    assert "risk_analysis" in report
    assert "statistics" in report


@pytest.mark.asyncio
async def test_cleanup(position_manager):
    """Test cleanup method."""
    # Add some data
    position_manager.tracked_positions["MGC"] = mock_position("MGC", 5, 2045.0)
    position_manager.position_alerts["MGC"] = {"max_loss": -500.0}

    await position_manager.cleanup()

    assert len(position_manager.tracked_positions) == 0
    assert len(position_manager.position_alerts) == 0
    assert position_manager._monitoring_active is False
