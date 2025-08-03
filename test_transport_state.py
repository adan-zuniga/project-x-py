#!/usr/bin/env python3
"""Test SignalR transport state."""

import asyncio

from project_x_py import ProjectX, create_realtime_client, setup_logging

setup_logging(level="INFO")


async def main():
    """Test transport state."""
    print("🔍 Testing SignalR Transport State\n")

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
            connected = await realtime_client.connect()
            print(f"Connected: {connected}")

            # Monitor transport state
            print("\n📊 Monitoring transport state for 10 seconds...")
            for i in range(10):
                await asyncio.sleep(1)

                # Check user connection
                if realtime_client.user_connection:
                    user_transport = realtime_client.user_connection.transport
                    if user_transport:
                        user_running = (
                            user_transport.is_running()
                            if hasattr(user_transport, "is_running")
                            else "N/A"
                        )
                        user_state = (
                            user_transport.state
                            if hasattr(user_transport, "state")
                            else "N/A"
                        )
                    else:
                        user_running = "No transport"
                        user_state = "No transport"
                else:
                    user_running = "No connection"
                    user_state = "No connection"

                # Check market connection
                if realtime_client.market_connection:
                    market_transport = realtime_client.market_connection.transport
                    if market_transport:
                        market_running = (
                            market_transport.is_running()
                            if hasattr(market_transport, "is_running")
                            else "N/A"
                        )
                        market_state = (
                            market_transport.state
                            if hasattr(market_transport, "state")
                            else "N/A"
                        )
                    else:
                        market_running = "No transport"
                        market_state = "No transport"
                else:
                    market_running = "No connection"
                    market_state = "No connection"

                print(
                    f"{i + 1}s - User: running={user_running}, state={user_state} | Market: running={market_running}, state={market_state}"
                )

                # Also check connection flags
                print(
                    f"     Flags - User connected: {realtime_client.user_connected}, Market connected: {realtime_client.market_connected}"
                )

            # Disconnect
            await realtime_client.disconnect()
            print("\n✅ Disconnected")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
