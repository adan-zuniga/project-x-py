import pytest


@pytest.mark.asyncio
async def test_get_risk_metrics_basic(position_manager, mock_positions_data):
    pm = position_manager
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
