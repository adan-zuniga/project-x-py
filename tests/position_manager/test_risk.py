import pytest

@pytest.mark.asyncio
async def test_get_risk_metrics_basic(position_manager, mock_positions_data):
    pm = position_manager
    await pm.get_all_positions()
    metrics = await pm.get_risk_metrics()

    # Compute expected total_exposure, num_contracts, diversification_score
    expected_total_exposure = sum(abs(d["size"]) for d in mock_positions_data)
    expected_num_contracts = len(set(d["contractId"] for d in mock_positions_data))
    # Diversification: 0 if only 1 contract, up to 1.0 for max diversity
    expected_diversification = (expected_num_contracts - 1) / (expected_num_contracts or 1)
    assert abs(metrics["total_exposure"] - expected_total_exposure) < 1e-3
    assert metrics["num_contracts"] == expected_num_contracts
    assert abs(metrics["diversification_score"] - expected_diversification) < 1e-3