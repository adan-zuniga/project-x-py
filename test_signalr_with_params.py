#!/usr/bin/env python3
"""Test SignalR with different URL parameters."""

import asyncio
import logging
import urllib.parse

from signalrcore.hub_connection_builder import HubConnectionBuilder

from project_x_py import ProjectX

# Enable detailed logging
logging.basicConfig(level=logging.INFO)


async def test_connection(url_params=""):
    """Test a SignalR connection with given parameters."""
    try:
        # Get JWT token
        async with ProjectX.from_env() as client:
            await client.authenticate()
            jwt = client.session_token
            account_id = str(client.account_info.id)

        # Build URL with params
        base_url = "https://rtc.topstepx.com/hubs/user"
        if url_params:
            base_url = f"{base_url}?{url_params}"

        print(f"\n🔌 Testing with URL: {base_url}")

        # Create connection
        hub = (
            HubConnectionBuilder()
            .with_url(
                base_url,
                options={
                    "headers": {
                        "Authorization": f"Bearer {jwt}",
                        "X-Account-Id": account_id,  # Try adding account ID header
                    }
                },
            )
            .configure_logging(logging.WARNING)
            .build()
        )

        connected = False
        close_reason = None

        def on_open():
            nonlocal connected
            connected = True
            print("   ✅ Connection opened")

        def on_close():
            nonlocal connected
            connected = False
            print("   ❌ Connection closed")

        def on_error(error):
            nonlocal close_reason
            close_reason = str(error)
            print(f"   ❌ Error: {error}")

        hub.on_open(on_open)
        hub.on_close(on_close)
        hub.on_error(on_error)

        # Start
        hub.start()
        await asyncio.sleep(3)

        # Check status
        if connected:
            print("   📊 Status: Connected and stable")
            hub.stop()
            return True
        else:
            print(f"   📊 Status: Failed - {close_reason or 'Connection closed'}")
            return False

    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False


async def main():
    """Test different connection configurations."""
    print("🔍 Testing SignalR Connection Configurations\n")

    # Get account info first
    async with ProjectX.from_env() as client:
        await client.authenticate()
        account_id = str(client.account_info.id)
        print(f"Account ID: {account_id}")

    # Test different parameter combinations
    test_cases = [
        ("No params", ""),
        ("With accountId", f"accountId={account_id}"),
        ("With account", f"account={account_id}"),
    ]

    results = []
    for name, params in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Test: {name}")
        success = await test_connection(
            params if not params.startswith("access_token") else ""
        )
        results.append((name, success))
        await asyncio.sleep(1)  # Avoid rate limiting

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 Summary:")
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {name}")


if __name__ == "__main__":
    asyncio.run(main())
