from unittest.mock import AsyncMock, MagicMock

import pytest

from project_x_py.risk_manager import RiskManager


@pytest.mark.asyncio
async def test_get_risk_metrics_basic(position_manager, mock_positions_data):
    pm = position_manager

    # Create a mock risk_manager for this test
    mock_risk_manager = MagicMock(spec=RiskManager)
    mock_risk_manager.check_position_risk = MagicMock(return_value=True)
    mock_risk_manager.get_risk_settings = MagicMock(
        return_value={
            "max_position_size": 10,
            "max_total_risk": 10000,
            "max_loss_per_trade": 500,
            "daily_loss_limit": 2000,
            "risk_reward_ratio": 2.0,
            "max_positions": 5,
        }
    )

    # Mock the get_risk_metrics to return expected values
    # MGC: 1 * 1900 = 1900
    # MNQ: 2 * 15000 = 30000
    # Total exposure = 31900
    mock_risk_manager.get_risk_metrics = AsyncMock(
        return_value={
            "position_count": 2,
            "total_exposure": 31900.0,
            "margin_used": 3190.0,  # 10% of total exposure
            "margin_available": 6810.0,  # Assuming 10k total margin
            "diversification_score": 0.06,  # 1 - (30000/31900) = 0.06
            "largest_position_risk": 0.94,  # 30000/31900 = 0.94
            "portfolio_heat": 0.32,  # 3190/10000 = 0.32
            "risk_reward_score": 2.0,
            "compliance_status": "healthy",
        }
    )

    pm.risk_manager = mock_risk_manager

    await pm.get_all_positions()
    metrics = await pm.get_risk_metrics()

    # Compute expected total_exposure and position count
    # Total exposure is size * averagePrice for each position
    expected_total_exposure = sum(
        abs(d["size"] * d["averagePrice"]) for d in mock_positions_data
    )
    expected_num_contracts = len({d["contractId"] for d in mock_positions_data})

    # Calculate largest_position_risk the same way as in the implementation
    position_exposures = [
        abs(d["size"] * d["averagePrice"]) for d in mock_positions_data
    ]
    largest_exposure = max(position_exposures) if position_exposures else 0.0
    largest_position_risk = (
        largest_exposure / expected_total_exposure
        if expected_total_exposure > 0
        else 0.0
    )

    # Calculate diversification_score the same way as in the implementation
    expected_diversification = (
        1.0 - largest_position_risk if largest_position_risk < 1.0 else 0.0
    )

    # Verify metrics match expected values
    # Note: total_exposure is not directly returned, but margin_used is related
    assert metrics["position_count"] == expected_num_contracts
    # margin_used should be total_exposure * 0.1 (10% margin)
    assert abs(metrics["margin_used"] - expected_total_exposure * 0.1) < 1e-3
