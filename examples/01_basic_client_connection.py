#!/usr/bin/env python3
"""
Basic Client Connection and Authentication Example

Shows how to connect to ProjectX, authenticate, and verify account access.
This is the foundation for all other examples.

Usage:
    Run with: uv run examples/01_basic_client_connection.py
    Or use test.sh which sets environment variables: ./test.sh

Author: TexasCoding
Date: July 2025
"""

from project_x_py import ProjectX, setup_logging


def main():
    """Demonstrate basic client connection and account verification."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Basic Client Connection Example")

    try:
        # Create client using environment variables
        # This uses PROJECT_X_API_KEY, PROJECT_X_USERNAME, PROJECT_X_ACCOUNT_NAME
        print("🔑 Creating ProjectX client from environment...")
        client = ProjectX.from_env()
        print("✅ Client created successfully!")

        # Get account information
        print("\n📊 Getting account information...")
        account = client.get_account_info()

        if not account:
            print("❌ No account information available")
            return False

        print("✅ Account Information:")
        print(f"   Account ID: {account.id}")
        print(f"   Account Name: {account.name}")
        print(f"   Balance: ${account.balance:,.2f}")
        print(f"   Trading Enabled: {account.canTrade}")
        print(f"   Simulated Account: {account.simulated}")

        # Verify trading capability
        if not account.canTrade:
            print("⚠️  Warning: Trading is not enabled on this account")

        if account.simulated:
            print("✅ This is a simulated account - safe for testing")
        else:
            print("⚠️  This is a LIVE account - be careful with real money!")

        # Test JWT token generation (needed for real-time features)
        print("\n🔐 Testing JWT token generation...")
        try:
            jwt_token = client.get_session_token()
            if jwt_token:
                print("✅ JWT token generated successfully")
                print(f"   Token length: {len(jwt_token)} characters")
            else:
                print("❌ Failed to generate JWT token")
        except Exception as e:
            print(f"❌ JWT token error: {e}")

        # Search for MNQ instrument (our testing instrument)
        print("\n🔍 Searching for MNQ (Micro E-mini NASDAQ) instrument...")
        instruments = client.search_instruments("MNQ")

        if instruments:
            print(f"✅ Found {len(instruments)} MNQ instruments:")
            for i, inst in enumerate(instruments[:3]):  # Show first 3
                print(f"   {i + 1}. {inst.name}")
                print(f"      ID: {inst.id}")
                print(f"      Description: {inst.description}")
                print(f"      Tick Size: ${inst.tickSize}")
                print(f"      Tick Value: ${inst.tickValue}")
        else:
            print("❌ No MNQ instruments found")

        # Get specific MNQ instrument for trading
        print("\n📈 Getting current MNQ contract...")
        mnq_instrument = client.get_instrument("MNQ")

        if mnq_instrument:
            print("✅ Current MNQ Contract:")
            print(f"   Contract ID: {mnq_instrument.id}")
            print(f"   Name: {mnq_instrument.name}")
            print(f"   Description: {mnq_instrument.description}")
            print(f"   Minimum Tick: ${mnq_instrument.tickSize}")
            print(f"   Tick Value: ${mnq_instrument.tickValue}")
        else:
            print("❌ Could not get MNQ instrument")

        # Test basic market data access
        print("\n📊 Testing market data access...")
        try:
            # Get recent data with different intervals to find what works
            for interval in [15, 5, 1]:  # Try 15-min, 5-min, 1-min
                data = client.get_data("MNQ", days=1, interval=interval)

                if data is not None and not data.is_empty():
                    print(
                        f"✅ Retrieved {len(data)} bars of {interval}-minute MNQ data"
                    )

                    # Show the most recent bar
                    latest_bar = data.tail(1)
                    for row in latest_bar.iter_rows(named=True):
                        print(f"   Latest {interval}-min Bar:")
                        print(f"     Time: {row['timestamp']}")
                        print(f"     Open: ${row['open']:.2f}")
                        print(f"     High: ${row['high']:.2f}")
                        print(f"     Low: ${row['low']:.2f}")
                        print(f"     Close: ${row['close']:.2f}")
                        print(f"     Volume: {row['volume']:,}")
                    break  # Stop after first successful data retrieval
            else:
                # If no interval worked, try with different days
                for days in [2, 5, 7]:
                    data = client.get_data("MNQ", days=days, interval=15)
                    if data is not None and not data.is_empty():
                        print(
                            f"✅ Retrieved {len(data)} bars of 15-minute MNQ data ({days} days)"
                        )
                        latest_bar = data.tail(1)
                        for row in latest_bar.iter_rows(named=True):
                            print(
                                f"   Latest Bar: ${row['close']:.2f} @ {row['timestamp']}"
                            )
                        break
                else:
                    print("❌ No market data available (may be outside market hours)")
                    print(
                        "   Note: Historical data availability depends on market hours and trading sessions"
                    )

        except Exception as e:
            print(f"❌ Market data error: {e}")

        # Check current positions and orders
        print("\n💼 Checking current positions...")
        try:
            positions = client.search_open_positions()
            if positions:
                print(f"✅ Found {len(positions)} open positions:")
                for pos in positions:
                    direction = "LONG" if pos.type == 1 else "SHORT"
                    print(
                        f"   {direction} {pos.size} {pos.contractId} @ ${pos.averagePrice:.2f}"
                    )
            else:
                print("📝 No open positions")
        except Exception as e:
            print(f"❌ Position check error: {e}")

        print("\n📋 Order Management Information:")
        print("   i  Order management requires the OrderManager component")
        print(
            "   Example: order_manager = create_order_manager(client, realtime_client)"
        )
        print("   See examples/02_order_management.py for complete order functionality")

        print("\n✅ Basic client connection example completed successfully!")
        print("\n📝 Next Steps:")
        print("   - Try examples/02_order_management.py for order placement")
        print("   - Try examples/03_position_management.py for position tracking")
        print("   - Try examples/04_realtime_data.py for real-time data feeds")

        return True

    except Exception as e:
        logger.error(f"❌ Example failed: {e}")
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
