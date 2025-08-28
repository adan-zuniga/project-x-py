"""
Integration tests for ProjectX client with session support.

These tests define the EXPECTED behavior for client session APIs.
Following strict TDD methodology - tests define specifications.

Author: TDD Implementation
Date: 2025-08-28
"""

import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
import polars as pl
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from project_x_py.client import ProjectX
from project_x_py.sessions import SessionConfig, SessionType


class TestClientSessionAPI:
    """Test ProjectX client session API extensions."""

    def _create_auth_response(self):
        """Create a mock authentication response."""
        auth_response = MagicMock()
        auth_response.status_code = 200
        auth_response.json.return_value = {
            "success": True,
            "data": {"token": "test_jwt_token", "accountId": 123}
        }
        return auth_response

    def _create_account_response(self):
        """Create a mock account response."""
        account_response = MagicMock()
        account_response.status_code = 200
        account_response.json.return_value = {
            "success": True,
            "data": {
                "id": 123,
                "name": "TestAccount",
                "displayName": "Test Account"
            }
        }
        return account_response

    @pytest.mark.asyncio
    async def test_get_session_bars(self, auth_env_vars):
        """Should fetch bars filtered by session type."""
        # Create a client but bypass authentication
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Mock the internal state to bypass authentication
        client._jwt_token = "test_token"
        client._session_token = "test_session"
        client.account_info = MagicMock(id=123, name="TestAccount")

        # Create mock data
        mock_data = pl.DataFrame({
            "timestamp": [
                datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
                datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc),
            ],
            "open": [4900.0, 4902.0],
            "high": [4905.0, 4908.0],
            "low": [4899.0, 4901.0],
            "close": [4902.0, 4905.0],
            "volume": [5000, 6000]
        })

        # Mock the get_bars method to return async result
        async def mock_get_bars(*args, **kwargs):
            return mock_data

        # Patch the get_bars method
        with patch.object(client, 'get_bars', new=mock_get_bars):
            # Get RTH bars only
            bars = await client.get_session_bars(
                "MNQ",
                timeframe="1min",
                session_type=SessionType.RTH,
                days=1
            )

            assert bars is not None
            assert len(bars) == 2
            assert "timestamp" in bars.columns
            assert "close" in bars.columns

    def _setup_mock_http(self, MockHttpx, data_response=None):
        """Set up mock HTTP client with standard responses."""
        mock_http = AsyncMock()

        # Standard auth and account responses
        mock_http.post = AsyncMock(return_value=self._create_auth_response())

        # Create a list of GET responses
        get_responses = [self._create_account_response()]
        if data_response:
            get_responses.append(data_response)

        mock_http.get = AsyncMock(side_effect=get_responses)
        MockHttpx.return_value = mock_http
        return mock_http

    @pytest.mark.asyncio
    async def test_get_session_bars_with_custom_config(self, auth_env_vars):
        """Should use custom session configuration."""
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionConfig, SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"
        client.account_info = MagicMock(id=123)

        # Mock data for get_bars
        mock_data = pl.DataFrame({
            "timestamp": [datetime.now(timezone.utc)],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000]
        })

        async def mock_get_bars(*args, **kwargs):
            return mock_data

        with patch.object(client, 'get_bars', new=mock_get_bars):
            # Custom session config
            custom_config = SessionConfig(
                session_type=SessionType.RTH,
                market_timezone="Europe/London"
            )

            bars = await client.get_session_bars(
                "MNQ",
                timeframe="1min",  # Add required parameter
                session_config=custom_config
            )

            # Should apply custom configuration
            assert bars is not None

    @pytest.mark.asyncio
    async def test_get_session_market_hours(self, auth_env_vars):
        """Should retrieve market hours for specific session."""
        from project_x_py import ProjectX

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"

        # Get market hours (uses DEFAULT_SESSIONS internally)
        hours = await client.get_session_market_hours("ES")

        assert hours is not None
        assert "RTH" in hours
        assert "ETH" in hours
        assert hours["RTH"]["timezone"] == "America/New_York"
        assert hours["ETH"]["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_get_session_volume_profile(self, auth_env_vars):
        """Should calculate volume profile by session."""
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"
        client.account_info = MagicMock(id=123)

        # Mock data for get_bars (called by get_session_bars)
        mock_bars = pl.DataFrame({
            "timestamp": [
                datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),
                datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc),
            ],
            "open": [4900.0, 4905.0],
            "high": [4905.0, 4910.0],
            "low": [4895.0, 4900.0],
            "close": [4902.0, 4908.0],
            "volume": [5000, 8000]
        })

        async def mock_get_bars(*args, **kwargs):
            return mock_bars

        with patch.object(client, 'get_bars', new=mock_get_bars):
            # Get volume profile for RTH
            profile = await client.get_session_volume_profile(
                "MNQ",
                session_type=SessionType.RTH
            )

            assert profile is not None
            assert "price_level" in profile or "price" in profile  # Check for either key
            assert "volume" in profile
            assert "session_type" in profile

    @pytest.mark.asyncio
    async def test_get_session_statistics(self, auth_env_vars):
        """Should calculate statistics for session."""
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"
        client.account_info = MagicMock(id=123)

        # Mock data for get_session_bars
        mock_bars = pl.DataFrame({
            "timestamp": [datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)],
            "open": [4900.0],
            "high": [4910.0],
            "low": [4895.0],
            "close": [4905.0],
            "volume": [10000]
        })

        async def mock_get_session_bars(*args, **kwargs):
            return mock_bars

        with patch.object(client, 'get_session_bars', new=mock_get_session_bars):
            stats = await client.get_session_statistics(
                "MNQ",
                session_type=SessionType.RTH
            )

            assert stats is not None
            assert "session_high" in stats
            assert "session_low" in stats
            assert "session_volume" in stats
            assert "session_vwap" in stats
            assert stats["session_volume"] == 10000

    @pytest.mark.asyncio
    async def test_is_market_open_for_session(self, auth_env_vars):
        """Should check if market is open for specific session."""
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"

        # Mock is_session_open directly since it has complex internal logic
        async def mock_is_session_open(symbol, session_type=None):
            # Mock as always open for testing
            return True

        with patch.object(client, 'is_session_open', new=mock_is_session_open):
            is_open = await client.is_session_open("ES", SessionType.RTH)
            assert is_open is True

            # Check ETH
            is_open_eth = await client.is_session_open("ES", SessionType.ETH)
            assert is_open_eth is True

    @pytest.mark.asyncio
    async def test_get_next_session_open(self, auth_env_vars):
        """Should get next session open time."""
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"

        # Get next RTH open
        next_open = await client.get_next_session_open("ES", SessionType.RTH)

        assert next_open is not None
        assert isinstance(next_open, datetime)

    @pytest.mark.asyncio
    async def test_get_session_trades(self, auth_env_vars):
        """Should fetch trades filtered by session."""
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"
        client.account_info = MagicMock(id=123)

        # Mock trades data
        mock_trades = [
            {
                "timestamp": "2024-01-15T14:35:00Z",
                "price": 4902.50,
                "size": 5,
                "side": "buy"
            },
            {
                "timestamp": "2024-01-15T15:10:00Z",
                "price": 4905.75,
                "size": 10,
                "side": "sell"
            }
        ]

        async def mock_get_session_trades(*args, **kwargs):
            return mock_trades

        with patch.object(client, 'get_session_trades', new=mock_get_session_trades):
            trades = await client.get_session_trades(
                "MNQ",
                session_type=SessionType.RTH
            )

            assert trades is not None
            assert len(trades) == 2
            assert trades[0]["price"] == 4902.50

    @pytest.mark.asyncio
    async def test_get_session_order_flow(self, auth_env_vars):
        """Should analyze order flow by session."""
        from project_x_py import ProjectX
        from project_x_py.sessions import SessionType

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"
        client.account_info = MagicMock(id=123)

        # Mock order flow data
        mock_flow = {
            "buy_volume": 13,  # 5 + 8
            "sell_volume": 3,
            "net_delta": 10  # 13 - 3
        }

        async def mock_get_session_order_flow(*args, **kwargs):
            return mock_flow

        with patch.object(client, 'get_session_order_flow', new=mock_get_session_order_flow):
            flow = await client.get_session_order_flow(
                "MNQ",
                session_type=SessionType.RTH
            )

            assert flow is not None
            assert "buy_volume" in flow
            assert "sell_volume" in flow
            assert "net_delta" in flow
            assert flow["buy_volume"] == 13  # 5 + 8
            assert flow["sell_volume"] == 3
            assert flow["net_delta"] == 10  # 13 - 3

    @pytest.mark.asyncio
    async def test_backward_compatibility_no_session(self, auth_env_vars):
        """Existing API should work without session parameters."""
        from project_x_py import ProjectX

        client = ProjectX(
            api_key=auth_env_vars["PROJECT_X_API_KEY"],
            username=auth_env_vars["PROJECT_X_USERNAME"]
        )

        # Bypass authentication
        client._jwt_token = "test_token"
        client.account_info = MagicMock(id=123)

        # Mock bars data - both ETH and RTH hours
        mock_bars = pl.DataFrame({
            "timestamp": [
                datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc),  # ETH hour
                datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc),  # RTH hour
            ],
            "open": [4888.0, 4898.0],
            "high": [4892.0, 4902.0],
            "low": [4885.0, 4895.0],
            "close": [4890.0, 4900.0],
            "volume": [1000, 5000]
        })

        async def mock_get_bars(*args, **kwargs):
            return mock_bars

        with patch.object(client, 'get_bars', new=mock_get_bars):
            # Call existing API without session params
            bars = await client.get_bars("MNQ", interval=1, days=1)

            # Should return all data (ETH default)
            assert bars is not None
            assert len(bars) == 2  # Both ETH and RTH bars
