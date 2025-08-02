"""
Comprehensive async tests for utility functions.

Tests both sync and async utility functions to ensure compatibility.
"""

import asyncio
from datetime import datetime

import polars as pl
import pytest

from project_x_py.utils import (
    calculate_position_value,
    extract_symbol_from_contract_id,
    format_price,
    format_volume,
    get_polars_last_value,
    round_to_tick_size,
    validate_contract_id,
)

# Test async rate limiter if it exists
try:
    from project_x_py.utils import RateLimiter

    HAS_ASYNC_RATE_LIMITER = True
except ImportError:
    HAS_ASYNC_RATE_LIMITER = False


class TestAsyncUtilityFunctions:
    """Test cases for utility functions in async context."""

    @pytest.mark.asyncio
    async def test_async_utility_computation(self):
        """Test that utility functions can be computed in async context."""
        # Create test data
        data = pl.DataFrame(
            {
                "close": [
                    100.0,
                    101.0,
                    102.0,
                    103.0,
                    104.0,
                    105.0,
                    106.0,
                    107.0,
                    108.0,
                    109.0,
                ],
                "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
            }
        )

        # Test that we can compute utilities concurrently
        async def compute_utility_async(func, *args, **kwargs):
            """Wrapper to compute utility function in executor for async context."""
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, func, *args, **kwargs)

        # Run multiple utility functions concurrently
        results = await asyncio.gather(
            compute_utility_async(get_polars_last_value, data, "close"),
            compute_utility_async(format_price, 123.456, 2),
            compute_utility_async(round_to_tick_size, 100.123, 0.01),
            compute_utility_async(calculate_position_value, 10, 100.0, 5.0, 0.01),
        )

        last_close, formatted_price, rounded_price, position_value = results

        # Verify all computations succeeded
        assert last_close == 109.0
        assert formatted_price == "123.46"
        assert rounded_price == 100.12
        assert position_value == 5000.0  # 10 contracts * 100.0 price * 5.0 tick_value

    @pytest.mark.asyncio
    async def test_concurrent_contract_validation(self):
        """Test concurrent contract validation."""
        contracts = [
            "CON.F.US.MGC.M25",
            "CON.F.US.MNQ.H25",
            "invalid_contract",
            "CON.F.US.MES.U25",
        ]

        # Validate contracts concurrently
        async def validate_async(contract):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, validate_contract_id, contract)

        results = await asyncio.gather(
            *[validate_async(contract) for contract in contracts]
        )

        # Verify results
        assert results[0] is True  # Valid MGC contract
        assert results[1] is True  # Valid MNQ contract
        assert results[2] is False  # Invalid contract
        assert results[3] is True  # Valid MES contract

    @pytest.mark.asyncio
    async def test_concurrent_symbol_extraction(self):
        """Test concurrent symbol extraction from contracts."""
        contracts = [
            "CON.F.US.MGC.M25",
            "CON.F.US.MNQ.H25",
            "CON.F.US.MES.U25",
        ]

        async def extract_symbol_async(contract):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, extract_symbol_from_contract_id, contract
            )

        symbols = await asyncio.gather(
            *[extract_symbol_async(contract) for contract in contracts]
        )

        # Verify results
        assert symbols[0] == "MGC"
        assert symbols[1] == "MNQ"
        assert symbols[2] == "MES"


@pytest.mark.skipif(not HAS_ASYNC_RATE_LIMITER, reason="AsyncRateLimiter not available")
class TestAsyncRateLimiter:
    """Test cases for AsyncRateLimiter."""

    @pytest.mark.asyncio
    async def test_async_rate_limiter_basic(self):
        """Test basic AsyncRateLimiter functionality."""
        limiter = RateLimiter(max_requests=3, window_seconds=2)

        request_count = 0

        async def make_request():
            nonlocal request_count
            await limiter.acquire()
            request_count += 1
            return request_count

        # Make 3 requests (should not be rate limited)
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(
            make_request(),
            make_request(),
            make_request(),
        )
        end_time = asyncio.get_event_loop().time()

        # Should have 3 results and execute quickly
        assert len(results) == 3
        assert request_count == 3
        assert end_time - start_time < 1.0  # Should be fast

    @pytest.mark.asyncio
    async def test_async_rate_limiter_with_delay(self):
        """Test AsyncRateLimiter with rate limiting."""
        limiter = RateLimiter(requests_per_minute=2)

        request_times = []

        async def make_request():
            await limiter.acquire()
            request_times.append(asyncio.get_event_loop().time())

        # Make 4 requests (should be rate limited)
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(
            make_request(),
            make_request(),
            make_request(),
        )
        end_time = asyncio.get_event_loop().time()

        # Should take some time due to rate limiting
        assert len(request_times) == 3
        assert end_time - start_time >= 0.5  # Should have some delay


class TestAsyncUtilityCompatibility:
    """Test compatibility of utilities in async contexts."""

    def test_sync_utils_still_work(self):
        """Test that synchronous utilities still work normally."""
        # Test basic price formatting
        formatted = format_price(123.456, 2)
        assert formatted == "123.46"

        # Test contract validation
        assert validate_contract_id("CON.F.US.MGC.M25") is True
        assert validate_contract_id("invalid") is False

        # Test symbol extraction
        symbol = extract_symbol_from_contract_id("CON.F.US.MGC.M25")
        assert symbol == "MGC"

    @pytest.mark.asyncio
    async def test_sync_utils_in_async_context(self):
        """Test that sync utilities work correctly in async context."""
        # These should work directly in async functions
        rounded = round_to_tick_size(200.456, 0.25)
        assert rounded == 200.5

        formatted = format_price(123.456, 2)
        assert formatted == "123.46"

        symbol = extract_symbol_from_contract_id("CON.F.US.MGC.M25")
        assert symbol == "MGC"

    @pytest.mark.asyncio
    async def test_utility_functions_thread_safety(self):
        """Test that utility functions are thread-safe in async context."""

        async def worker(price_base):
            """Worker that does price calculations."""
            results = []
            for i in range(5):
                price = price_base + i * 0.1
                rounded = round_to_tick_size(price, 0.01)
                formatted = format_price(rounded, 2)
                results.append((rounded, formatted))
                await asyncio.sleep(0.001)  # Small async delay
            return results

        # Run multiple workers concurrently
        results = await asyncio.gather(
            worker(100.0),
            worker(200.0),
            worker(300.0),
        )

        # Verify all workers completed successfully
        assert len(results) == 3
        assert all(len(worker_results) == 5 for worker_results in results)

    @pytest.mark.asyncio
    async def test_error_handling_in_async_utils(self):
        """Test error handling when using utilities in async context."""

        async def safe_utility_call(func, *args, **kwargs):
            """Safely call utility function with error handling."""
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return f"Error: {e!s}"

        # Test with valid and invalid inputs
        results = await asyncio.gather(
            safe_utility_call(round_to_tick_size, 100.0, 0.01),
            safe_utility_call(round_to_tick_size, "invalid", 0.01),
            safe_utility_call(validate_contract_id, "CON.F.US.MGC.M25"),
            safe_utility_call(validate_contract_id, None),
        )

        # Verify error handling
        assert results[0] == 100.0  # Valid calculation
        assert "Error:" in str(results[1])  # Invalid input handled
        assert results[2] is True  # Valid contract
        assert results[3] is False or "Error:" in str(results[3])  # Invalid contract


class TestAsyncDataProcessing:
    """Test async data processing patterns with utilities."""

    @pytest.mark.asyncio
    async def test_async_dataframe_processing(self):
        """Test processing DataFrames in async context."""
        # Create test DataFrame
        data = pl.DataFrame(
            {
                "timestamp": [datetime.now() for _ in range(5)],
                "close": [100.0 + i for i in range(5)],
                "volume": [1000 + i * 100 for i in range(5)],
            }
        )

        # Process data asynchronously
        async def process_data():
            # Get last values
            last_close = get_polars_last_value(data, "close")
            last_volume = get_polars_last_value(data, "volume")

            # Format values
            formatted_close = format_price(last_close, 2)
            formatted_volume = format_volume(int(last_volume))

            return {
                "last_close": last_close,
                "last_volume": last_volume,
                "formatted_close": formatted_close,
                "formatted_volume": formatted_volume,
            }

        result = await process_data()

        # Verify processing
        assert result["last_close"] == 104.0
        assert result["last_volume"] == 1400
        assert result["formatted_close"] == "104.00"
        assert result["formatted_volume"] is not None

    @pytest.mark.asyncio
    async def test_batch_price_processing(self):
        """Test batch processing of price data with utilities."""
        # Create batch of price data
        price_data = [
            {"price": 100.123, "tick_size": 0.01, "decimals": 2},
            {"price": 200.456, "tick_size": 0.25, "decimals": 2},
            {"price": 300.789, "tick_size": 0.1, "decimals": 1},
        ]

        async def process_batch(batch):
            """Process batch of price data."""
            tasks = []

            for item in batch:

                async def process_item(data):
                    # Simulate async processing
                    await asyncio.sleep(0.001)
                    rounded = round_to_tick_size(data["price"], data["tick_size"])
                    formatted = format_price(rounded, data["decimals"])
                    return {"rounded": rounded, "formatted": formatted}

                tasks.append(process_item(item))

            return await asyncio.gather(*tasks)

        # Process batch
        processed_prices = await process_batch(price_data)

        # Verify results
        assert len(processed_prices) == 3
        assert processed_prices[0]["rounded"] == 100.12
        assert processed_prices[0]["formatted"] == "100.12"
        assert processed_prices[1]["rounded"] == 200.5
        assert processed_prices[2]["rounded"] == 300.8
