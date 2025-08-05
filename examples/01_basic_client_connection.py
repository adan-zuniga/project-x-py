#!/usr/bin/env python3
"""
Async Basic Client Connection and Authentication Example

Shows how to connect to ProjectX asynchronously, authenticate, and verify account access.
This is the foundation for all other async examples.

Usage:
    Run with: uv run examples/01_basic_client_connection.py
    Or use test.sh which sets environment variables: ./test.sh

Author: TexasCoding
Date: July 2025
"""

import asyncio

from project_x_py import ProjectX, setup_logging


async def main():
    """Demonstrate basic async client connection and account verification."""
    logger = setup_logging(level="INFO")
    logger.info("🚀 Starting Async Basic Client Connection Example")

    try:
        # Create async client using environment variables
        # This uses PROJECT_X_API_KEY, PROJECT_X_USERNAME, PROJECT_X_ACCOUNT_NAME
        print("🔑 Creating ProjectX client from environment...")

        # Use async context manager for proper resource cleanup
        async with ProjectX.from_env() as client:
            print("✅ Async client created successfully!")

            # Authenticate asynchronously
            print("\n🔐 Authenticating...")
            await client.authenticate()
            print("✅ Authentication successful!")

            # Get account information
            print("\n📊 Getting account information...")
            account = client.account_info

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
                print("Info: This is a simulated account")

            # Test account health with concurrent requests
            print("\n🏥 Testing account health with concurrent requests...")

            # Run multiple operations concurrently
            health_task = asyncio.create_task(client.get_health_status())
            positions_task = asyncio.create_task(client.search_open_positions())
            instruments_task = asyncio.create_task(client.search_instruments("MGC"))

            # Wait for all tasks to complete
            health, positions, instruments = await asyncio.gather(
                health_task, positions_task, instruments_task
            )

            print(f"✅ API Calls Made: {health['api_calls']}")
            print(f"✅ Open Positions: {len(positions)}")
            print(f"✅ Found Instruments: {len(instruments)}")

            # Show async benefits
            print("\n🚀 Async Benefits Demonstrated:")
            print("   - Non-blocking I/O operations")
            print("   - Concurrent API calls with asyncio.gather()")
            print("   - Proper resource cleanup with async context manager")
            print("   - Better performance for multiple operations")

            return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Run the async main function
    print("\n" + "=" * 60)
    print("ASYNC BASIC CLIENT CONNECTION EXAMPLE")
    print("=" * 60 + "\n")

    success = asyncio.run(main())

    if success:
        print("\n✅ Example completed successfully!")
    else:
        print("\n❌ Example failed!")
