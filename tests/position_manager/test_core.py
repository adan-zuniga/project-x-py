from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_get_all_positions_updates_stats(position_manager, mock_positions_data):
    pm = position_manager
    result = await pm.get_all_positions()
    assert len(result) == len(mock_positions_data)
    assert pm.stats["positions_tracked"] == len(mock_positions_data)
    assert set(pm.tracked_positions.keys()) == {
        d["contractId"] for d in mock_positions_data
    }


@pytest.mark.asyncio
async def test_get_position_cache_vs_api(position_manager):
    pm = position_manager

    # a) Realtime disabled: should call API
    pm._realtime_enabled = False
    with patch.object(
        pm.project_x, "search_open_positions", wraps=pm.project_x.search_open_positions
    ) as mock_search:
        pos = await pm.get_position("MGC")
        assert pos.id
        mock_search.assert_called_once()

    # b) Realtime enabled: should use cache only
    pm._realtime_enabled = True
    # Prepopulate cache
    mgc_pos = await pm.get_position("MGC")
    pm.tracked_positions["MGC"] = mgc_pos
    with patch.object(
        pm.project_x,
        "search_open_positions",
        side_effect=Exception("Should not be called"),
    ):
        pos2 = await pm.get_position("MGC")
        assert pos2 is pm.tracked_positions["MGC"]


@pytest.mark.asyncio
async def test_is_position_open(position_manager):
    pm = position_manager
    await pm.get_all_positions()
    assert await pm.is_position_open("MGC") is True
    assert await pm.is_position_open("UNKNOWN") is False
    # Simulate closed size
    pm.tracked_positions["MGC"].size = 0
    assert await pm.is_position_open("MGC") is False


@pytest.mark.asyncio
async def test_refresh_positions(position_manager):
    pm = position_manager
    prev_stats = dict(pm.stats)
    changed = await pm.refresh_positions()
    assert changed is True
    assert pm.stats["positions_tracked"] == len(pm.tracked_positions)


@pytest.mark.asyncio
async def test_cleanup(position_manager):
    pm = position_manager
    # Prepopulate tracked_positions and position_alerts
    await pm.get_all_positions()
    pm.position_alerts = {"foo": "bar"}
    pm.order_manager = object()
    pm._order_sync_enabled = True

    await pm.cleanup()
    assert pm.tracked_positions == {}
    assert pm.position_alerts == {}
    assert pm.order_manager is None
    assert pm._order_sync_enabled is False
