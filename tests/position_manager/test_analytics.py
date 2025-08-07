import pytest


@pytest.mark.asyncio
async def test_calculate_position_pnl_long_short(position_manager, mock_positions_data):
    pm = position_manager
    # Long position: current_price > average_price
    long_pos = next(p for p in await pm.get_all_positions() if p.type == 1)
    pnl_data = await pm.calculate_position_pnl(long_pos, current_price=1910.0)
    assert pnl_data["unrealized_pnl"] > 0

    # Short position: current_price < average_price
    short_pos = next(p for p in await pm.get_all_positions() if p.type == 2)
    pnl_data = await pm.calculate_position_pnl(short_pos, current_price=14950.0)
    assert pnl_data["unrealized_pnl"] > 0  # Short: average 15000 > 14950 = profit


@pytest.mark.asyncio
async def test_calculate_position_pnl_with_point_value(
    position_manager, mock_positions_data
):
    pm = position_manager
    long_pos = next(p for p in await pm.get_all_positions() if p.type == 1)
    # Use point_value scaling
    pnl_data = await pm.calculate_position_pnl(
        long_pos, current_price=1910.0, point_value=2.0
    )
    # Should be double the default
    base_data = await pm.calculate_position_pnl(long_pos, current_price=1910.0)
    assert abs(pnl_data["unrealized_pnl"] - base_data["unrealized_pnl"] * 2.0) < 1e-6


@pytest.mark.asyncio
async def test_calculate_portfolio_pnl(position_manager, populate_prices):
    pm = position_manager
    await pm.get_all_positions()
    prices = populate_prices
    portfolio_data = await pm.calculate_portfolio_pnl(prices)
    # MGC: long, size=1, avg=1900, price=1910 => +10;
    # MNQ: short, size=2, avg=15000, price=14950 => (15000-14950)*2=+100
    assert abs(portfolio_data["total_pnl"] - 110.0) < 1e-3
    assert portfolio_data["total_trades"] == 2
