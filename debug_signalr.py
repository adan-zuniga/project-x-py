#!/usr/bin/env python3
"""Debug SignalR connection issues."""

import asyncio
import logging

from project_x_py import ProjectX, setup_logging

# Enable detailed logging
setup_logging(level="DEBUG")

# Also enable SignalR logging
signalr_logger = logging.getLogger("SignalRCoreClient")
signalr_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
signalr_logger.addHandler(handler)


async def main():
    """Test SignalR connection."""
    print("🔍 Debug SignalR Connection Test")
    print("=" * 60)

    try:
        async with ProjectX.from_env() as client:
            await client.authenticate()
            print(f"✅ Authenticated: {client.account_info.name}")
            print(f"   Account ID: {client.account_info.id}")

            # Get and display JWT token info (first few chars only)
            jwt = client.session_token
            print(f"   JWT Token: {jwt[:20]}...{jwt[-20:]}")
            print(f"   Token length: {len(jwt)}")

            # Parse JWT to check structure
            parts = jwt.split(".")
            print(f"   JWT parts: {len(parts)} (should be 3)")

            # Create realtime client with explicit configuration
            from project_x_py.realtime import ProjectXRealtimeClient

            print("\n🔌 Creating realtime client...")
            realtime_client = ProjectXRealtimeClient(
                jwt_token=jwt,
                account_id=str(client.account_info.id),
                user_hub_url="https://rtc.topstepx.com/hubs/user",
                market_hub_url="https://rtc.topstepx.com/hubs/market",
            )

            print("   URLs configured:")
            print(f"   User Hub: {realtime_client.user_hub_url}")
            print(f"   Market Hub: {realtime_client.market_hub_url}")

            # Try to connect
            print("\n🚀 Attempting connection...")
            connected = await realtime_client.connect()

            if connected:
                print("✅ Connected successfully!")
                print(f"   User connected: {realtime_client.user_connected}")
                print(f"   Market connected: {realtime_client.market_connected}")

                # Wait a bit to see if connection stays alive
                print("\n⏱️ Monitoring connection for 10 seconds...")
                for i in range(10):
                    await asyncio.sleep(1)
                    print(
                        f"   {i + 1}s - User: {realtime_client.user_connected}, Market: {realtime_client.market_connected}"
                    )

                # Try to subscribe
                print("\n📡 Attempting to subscribe to user updates...")
                sub_result = await realtime_client.subscribe_user_updates()
                print(f"   Subscription result: {sub_result}")

                # Disconnect
                print("\n🔌 Disconnecting...")
                await realtime_client.disconnect()
            else:
                print("❌ Connection failed!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
