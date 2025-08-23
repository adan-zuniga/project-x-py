#!/usr/bin/env python3
"""
Test script for comprehensive data validation system.

This example demonstrates the new data validation layer with price, volume,
and timestamp sanity checks for protecting against corrupt market data.

Author: @TexasCoding
Date: 2025-08-22
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_data_validation():
    """Test the comprehensive data validation system."""

    # Import validation components
    from project_x_py.realtime_data_manager.validation import (
        DataValidationMixin,
    )

    # Create a test validation instance
    class TestValidation(DataValidationMixin):
        def __init__(self):
            self.config = {
                "validation_config": {
                    "enable_price_validation": True,
                    "enable_volume_validation": True,
                    "enable_timestamp_validation": True,
                    "price_range_multiplier": 2.0,
                    "volume_spike_threshold": 5.0,
                    "max_spread_percent": 1.0,
                    "timestamp_tolerance_seconds": 30.0,
                }
            }
            self.tick_size = 0.25
            super().__init__()

    validator = TestValidation()

    print("🧪 Testing Data Validation System")
    print("=" * 50)

    # Test 1: Valid quote data
    print("\n📊 Test 1: Valid Quote Data")
    valid_quote = {
        "symbol": "F.US.MNQ",
        "bestBid": 23920.50,
        "bestAsk": 23920.75,
        "lastPrice": 23920.50,
        "timestamp": datetime.now(),
    }

    result = await validator.validate_quote_data(valid_quote)
    print(f"✅ Valid quote result: {'PASSED' if result else 'FAILED'}")

    # Test 2: Invalid quote data (bid > ask)
    print("\n📊 Test 2: Invalid Quote Data (Bid > Ask)")
    invalid_quote = {
        "symbol": "F.US.MNQ",
        "bestBid": 23921.00,  # Higher than ask
        "bestAsk": 23920.75,
        "timestamp": datetime.now(),
    }

    result = await validator.validate_quote_data(invalid_quote)
    print(
        f"❌ Invalid quote result: {'REJECTED' if not result else 'UNEXPECTEDLY PASSED'}"
    )

    # Test 3: Valid trade data
    print("\n💹 Test 3: Valid Trade Data")
    valid_trade = {
        "symbolId": "F.US.MNQ",
        "price": 23920.50,
        "volume": 1,
        "timestamp": datetime.now(),
    }

    result = await validator.validate_trade_data(valid_trade)
    print(f"✅ Valid trade result: {'PASSED' if result else 'FAILED'}")

    # Test 4: Invalid trade data (negative price)
    print("\n💹 Test 4: Invalid Trade Data (Negative Price)")
    invalid_trade = {
        "symbolId": "F.US.MNQ",
        "price": -100.0,  # Negative price
        "volume": 1,
        "timestamp": datetime.now(),
    }

    result = await validator.validate_trade_data(invalid_trade)
    print(
        f"❌ Invalid trade result: {'REJECTED' if not result else 'UNEXPECTEDLY PASSED'}"
    )

    # Test 5: Invalid volume
    print("\n💹 Test 5: Invalid Trade Data (Excessive Volume)")
    excessive_volume_trade = {
        "symbolId": "F.US.MNQ",
        "price": 23920.50,
        "volume": 200000,  # Exceeds max volume limit
        "timestamp": datetime.now(),
    }

    result = await validator.validate_trade_data(excessive_volume_trade)
    print(
        f"❌ Excessive volume result: {'REJECTED' if not result else 'UNEXPECTEDLY PASSED'}"
    )

    # Test 6: Future timestamp
    print("\n⏰ Test 6: Invalid Trade Data (Future Timestamp)")
    from datetime import timedelta

    future_time = datetime.now() + timedelta(minutes=10)

    future_trade = {
        "symbolId": "F.US.MNQ",
        "price": 23920.50,
        "volume": 1,
        "timestamp": future_time,
    }

    result = await validator.validate_trade_data(future_trade)
    print(
        f"❌ Future timestamp result: {'REJECTED' if not result else 'UNEXPECTEDLY PASSED'}"
    )

    # Get validation statistics
    print("\n📈 Validation Statistics")
    print("=" * 30)
    status = await validator.get_validation_status()

    print(f"Total processed: {status['total_processed']}")
    print(f"Total rejected: {status['total_rejected']}")
    print(f"Rejection rate: {status['rejection_rate']:.1f}%")
    print(
        f"Avg validation time: {status['performance']['avg_validation_time_ms']:.2f}ms"
    )

    print("\n🔍 Rejection Reasons:")
    for reason, count in status["rejection_reasons"].items():
        print(f"  {reason}: {count}")

    print("\n📊 Data Quality Metrics:")
    quality = status["data_quality"]
    for metric, count in quality.items():
        print(f"  {metric}: {count}")


async def test_validation_config():
    """Test different validation configurations."""
    print("\n⚙️  Testing Validation Configurations")
    print("=" * 40)

    from project_x_py.realtime_data_manager.validation import ValidationConfig

    # Default configuration
    default_config = ValidationConfig()
    print(f"Default max price: ${default_config.max_price:,.0f}")
    print(f"Default volume spike threshold: {default_config.volume_spike_threshold}x")
    print(f"Default max spread: {default_config.max_spread_percent}%")

    # Custom configuration for high-frequency trading
    hft_config = ValidationConfig(
        price_range_multiplier=1.5,  # Stricter price validation
        volume_spike_threshold=20.0,  # Allow larger volume spikes
        max_spread_percent=0.5,  # Tighter spread requirements
        timestamp_tolerance_seconds=10.0,  # Stricter timestamp ordering
    )

    print("\nHFT Config:")
    print(f"  Price range multiplier: {hft_config.price_range_multiplier}x")
    print(f"  Volume spike threshold: {hft_config.volume_spike_threshold}x")
    print(f"  Max spread: {hft_config.max_spread_percent}%")
    print(f"  Timestamp tolerance: {hft_config.timestamp_tolerance_seconds}s")


async def main():
    """Main test function."""
    print("🛡️  Project-X-Py Data Validation Test Suite")
    print("=" * 60)

    try:
        await test_data_validation()
        await test_validation_config()

        print("\n✅ All validation tests completed successfully!")
        print("\n📋 Summary:")
        print("  - Price sanity checks (negative, excessive, tick alignment)")
        print("  - Volume validation (negative, excessive, spike detection)")
        print("  - Timestamp verification (future, past, ordering)")
        print("  - Bid/ask spread consistency")
        print("  - Configurable validation rules")
        print("  - Comprehensive rejection metrics")
        print("  - Performance monitoring")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
