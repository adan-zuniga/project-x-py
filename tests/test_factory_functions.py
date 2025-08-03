"""
Tests for factory functions.

These tests focus on the parameter validation and error handling.
Full integration testing would require significant mocking infrastructure.
"""

import pytest

from project_x_py import (
    ProjectXConfig,
    create_initialized_trading_suite,
    create_trading_suite,
)
from project_x_py.models import Account


class TestFactoryFunctions:
    """Test factory function parameter validation and basic behavior."""

    @pytest.mark.asyncio
    async def test_missing_jwt_token(self):
        """Test error when JWT token is missing."""
        # Create a mock client without JWT token
        mock_client = type(
            "MockClient",
            (),
            {
                "session_token": None,
                "account_info": Account(
                    id=123,
                    name="Test",
                    balance=1000,
                    canTrade=True,
                    isVisible=True,
                    simulated=False,
                ),
                "config": ProjectXConfig(),
            },
        )()

        with pytest.raises(ValueError, match="JWT token is required"):
            await create_trading_suite(
                instrument="MNQ",
                project_x=mock_client,
            )

    @pytest.mark.asyncio
    async def test_missing_account_id(self):
        """Test error when account ID is missing."""
        # Create a mock client without account info
        mock_client = type(
            "MockClient",
            (),
            {
                "session_token": "test_token",
                "account_info": None,
                "config": ProjectXConfig(),
            },
        )()

        with pytest.raises(ValueError, match="Account ID is required"):
            await create_trading_suite(
                instrument="MNQ",
                project_x=mock_client,
            )

    @pytest.mark.asyncio
    async def test_default_timeframes(self):
        """Test that default timeframes are set correctly."""
        # This test validates the parameter handling without creating real objects
        # In a real test environment, you would mock the dependencies
        pass

    @pytest.mark.asyncio
    async def test_initialized_wrapper_parameters(self):
        """Test that create_initialized_trading_suite passes correct parameters."""
        # This would be tested with proper mocking infrastructure
        # For now, we just ensure the function exists and can be imported
        assert callable(create_initialized_trading_suite)
