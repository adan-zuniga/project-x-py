"""Tests for AsyncProjectX client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from project_x_py import (
    AsyncProjectX,
    ProjectXConfig,
    ProjectXConnectionError,
)
from project_x_py.async_client import AsyncRateLimiter


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables."""
    monkeypatch.setenv("PROJECT_X_API_KEY", "test_api_key")
    monkeypatch.setenv("PROJECT_X_USERNAME", "test_username")


@pytest.mark.asyncio
async def test_async_client_creation():
    """Test async client can be created."""
    client = AsyncProjectX(
        username="test_user",
        api_key="test_key",
    )
    assert client.username == "test_user"
    assert client.api_key == "test_key"
    assert client.account_name is None
    assert isinstance(client.config, ProjectXConfig)


@pytest.mark.asyncio
async def test_async_client_from_env(mock_env_vars):
    """Test creating async client from environment variables."""
    async with AsyncProjectX.from_env() as client:
        assert client.username == "test_username"
        assert client.api_key == "test_api_key"
        assert client._client is not None  # Client should be initialized


@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async client works as context manager."""
    client = AsyncProjectX(username="test", api_key="key")

    # Client should not be initialized yet
    assert client._client is None

    async with client:
        # Client should be initialized
        assert client._client is not None
        assert isinstance(client._client, httpx.AsyncClient)

    # Client should be cleaned up
    assert client._client is None


@pytest.mark.asyncio
async def test_http2_support():
    """Test that HTTP/2 is enabled."""
    client = AsyncProjectX(username="test", api_key="key")

    async with client:
        # Check HTTP/2 is enabled
        assert client._client._transport._pool._http2 is True


@pytest.mark.asyncio
async def test_authentication_flow():
    """Test authentication flow with mocked responses."""
    client = AsyncProjectX(username="test", api_key="key")

    # Mock responses
    mock_login_response = {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZXhwIjoxNzA0MDY3MjAwfQ.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ"
    }

    mock_accounts_response = [
        {
            "id": "acc1",
            "name": "Test Account",
            "balance": 10000.0,
            "canTrade": True,
            "isVisible": True,
            "simulated": True,
        }
    ]

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = [mock_login_response, mock_accounts_response]

        async with client:
            await client.authenticate()

            assert client._authenticated is True
            assert client.session_token == mock_login_response["access_token"]
            assert client.account_info is not None
            assert client.account_info.name == "Test Account"

            # Verify calls
            assert mock_request.call_count == 2
            mock_request.assert_any_call(
                "POST", "/auth/login", data={"username": "test", "password": "key"}
            )
            mock_request.assert_any_call("GET", "/accounts")


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test that async client can handle concurrent requests."""
    client = AsyncProjectX(username="test", api_key="key")

    # Mock responses
    positions_response = [
        {
            "id": 1,
            "accountId": 123,
            "contractId": "NQZ5",
            "creationTimestamp": "2024-01-01T00:00:00Z",
            "type": 1,
            "size": 1,
            "averagePrice": 100.0,
        }
    ]

    instrument_response = [
        {
            "id": "NQ-123",
            "name": "NQ",
            "description": "Nasdaq 100 Mini",
            "tickSize": 0.25,
            "tickValue": 5.0,
            "activeContract": True,
        }
    ]

    async def mock_make_request(method, endpoint, **kwargs):
        await asyncio.sleep(0.1)  # Simulate network delay
        if "positions" in endpoint:
            return positions_response
        elif "instruments" in endpoint:
            return instrument_response
        return {}

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = mock_make_request

        # Mock authentication method entirely
        with patch.object(
            client, "_ensure_authenticated", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.return_value = None
            # Set account info for position calls
            client.account_info = MagicMock(id="test_account_id")

            async with client:
                # Run multiple requests concurrently
                results = await asyncio.gather(
                    client.get_positions(),
                    client.get_instrument("NQ"),
                    client.get_positions(),
                )

                assert len(results) == 3
                assert len(results[0]) == 1  # First positions call
                assert results[1].name == "NQ"  # Instrument call
                assert len(results[2]) == 1  # Second positions call


@pytest.mark.asyncio
async def test_cache_functionality():
    """Test that caching works for instruments."""
    client = AsyncProjectX(username="test", api_key="key")

    instrument_response = [
        {
            "id": "NQ-123",
            "name": "NQ",
            "description": "Nasdaq 100 Mini",
            "tickSize": 0.25,
            "tickValue": 5.0,
            "activeContract": True,
        }
    ]

    call_count = 0

    async def mock_make_request(method, endpoint, **kwargs):
        nonlocal call_count
        call_count += 1
        return instrument_response

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = mock_make_request

        # Mock authentication method entirely
        with patch.object(
            client, "_ensure_authenticated", new_callable=AsyncMock
        ) as mock_auth:
            mock_auth.return_value = None

            async with client:
                # First call should hit API
                inst1 = await client.get_instrument("NQ")
                assert call_count == 1
                assert client.cache_hit_count == 0

                # Second call should hit cache
                inst2 = await client.get_instrument("NQ")
                assert call_count == 1  # No additional API call
                assert client.cache_hit_count == 1

                # Results should be the same
                assert inst1.name == inst2.name


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling and retries."""
    client = AsyncProjectX(username="test", api_key="key")

    async with client:
        # Test connection error with retries
        with patch.object(client._client, "request") as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(ProjectXConnectionError) as exc_info:
                await client._make_request("GET", "/test")

            assert "Failed to connect" in str(exc_info.value)
            # Should have retried based on config
            assert mock_request.call_count == client.config.retry_attempts + 1


@pytest.mark.asyncio
async def test_health_status():
    """Test health status reporting."""
    client = AsyncProjectX(username="test", api_key="key")
    client.account_info = MagicMock()
    client.account_info.name = "Test Account"

    # Mock authentication method entirely
    with patch.object(
        client, "_ensure_authenticated", new_callable=AsyncMock
    ) as mock_auth:
        mock_auth.return_value = None

        async with client:
            # Set authenticated flag
            client._authenticated = True
            # Make some API calls to populate stats
            client.api_call_count = 10
            client.cache_hit_count = 3

            status = await client.get_health_status()

            assert status["authenticated"] is True
            assert status["account"] == "Test Account"
            assert status["api_calls"] == 10
            assert status["cache_hits"] == 3
            assert status["cache_hit_rate"] == 0.3


@pytest.mark.asyncio
async def test_list_accounts():
    """Test listing accounts."""
    client = AsyncProjectX(username="test", api_key="key")

    mock_accounts = [
        {
            "id": 1,
            "name": "Account 1",
            "balance": 10000.0,
            "canTrade": True,
            "isVisible": True,
            "simulated": True,
        },
        {
            "id": 2,
            "name": "Account 2",
            "balance": 20000.0,
            "canTrade": True,
            "isVisible": True,
            "simulated": False,
        },
    ]

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_accounts

        with patch.object(client, "_ensure_authenticated", new_callable=AsyncMock):
            async with client:
                accounts = await client.list_accounts()

                assert len(accounts) == 2
                assert accounts[0].name == "Account 1"
                assert accounts[0].balance == 10000.0
                assert accounts[1].name == "Account 2"
                assert accounts[1].balance == 20000.0


@pytest.mark.asyncio
async def test_search_instruments():
    """Test searching for instruments."""
    client = AsyncProjectX(username="test", api_key="key")

    mock_instruments = [
        {
            "id": "GC1",
            "name": "GC",
            "description": "Gold Futures",
            "tickSize": 0.1,
            "tickValue": 10.0,
            "activeContract": True,
        },
        {
            "id": "GC2",
            "name": "GC",
            "description": "Gold Futures",
            "tickSize": 0.1,
            "tickValue": 10.0,
            "activeContract": False,
        },
    ]

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_instruments

        with patch.object(client, "_ensure_authenticated", new_callable=AsyncMock):
            async with client:
                # Test basic search
                instruments = await client.search_instruments("gold")
                assert len(instruments) == 2

                # Test live filter
                await client.search_instruments("gold", live=True)
                mock_request.assert_called_with(
                    "GET",
                    "/instruments/search",
                    params={"query": "gold", "live": "true"},
                )


@pytest.mark.asyncio
async def test_get_bars():
    """Test getting market data bars."""
    client = AsyncProjectX(username="test", api_key="key")
    client.account_info = MagicMock()
    client.account_info.id = 123

    mock_bars = [
        {
            "timestamp": "2024-01-01T00:00:00.000Z",
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1000,
        },
        {
            "timestamp": "2024-01-01T00:05:00.000Z",
            "open": 100.5,
            "high": 101.5,
            "low": 100.0,
            "close": 101.0,
            "volume": 1500,
        },
    ]

    mock_instrument = MagicMock()
    mock_instrument.id = "NQ-123"

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_bars

        with patch.object(
            client, "get_instrument", new_callable=AsyncMock
        ) as mock_get_inst:
            mock_get_inst.return_value = mock_instrument

            with patch.object(client, "_ensure_authenticated", new_callable=AsyncMock):
                async with client:
                    data = await client.get_bars("NQ", days=1, interval=5)

                    assert len(data) == 2
                    assert data["open"][0] == 100.0
                    assert data["close"][1] == 101.0

                    # Check caching
                    data2 = await client.get_bars("NQ", days=1, interval=5)
                    assert client.cache_hit_count == 1  # Should hit cache


@pytest.mark.asyncio
async def test_search_trades():
    """Test searching trade history."""
    client = AsyncProjectX(username="test", api_key="key")
    client.account_info = MagicMock()
    client.account_info.id = 123

    mock_trades = [
        {
            "id": 1,
            "accountId": 123,
            "contractId": "NQ-123",
            "creationTimestamp": "2024-01-01T10:00:00Z",
            "price": 15000.0,
            "profitAndLoss": None,
            "fees": 2.50,
            "side": 0,
            "size": 2,
            "voided": False,
            "orderId": 100,
        },
        {
            "id": 2,
            "accountId": 123,
            "contractId": "ES-456",
            "creationTimestamp": "2024-01-01T11:00:00Z",
            "price": 4500.0,
            "profitAndLoss": 150.0,
            "fees": 2.50,
            "side": 1,
            "size": 1,
            "voided": False,
            "orderId": 101,
        },
    ]

    with patch.object(client, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_trades

        with patch.object(client, "_ensure_authenticated", new_callable=AsyncMock):
            async with client:
                trades = await client.search_trades()

                assert len(trades) == 2
                assert trades[0].contractId == "NQ-123"
                assert trades[0].size == 2
                assert trades[0].side == 0  # Buy
                assert trades[1].size == 1
                assert trades[1].side == 1  # Sell


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting functionality."""
    import time

    client = AsyncProjectX(username="test", api_key="key")
    # Set aggressive rate limit for testing
    client.rate_limiter = AsyncRateLimiter(max_requests=2, window_seconds=1)

    async with client:
        with patch.object(
            client._client, "request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = AsyncMock(status_code=200, json=dict)

            start = time.time()

            # Make 3 requests quickly - should trigger rate limit
            await asyncio.gather(
                client._make_request("GET", "/test1"),
                client._make_request("GET", "/test2"),
                client._make_request("GET", "/test3"),
            )

            elapsed = time.time() - start
            # Should have waited at least 1 second for the third request
            assert elapsed >= 1.0
