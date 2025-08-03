#!/usr/bin/env python3
"""Test SignalR connection directly."""

import asyncio
import logging

from signalrcore.hub_connection_builder import HubConnectionBuilder

from project_x_py import ProjectX

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)


async def main():
    """Test SignalR directly."""
    print("🔍 Testing Direct SignalR Connection\n")

    try:
        # Get JWT token
        async with ProjectX.from_env() as client:
            await client.authenticate()
            jwt = client.session_token
            account_id = str(client.account_info.id)
            print(f"✅ Got JWT token and account ID: {account_id}")

        # Create connection directly
        print("\n🔌 Creating SignalR connection...")
        hub = (
            HubConnectionBuilder()
            .with_url(
                "https://rtc.topstepx.com/hubs/user",
                options={"headers": {"Authorization": f"Bearer {jwt}"}},
            )
            .configure_logging(logging.DEBUG)
            .with_automatic_reconnect(
                {
                    "type": "interval",
                    "keep_alive_interval": 10,
                    "intervals": [1, 3, 5, 5, 5, 5],
                }
            )
            .build()
        )

        # Set up event handlers
        connected = False

        def on_open():
            nonlocal connected
            connected = True
            print("✅ Hub opened!")

        def on_close():
            nonlocal connected
            connected = False
            print("❌ Hub closed!")

        def on_error(error):
            print(f"❌ Error: {error}")

        hub.on_open(on_open)
        hub.on_close(on_close)
        hub.on_error(on_error)

        # Start connection
        print("🚀 Starting connection...")
        hub.start()

        # Wait a bit for connection
        await asyncio.sleep(2)

        print(f"\n📊 Connection status:")
        print(f"   Connected: {connected}")
        print(f"   Transport: {hub.transport}")
        print(f"   State: {hub.transport._state if hub.transport else 'No transport'}")

        if hub.transport:
            print(
                f"   Running: {hub.transport.is_running() if hasattr(hub.transport, 'is_running') else 'N/A'}"
            )

        # Try to send a message
        if connected and hub.transport and hub.transport.is_running():
            print("\n📡 Attempting to subscribe...")
            try:
                hub.send("SubscribeAccounts", [])
                print("✅ Subscribe sent!")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"❌ Subscribe failed: {e}")
        else:
            print("\n❌ Cannot send - hub not properly connected")

        # Stop
        print("\n🔌 Stopping...")
        hub.stop()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
