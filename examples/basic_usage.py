"""
Basic async usage example for the ProjectX Python SDK v2.0.0

This example demonstrates the new async/await patterns introduced in v2.0.0.
"""

import asyncio
import os

from project_x_py import ProjectX
from project_x_py.models import Instrument, Position


async def main():
    """Main async function demonstrating basic SDK usage."""

    # Method 1: Using environment variables (recommended)
    # Set these environment variables:
    # export PROJECT_X_API_KEY="your_api_key"
    # export PROJECT_X_USERNAME="your_username"

    print("🚀 ProjectX Python SDK v2.0.0 - Async Example")
    print("=" * 50)

    try:
        # Create async client using environment variables
        async with ProjectX.from_env() as client:
            print("✅ Client created successfully")
            if client.account_info is None:
                print("❌ No account info found")
                return

            # Authenticate
            print("\n🔐 Authenticating...")
            await client.authenticate()
            print(f"✅ Authenticated as: {client.account_info.name}")
            print(f"📊 Using account: {client.account_info.name}")
            print(f"💰 Balance: ${client.account_info.balance:,.2f}")

            # Get positions
            print("\n📈 Fetching positions...")
            positions: list[Position] = await client.get_positions()

            if positions:
                print(f"Found {len(positions)} position(s):")
                for pos in positions:
                    side = "Long" if pos.type == "LONG" else "Short"
                    print(
                        f"  - {pos.contractId}: {side} {pos.size} @ ${pos.averagePrice}"
                    )
            else:
                print("No open positions")

            # Get instrument info
            print("\n🔍 Fetching instrument information...")
            # Run multiple instrument fetches concurrently
            instruments: tuple[
                Instrument, Instrument, Instrument
            ] = await asyncio.gather(
                client.get_instrument("NQ"),
                client.get_instrument("ES"),
                client.get_instrument("MGC"),
            )

            print("Instrument details:")
            for inst in instruments:
                print(f"  - {inst.symbolId}: {inst.name}")
                print(f"    Tick size: ${inst.tickSize}")
                print(f"    Contract size: {inst.tickValue}")

            # Show performance stats
            print("\n📊 Performance Statistics:")
            health = await client.get_health_status()
            print(f"  - API calls made: {health['api_calls']}")
            print(f"  - Cache hits: {health['cache_hits']}")
            print(f"  - Cache hit rate: {health['cache_hit_rate']:.1%}")
            print(f"  - Token expires in: {health['token_expires_in']:.0f} seconds")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


async def concurrent_example():
    """Example showing concurrent API operations."""
    print("\n🚀 Concurrent Operations Example")
    print("=" * 50)

    async with ProjectX.from_env() as client:
        await client.authenticate()

        # Time sequential operations
        import time

        start = time.time()

        sequential_time = time.time() - start
        print(f"Sequential operations took: {sequential_time:.2f} seconds")

        # Concurrent (new way)
        start = time.time()

        # Run all operations concurrently
        pos2, inst3, inst4 = await asyncio.gather(
            client.get_positions(),
            client.get_instrument("NQ"),
            client.get_instrument("ES"),
        )

        concurrent_time = time.time() - start
        print(f"Concurrent operations took: {concurrent_time:.2f} seconds")
        print(f"Speed improvement: {sequential_time / concurrent_time:.1f}x faster!")


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("PROJECT_X_API_KEY") or not os.getenv("PROJECT_X_USERNAME"):
        print(
            "❌ Please set PROJECT_X_API_KEY and PROJECT_X_USERNAME environment variables"
        )
        print("Example:")
        print("  export PROJECT_X_API_KEY='your_api_key'")
        print("  export PROJECT_X_USERNAME='your_username'")
        exit(1)

    # Run the main example
    asyncio.run(main())

    # Uncomment to run concurrent example
    # asyncio.run(concurrent_example())
