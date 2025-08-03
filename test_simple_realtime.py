#!/usr/bin/env python3
"""Test if we can maintain a SignalR connection."""

import asyncio
import time

from project_x_py import ProjectX, create_realtime_client, setup_logging

setup_logging(level="INFO")


async def main():
    """Test basic real-time connection."""
    print("🔍 Testing Real-time Connection\n")

    try:
        # Authenticate
        async with ProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Authenticated: {client.account_info.name}")

            # Create realtime client
            realtime_client = create_realtime_client(
                jwt_token=client.session_token, account_id=str(client.account_info.id)
            )

            # Connect without subscribing to anything
            print("\n🔌 Connecting to SignalR hubs...")
            connected = await realtime_client.connect()

            if connected:
                print("✅ Initial connection successful!")
                print(f"   User hub: {realtime_client.user_connected}")
                print(f"   Market hub: {realtime_client.market_connected}")

                # Monitor connection status
                print("\n⏱️ Monitoring connection status...")
                for i in range(30):
                    await asyncio.sleep(1)
                    user_status = "✅" if realtime_client.user_connected else "❌"
                    market_status = "✅" if realtime_client.market_connected else "❌"
                    print(f"   {i + 1}s - User: {user_status}, Market: {market_status}")

                    # If both disconnected, break
                    if (
                        not realtime_client.user_connected
                        and not realtime_client.market_connected
                    ):
                        print("\n❌ Both connections lost!")
                        break

                # Try to get connection stats
                stats = realtime_client.get_stats()
                print(f"\n📊 Connection stats:")
                print(f"   Events received: {stats['events_received']}")
                print(f"   Connection errors: {stats['connection_errors']}")

            else:
                print("❌ Failed to connect!")

            # Disconnect
            await realtime_client.disconnect()
            print("\n✅ Disconnected")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
