import pytest

from project_x_py.position_manager.analytics import AnalyticsMixin

@pytest.mark.asyncio
async def test_calculate_position_pnl_long_short(position_manager, mock_positions_data):
    pm = position_manager
    # Long position: current_price > average_price
    long_pos = [p for p in await pm.get_all_positions() if p.type == 1][0]
    pnl_long = pm.calculate_position_pnl(long_pos, current_price=1910.0)
    assert pnl_long > 0

    # Short position: current_price < average_price
    short_pos = [p for p in await pm.get_all_positions() if p.type == 2][0]
    pnl_short = pm.calculate_position_pnl(short_pos, current_price=14950.0)
    assert pnl_short > 0  # Short: average 15000 > 14950 = profit

@pytest.mark.asyncio
async def test_calculate_position_pnl_with_point_value(position_manager, mock_positions_data):
    pm = position_manager
    long_pos = [p for p in await pm.get_all_positions() if p.type == 1][0]
    # Use point_value scaling
    pnl = pm.calculate_position_pnl(long_pos, current_price=1910.0, point_value=2.0)
    # Should be double the default
    base = pm.calculate_position_pnl(long_pos, current_price=1910.0)
    assert abs(pnl - base * 2.0) < 1e-6

@pytest.mark.asyncio
async def test_calculate_portfolio_pnl(position_manager, populate_prices):
    pm = position_manager
    await pm.get_all_positions()
    prices = populate_prices
    total_pnl, positions_with_prices = pm.calculate_portfolio_pnl(prices)
    # MGC: long, size=1, avg=1900, price=1910 => +10;
    # MNQ: short, size=2, avg=15000, price=14950 => (15000-14950)*2=+100
    assert abs(total_pnl - 110.0) < 1e-3
    assert positions_with_prices == 2