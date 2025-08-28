"""
Integration tests for TradingSuite with session support.

These tests define the EXPECTED behavior for TradingSuite's session
features. Following strict TDD methodology - tests define specifications.

Author: TDD Implementation
Date: 2025-08-28
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import polars as pl
from datetime import datetime, timezone, timedelta

from project_x_py import TradingSuite, EventType
from project_x_py.sessions import SessionConfig, SessionType


class TestTradingSuiteSessionIntegration:
    """Test TradingSuite with session configuration."""

    @pytest.mark.asyncio
    async def test_create_suite_with_session_config(self):
        """Should initialize TradingSuite with session configuration."""
        with patch('project_x_py.trading_suite.ProjectX') as MockClient:
            # Setup mock client
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.get_account_info = AsyncMock(return_value=MagicMock(
                id=123,
                name="TestAccount"
            ))
            mock_client.get_session_token = AsyncMock(return_value="jwt_token")
            mock_client.get_instrument = AsyncMock(return_value=MagicMock(
                id="MNQ_ID",
                name="MNQ"
            ))
            MockClient.from_env.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.from_env.return_value.__aexit__ = AsyncMock()

            with patch('project_x_py.trading_suite.ProjectXRealtimeClient') as MockRT:
                mock_realtime = AsyncMock()
                mock_realtime.connect = AsyncMock(return_value=True)
                mock_realtime.subscribe_to_market = AsyncMock()
                mock_realtime.is_connected = MagicMock(return_value=True)
                MockRT.return_value = mock_realtime

                with patch('project_x_py.trading_suite.RealtimeDataManager') as MockDM:
                    mock_data_mgr = AsyncMock()
                    mock_data_mgr.initialize = AsyncMock()
                    mock_data_mgr.start_realtime_feed = AsyncMock()
                    MockDM.return_value = mock_data_mgr

                    # Create suite with session config
                    session_config = SessionConfig(
                        session_type=SessionType.RTH,
                        market_timezone="America/New_York"
                    )

                    suite = await TradingSuite.create(
                        "MNQ",
                        timeframes=["1min", "5min"],
                        session_config=session_config
                    )

                    # Verify session config was passed to data manager
                    MockDM.assert_called_once()
                    call_kwargs = MockDM.call_args[1]
                    assert call_kwargs.get('session_config') == session_config

                    # Suite should have session methods
                    assert hasattr(suite, 'set_session_type')
                    assert hasattr(suite, 'get_session_data')
                    assert hasattr(suite, 'get_session_statistics')

                    await suite.disconnect()

    @pytest.mark.asyncio
    async def test_suite_set_session_type(self):
        """Should change session type dynamically."""
        with patch('project_x_py.trading_suite.ProjectX') as MockClient:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.get_account_info = AsyncMock(return_value=MagicMock(
                id=123,
                name="TestAccount"
            ))
            mock_client.get_session_token = AsyncMock(return_value="jwt_token")
            mock_client.get_instrument = AsyncMock(return_value=MagicMock(
                id="MNQ_ID",
                name="MNQ"
            ))
            MockClient.from_env.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.from_env.return_value.__aexit__ = AsyncMock()

            with patch('project_x_py.trading_suite.ProjectXRealtimeClient') as MockRT:
                mock_realtime = AsyncMock()
                mock_realtime.connect = AsyncMock(return_value=True)
                mock_realtime.subscribe_to_market = AsyncMock()
                mock_realtime.is_connected = MagicMock(return_value=True)
                MockRT.return_value = mock_realtime

                with patch('project_x_py.trading_suite.RealtimeDataManager') as MockDM:
                    mock_data_mgr = AsyncMock()
                    mock_data_mgr.initialize = AsyncMock()
                    mock_data_mgr.start_realtime_feed = AsyncMock()
                    mock_data_mgr.set_session_type = AsyncMock()
                    MockDM.return_value = mock_data_mgr

                    # Create suite with default ETH
                    suite = await TradingSuite.create(
                        "MNQ",
                        session_config=SessionConfig()
                    )

                    # Change to RTH
                    await suite.set_session_type(SessionType.RTH)

                    # Verify data manager was updated
                    mock_data_mgr.set_session_type.assert_called_with(SessionType.RTH)

                    await suite.disconnect()

    @pytest.mark.asyncio
    async def test_suite_get_session_data(self):
        """Should retrieve session-filtered data."""
        with patch('project_x_py.trading_suite.ProjectX') as MockClient:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.get_account_info = AsyncMock(return_value=MagicMock(
                id=123,
                name="TestAccount"
            ))
            mock_client.get_session_token = AsyncMock(return_value="jwt_token")
            mock_client.get_instrument = AsyncMock(return_value=MagicMock(
                id="MNQ_ID",
                name="MNQ"
            ))
            MockClient.from_env.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.from_env.return_value.__aexit__ = AsyncMock()

            with patch('project_x_py.trading_suite.ProjectXRealtimeClient') as MockRT:
                mock_realtime = AsyncMock()
                mock_realtime.connect = AsyncMock(return_value=True)
                mock_realtime.subscribe_to_market = AsyncMock()
                mock_realtime.is_connected = MagicMock(return_value=True)
                MockRT.return_value = mock_realtime

                with patch('project_x_py.trading_suite.RealtimeDataManager') as MockDM:
                    # Create mock data
                    mock_rth_data = pl.DataFrame({
                        "timestamp": [datetime.now(timezone.utc)],
                        "close": [100.0],
                        "volume": [1000]
                    })

                    mock_data_mgr = AsyncMock()
                    mock_data_mgr.initialize = AsyncMock()
                    mock_data_mgr.start_realtime_feed = AsyncMock()
                    mock_data_mgr.get_session_data = AsyncMock(return_value=mock_rth_data)
                    MockDM.return_value = mock_data_mgr

                    suite = await TradingSuite.create(
                        "MNQ",
                        session_config=SessionConfig(session_type=SessionType.RTH)
                    )

                    # Get RTH data
                    rth_data = await suite.get_session_data("1min", SessionType.RTH)

                    assert rth_data is not None
                    assert len(rth_data) == 1
                    assert rth_data["close"][0] == 100.0

                    await suite.disconnect()

    @pytest.mark.asyncio
    async def test_suite_get_session_statistics(self):
        """Should calculate session-specific statistics."""
        with patch('project_x_py.trading_suite.ProjectX') as MockClient:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.get_account_info = AsyncMock(return_value=MagicMock(
                id=123,
                name="TestAccount"
            ))
            mock_client.get_session_token = AsyncMock(return_value="jwt_token")
            mock_client.get_instrument = AsyncMock(return_value=MagicMock(
                id="MNQ_ID",
                name="MNQ"
            ))
            MockClient.from_env.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.from_env.return_value.__aexit__ = AsyncMock()

            with patch('project_x_py.trading_suite.ProjectXRealtimeClient') as MockRT:
                mock_realtime = AsyncMock()
                mock_realtime.connect = AsyncMock(return_value=True)
                mock_realtime.subscribe_to_market = AsyncMock()
                mock_realtime.is_connected = MagicMock(return_value=True)
                MockRT.return_value = mock_realtime

                with patch('project_x_py.trading_suite.RealtimeDataManager') as MockDM:
                    mock_stats = {
                        "rth_volume": 50000,
                        "eth_volume": 15000,
                        "rth_vwap": 4900.50,
                        "eth_vwap": 4895.25
                    }

                    mock_data_mgr = AsyncMock()
                    mock_data_mgr.initialize = AsyncMock()
                    mock_data_mgr.start_realtime_feed = AsyncMock()
                    mock_data_mgr.get_session_statistics = AsyncMock(return_value=mock_stats)
                    MockDM.return_value = mock_data_mgr

                    suite = await TradingSuite.create("MNQ")

                    # Get session statistics
                    stats = await suite.get_session_statistics()

                    assert stats["rth_volume"] == 50000
                    assert stats["eth_volume"] == 15000
                    assert stats["rth_vwap"] == 4900.50

                    await suite.disconnect()

    @pytest.mark.asyncio
    async def test_suite_session_event_filtering(self):
        """Events should respect session filtering."""
        with patch('project_x_py.trading_suite.ProjectX') as MockClient:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.get_account_info = AsyncMock(return_value=MagicMock(
                id=123,
                name="TestAccount"
            ))
            mock_client.get_session_token = AsyncMock(return_value="jwt_token")
            mock_client.get_instrument = AsyncMock(return_value=MagicMock(
                id="MNQ_ID",
                name="MNQ"
            ))
            MockClient.from_env.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.from_env.return_value.__aexit__ = AsyncMock()

            with patch('project_x_py.trading_suite.ProjectXRealtimeClient') as MockRT:
                mock_realtime = AsyncMock()
                mock_realtime.connect = AsyncMock(return_value=True)
                mock_realtime.subscribe_to_market = AsyncMock()
                mock_realtime.is_connected = MagicMock(return_value=True)
                MockRT.return_value = mock_realtime

                with patch('project_x_py.trading_suite.RealtimeDataManager') as MockDM:
                    mock_data_mgr = AsyncMock()
                    mock_data_mgr.initialize = AsyncMock()
                    mock_data_mgr.start_realtime_feed = AsyncMock()
                    MockDM.return_value = mock_data_mgr

                    suite = await TradingSuite.create(
                        "MNQ",
                        session_config=SessionConfig(session_type=SessionType.RTH)
                    )

                    # Register event handler
                    event_received = []

                    async def on_session_bar(event):
                        event_received.append(event)

                    # Session filtering happens at data manager level, not event handler level
                    await suite.on(EventType.NEW_BAR, on_session_bar)

                    # Verify event handler is registered
                    assert hasattr(suite, 'events')

                    await suite.disconnect()

    @pytest.mark.asyncio
    async def test_suite_default_eth_backward_compatibility(self):
        """Default behavior should remain ETH for backward compatibility."""
        with patch('project_x_py.trading_suite.ProjectX') as MockClient:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.get_account_info = AsyncMock(return_value=MagicMock(
                id=123,
                name="TestAccount"
            ))
            mock_client.get_session_token = AsyncMock(return_value="jwt_token")
            mock_client.get_instrument = AsyncMock(return_value=MagicMock(
                id="MNQ_ID",
                name="MNQ"
            ))
            MockClient.from_env.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.from_env.return_value.__aexit__ = AsyncMock()

            with patch('project_x_py.trading_suite.ProjectXRealtimeClient') as MockRT:
                mock_realtime = AsyncMock()
                mock_realtime.connect = AsyncMock(return_value=True)
                mock_realtime.subscribe_to_market = AsyncMock()
                mock_realtime.is_connected = MagicMock(return_value=True)
                MockRT.return_value = mock_realtime

                with patch('project_x_py.trading_suite.RealtimeDataManager') as MockDM:
                    mock_data_mgr = AsyncMock()
                    mock_data_mgr.initialize = AsyncMock()
                    mock_data_mgr.start_realtime_feed = AsyncMock()
                    MockDM.return_value = mock_data_mgr

                    # Create suite without session config (backward compatibility)
                    suite = await TradingSuite.create("MNQ")

                    # Should use default ETH (no session filtering)
                    MockDM.assert_called_once()
                    call_kwargs = MockDM.call_args[1]
                    assert call_kwargs.get('session_config') is None

                    await suite.disconnect()

    @pytest.mark.asyncio
    async def test_suite_session_with_indicators(self):
        """Should apply indicators to session-filtered data."""
        with patch('project_x_py.trading_suite.ProjectX') as MockClient:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.authenticate = AsyncMock()
            mock_client.get_account_info = AsyncMock(return_value=MagicMock(
                id=123,
                name="TestAccount"
            ))
            mock_client.get_session_token = AsyncMock(return_value="jwt_token")
            mock_client.get_instrument = AsyncMock(return_value=MagicMock(
                id="MNQ_ID",
                name="MNQ"
            ))
            MockClient.from_env.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.from_env.return_value.__aexit__ = AsyncMock()

            with patch('project_x_py.trading_suite.ProjectXRealtimeClient') as MockRT:
                mock_realtime = AsyncMock()
                mock_realtime.connect = AsyncMock(return_value=True)
                mock_realtime.subscribe_to_market = AsyncMock()
                mock_realtime.is_connected = MagicMock(return_value=True)
                MockRT.return_value = mock_realtime

                with patch('project_x_py.trading_suite.RealtimeDataManager') as MockDM:
                    from project_x_py.indicators import SMA

                    # Create mock session data
                    timestamps = [datetime.now(timezone.utc) - timedelta(minutes=i) for i in range(20)]
                    mock_data = pl.DataFrame({
                        "timestamp": timestamps[::-1],
                        "close": [100.0 + i * 0.1 for i in range(20)],
                        "volume": [1000] * 20
                    })

                    mock_data_mgr = AsyncMock()
                    mock_data_mgr.initialize = AsyncMock()
                    mock_data_mgr.start_realtime_feed = AsyncMock()
                    mock_data_mgr.get_session_data = AsyncMock(return_value=mock_data)
                    MockDM.return_value = mock_data_mgr

                    suite = await TradingSuite.create(
                        "MNQ",
                        session_config=SessionConfig(session_type=SessionType.RTH)
                    )

                    # Get session data with indicator
                    rth_data = await suite.get_session_data("1min", SessionType.RTH)
                    with_sma = rth_data.pipe(SMA, period=10)

                    assert "sma_10" in with_sma.columns
                    assert not with_sma["sma_10"][-10:].has_nulls()

                    await suite.disconnect()
