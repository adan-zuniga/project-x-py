#!/usr/bin/env python3
"""Test subscription timing issues."""

import asyncio

from project_x_py import ProjectX, create_realtime_client, setup_logging

setup_logging(level="INFO")


async def main():
    """Test subscription with different timing."""
    print("🔍 Testing Subscription Timing\n")

    try:
        async with ProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Authenticated: {client.account_info.name}")

            # Create realtime client
            realtime_client = create_realtime_client(
                jwt_token=client.session_token, account_id=str(client.account_info.id)
            )

            # Connect
            print("\n🔌 Connecting...")
            if await realtime_client.connect():
                print("✅ Connected!")

                # Try subscribing with different delays
                delays = [0, 1, 2, 5, 10]

                for delay in delays:
                    print(f"\n⏱️ Testing subscription with {delay}s delay...")
                    await asyncio.sleep(delay)

                    # Check connection status first
                    print(f"   User connected: {realtime_client.user_connected}")
                    print(f"   Market connected: {realtime_client.market_connected}")

                    # Check if transport is available
                    if hasattr(realtime_client.user_connection, "transport"):
                        transport = realtime_client.user_connection.transport
                        if transport:
                            print(
                                f"   Transport state: {transport._state if hasattr(transport, '_state') else 'unknown'}"
                            )
                            print(
                                f"   Transport running: {transport.is_running() if hasattr(transport, 'is_running') else 'unknown'}"
                            )

                    # Try to subscribe
                    try:
                        result = await realtime_client.subscribe_user_updates()
                        print(
                            f"   Subscribe result: {'✅ Success' if result else '❌ Failed'}"
                        )

                        if result:
                            print("   Success! Breaking loop.")
                            break
                    except Exception as e:
                        print(f"   ❌ Error: {e}")

                # Disconnect
                await realtime_client.disconnect()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
