from unittest.mock import AsyncMock

import pytest

from project_x_py.event_bus import EventBus
from project_x_py.models import Position
from project_x_py.position_manager.core import PositionManager


@pytest.fixture
async def position_manager(initialized_client, mock_positions_data):
    """Fixture for PositionManager with mocked ProjectX client and open positions."""
    # Convert mock_positions_data dicts to Position objects
    positions = [Position(**data) for data in mock_positions_data]

    # Patch search_open_positions to AsyncMock returning Position objects
    initialized_client.search_open_positions = AsyncMock(return_value=positions)
    # Optionally patch other APIs as needed for isolation

    # Create EventBus for the test
    event_bus = EventBus()

    pm = PositionManager(initialized_client, event_bus)
    return pm


@pytest.fixture
def populate_prices():
    """Optional fixture to provide a price dict for positions."""
    return {
        "MGC": 1910.0,
        "MNQ": 14950.0,
    }
