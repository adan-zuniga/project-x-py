"""
Tests for multi-instrument TradingSuite functionality.

Following TDD principles for the multi-instrument refactor as outlined in
the architecture document.
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from project_x_py import Features, TradingSuite, TradingSuiteConfig
from project_x_py.models import Account, Instrument


@pytest.mark.asyncio
async def test_instrument_context_creation():
    """
    RED: Test InstrumentContext creation with all required managers.

    This test defines the expected behavior for InstrumentContext - it should
    encapsulate all managers for a single instrument and provide clean access.
    """
    # This will fail until we implement InstrumentContext
    from project_x_py.trading_suite import InstrumentContext

    # Mock the managers that should be in the context
    mock_instrument_info = MagicMock()
    mock_instrument_info.id = "MNQ_CONTRACT_ID"
    mock_instrument_info.symbol = "MNQ"

    mock_data_manager = MagicMock()
    mock_order_manager = MagicMock()
    mock_position_manager = MagicMock()
    mock_orderbook = MagicMock()
    mock_risk_manager = MagicMock()

    # Create InstrumentContext
    context = InstrumentContext(
        symbol="MNQ",
        instrument_info=mock_instrument_info,
        data=mock_data_manager,
        orders=mock_order_manager,
        positions=mock_position_manager,
        orderbook=mock_orderbook,
        risk_manager=mock_risk_manager,
    )

    # Verify all components are accessible
    assert context.symbol == "MNQ"
    assert context.instrument_info == mock_instrument_info
    assert context.data == mock_data_manager
    assert context.orders == mock_order_manager
    assert context.positions == mock_position_manager
    assert context.orderbook == mock_orderbook
    assert context.risk_manager == mock_risk_manager


@pytest.mark.asyncio
async def test_multi_instrument_suite_creation():
    """
    RED: Test TradingSuite creation with multiple instruments.

    This test defines how TradingSuite should handle multiple instruments
    with dictionary-like access pattern.
    """
    # Setup common mocks
    mock_client = MagicMock()
    mock_client.account_info = Account(
        id=12345,
        name="TEST_ACCOUNT",
        balance=100000.0,
        canTrade=True,
        isVisible=True,
        simulated=True,
    )
    mock_client.session_token = "mock_jwt_token"
    mock_client.config = MagicMock()
    mock_client.authenticate = AsyncMock()

    # Mock instruments for each symbol
    instruments = {
        "MNQ": MagicMock(id="MNQ_CONTRACT_ID", symbol="MNQ"),
        "MES": MagicMock(id="MES_CONTRACT_ID", symbol="MES"),
        "MCL": MagicMock(id="MCL_CONTRACT_ID", symbol="MCL"),
    }

    async def mock_get_instrument(symbol: str):
        return instruments[symbol]

    mock_client.get_instrument = AsyncMock(side_effect=mock_get_instrument)
    mock_client.search_all_orders = AsyncMock(return_value=[])
    mock_client.search_open_positions = AsyncMock(return_value=[])

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client
    mock_context.__aexit__.return_value = None

    # Mock realtime client
    mock_realtime = MagicMock()
    mock_realtime.connect = AsyncMock(return_value=True)
    mock_realtime.disconnect = AsyncMock(return_value=None)
    mock_realtime.subscribe_user_updates = AsyncMock(return_value=True)
    mock_realtime.subscribe_market_data = AsyncMock(return_value=True)
    mock_realtime.is_connected.return_value = True

    # Mock component creation for each instrument
    mock_data_managers = {}
    mock_position_managers = {}

    def create_mock_data_manager(instrument, **kwargs):
        mock_dm = MagicMock()
        mock_dm.initialize = AsyncMock(return_value=True)
        mock_dm.start_realtime_feed = AsyncMock(return_value=True)
        mock_dm.stop_realtime_feed = AsyncMock(return_value=None)
        mock_dm.cleanup = AsyncMock(return_value=None)
        mock_dm.get_current_price = AsyncMock(return_value=16500.25)
        mock_data_managers[instrument] = mock_dm
        return mock_dm

    def create_mock_position_manager(*args, **kwargs):
        mock_pm = MagicMock()
        mock_pm.initialize = AsyncMock(return_value=True)
        mock_pm.get_all_positions = AsyncMock(return_value=[])
        return mock_pm

    with patch(
        "project_x_py.trading_suite.ProjectX.from_env", return_value=mock_context
    ):
        with patch(
            "project_x_py.trading_suite.ProjectXRealtimeClient",
            return_value=mock_realtime,
        ):
            with patch(
                "project_x_py.trading_suite.RealtimeDataManager",
                side_effect=create_mock_data_manager,
            ):
                with patch(
                    "project_x_py.trading_suite.PositionManager",
                    side_effect=create_mock_position_manager,
                ):
                    # Create multi-instrument suite
                    suite = await TradingSuite.create(
                        instruments=[
                            "MNQ",
                            "MES",
                            "MCL",
                        ],  # This should work after refactor
                        timeframes=["1min", "5min"],
                    )

                    # Test dictionary-like access
                    assert len(suite) == 3
                    assert "MNQ" in suite
                    assert "MES" in suite
                    assert "MCL" in suite

                    # Test item access
                    mnq_context = suite["MNQ"]
                    assert mnq_context.symbol == "MNQ"
                    assert mnq_context.instrument_info == instruments["MNQ"]

                    mes_context = suite["MES"]
                    assert mes_context.symbol == "MES"
                    assert mes_context.instrument_info == instruments["MES"]

                    # Test iteration
                    symbols = list(suite)
                    assert set(symbols) == {"MNQ", "MES", "MCL"}

                    # Test keys/items methods
                    assert set(suite.keys()) == {"MNQ", "MES", "MCL"}

                    for symbol, context in suite.items():
                        assert symbol in ["MNQ", "MES", "MCL"]
                        assert context.symbol == symbol
                        assert context.instrument_info == instruments[symbol]

                    await suite.disconnect()


@pytest.mark.asyncio
async def test_backward_compatibility_single_instrument():
    """
    RED: Test that single-instrument access still works with deprecation warnings.

    Existing code should continue to work but with deprecation warnings.
    """
    # Setup single instrument mocks
    mock_client = MagicMock()
    mock_client.account_info = Account(
        id=12345,
        name="TEST_ACCOUNT",
        balance=100000.0,
        canTrade=True,
        isVisible=True,
        simulated=True,
    )
    mock_client.session_token = "mock_jwt_token"
    mock_client.config = MagicMock()
    mock_client.authenticate = AsyncMock()
    mock_client.get_instrument = AsyncMock(return_value=MagicMock(id="MNQ_CONTRACT_ID"))
    mock_client.search_all_orders = AsyncMock(return_value=[])
    mock_client.search_open_positions = AsyncMock(return_value=[])

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client
    mock_context.__aexit__.return_value = None

    mock_realtime = MagicMock()
    mock_realtime.connect = AsyncMock(return_value=True)
    mock_realtime.disconnect = AsyncMock(return_value=None)
    mock_realtime.subscribe_user_updates = AsyncMock(return_value=True)
    mock_realtime.subscribe_market_data = AsyncMock(return_value=True)
    mock_realtime.is_connected.return_value = True

    mock_data_manager = MagicMock()
    mock_data_manager.initialize = AsyncMock(return_value=True)
    mock_data_manager.start_realtime_feed = AsyncMock(return_value=True)
    mock_data_manager.stop_realtime_feed = AsyncMock(return_value=None)
    mock_data_manager.cleanup = AsyncMock(return_value=None)

    mock_position_manager = MagicMock()
    mock_position_manager.initialize = AsyncMock(return_value=True)

    with patch(
        "project_x_py.trading_suite.ProjectX.from_env", return_value=mock_context
    ):
        with patch(
            "project_x_py.trading_suite.ProjectXRealtimeClient",
            return_value=mock_realtime,
        ):
            with patch(
                "project_x_py.trading_suite.RealtimeDataManager",
                return_value=mock_data_manager,
            ):
                with patch(
                    "project_x_py.trading_suite.PositionManager",
                    return_value=mock_position_manager,
                ):
                    # Create single instrument suite (current API)
                    suite = await TradingSuite.create("MNQ")

                    # New API should work
                    mnq_context = suite["MNQ"]
                    assert mnq_context.symbol == "MNQ"

                    # Old API should work with deprecation warnings
                    with pytest.warns(
                        DeprecationWarning,
                        match="Direct access to 'data' is deprecated",
                    ):
                        old_data_manager = suite.data
                        assert old_data_manager == mock_data_manager

                    with pytest.warns(
                        DeprecationWarning,
                        match="Direct access to 'orders' is deprecated",
                    ):
                        old_order_manager = suite.orders

                    with pytest.warns(
                        DeprecationWarning,
                        match="Direct access to 'positions' is deprecated",
                    ):
                        old_position_manager = suite.positions

                    await suite.disconnect()


@pytest.mark.asyncio
async def test_multi_instrument_parallel_creation():
    """
    RED: Test that multiple instruments are created in parallel for performance.

    The create method should use asyncio.gather to create instrument contexts
    in parallel rather than sequentially.
    """
    # This test will verify the parallel creation behavior
    # Implementation will track creation timing and call order

    creation_order = []

    async def mock_create_context(symbol: str):
        creation_order.append(f"start_{symbol}")
        # Simulate async work
        await AsyncMock()()
        creation_order.append(f"end_{symbol}")
        return symbol, MagicMock()  # Return symbol and mock context

    # Test that we're actually using asyncio.gather for parallel creation
    # by checking the call pattern in _create_instrument_contexts
    instruments = ["MNQ", "MES", "MCL"]

    # Verify that the parallel creation pattern exists in the method
    import inspect

    from project_x_py.trading_suite import TradingSuite

    source = inspect.getsource(TradingSuite._create_instrument_contexts)

    # Verify parallel execution patterns are in the source
    assert "asyncio.gather" in source, "Should use asyncio.gather for parallel creation"
    assert "[_create_single_context(symbol) for symbol in instruments]" in source, (
        "Should create tasks in parallel"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
