#!/usr/bin/env python3
"""
Platform Configuration Demo

This example demonstrates how to configure the ProjectX Python SDK
for different platforms:
- ProjectX Gateway (demo endpoints)
- TopStepX (production endpoints)
- Custom endpoints

Author: TexasCoding
Date: June 2025
"""

import os
import sys

# Add the src directory to Python path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from project_x_py import (
    create_custom_config,
    load_default_config,
    load_topstepx_config,
)


def demo_configuration_options():
    """Demonstrate different configuration options for platform endpoints."""
    print("🔧 ProjectX Python SDK - Platform Configuration Options\n")

    # 1. Default Configuration (TopStepX)
    print("1️⃣ Default Configuration (TopStepX):")
    default_config = load_default_config()
    print(f"   User Hub: {default_config.user_hub_url}")
    print(f"   Market Hub: {default_config.market_hub_url}")
    print(f"   API URL: {default_config.api_url}")

    # 2. TopStepX Configuration (explicit)
    print("\n2️⃣ TopStepX Configuration (explicit):")
    topstep_config = load_topstepx_config()
    print(f"   User Hub: {topstep_config.user_hub_url}")
    print(f"   Market Hub: {topstep_config.market_hub_url}")

    # 3. Custom Configuration
    print("\n3️⃣ Custom Configuration:")
    custom_config = create_custom_config(
        user_hub_url="https://custom.example.com/hubs/user",
        market_hub_url="https://custom.example.com/hubs/market",
        api_url="https://custom.example.com/api",
        timeout_seconds=60,
        retry_attempts=5,
    )
    print(f"   User Hub: {custom_config.user_hub_url}")
    print(f"   Market Hub: {custom_config.market_hub_url}")
    print(f"   API URL: {custom_config.api_url}")
    print(f"   Timeout: {custom_config.timeout_seconds}s")
    print(f"   Retries: {custom_config.retry_attempts}")


def demo_realtime_client_configuration():
    """Show how to configure realtime client with different endpoints."""
    print("\n🌐 Realtime Client Configuration Examples\n")

    # 1. Using default config (TopStepX)
    print("1️⃣ Default Configuration:")
    print("   client = ProjectXRealtimeClient(token, account_id)")
    print("   # Uses TopStepX endpoints by default")

    # 2. Using explicit config
    print("\n2️⃣ Using Config Object:")
    print("   config = load_topstepx_config()")
    print("   client = ProjectXRealtimeClient(token, account_id, config=config)")

    # 3. Using custom URLs
    print("\n3️⃣ Custom URLs:")
    print("   client = ProjectXRealtimeClient(")
    print("       token, account_id,")
    print("       user_hub_url='https://your-domain.com/hubs/user',")
    print("       market_hub_url='https://your-domain.com/hubs/market'")
    print("   )")

    # 4. Environment variables
    print("\n4️⃣ Environment Variables:")
    print("   # Set in shell:")
    print("   export PROJECTX_USER_HUB_URL=https://your-domain.com/hubs/user")
    print("   export PROJECTX_MARKET_HUB_URL=https://your-domain.com/hubs/market")
    print("   # Then use load_default_config() to pick them up automatically")


def demo_trading_suite_configuration():
    """Demonstrate trading suite configuration for different platforms."""

    print("\n📊 Trading Suite Configuration Examples")
    print("=" * 60)

    # Note: This is just for demonstration - would need valid credentials
    print("\n💡 Code Example: TopStepX Trading Suite")
    print("-" * 45)
    print("""
# For TopStepX (default configuration)
from project_x_py import ProjectX, create_trading_suite, load_topstepx_config

config = load_topstepx_config()
client = ProjectX.from_env()  # Uses environment variables
account = client.get_account_info()

suite = create_trading_suite(
    instrument="MGC",
    project_x=client,
    jwt_token=client.get_session_token(),
    account_id=account.id,
    config=config  # TopStepX endpoints
)
""")

    print("\n💡 Code Example: ProjectX Gateway Trading Suite")
    print("-" * 50)
    print("""
# For ProjectX Gateway
from project_x_py import ProjectX, create_trading_suite, load_projectx_gateway_config

config = load_projectx_gateway_config()
client = ProjectX.from_env()
account = client.get_account_info()

suite = create_trading_suite(
    instrument="MGC",
    project_x=client,
    jwt_token=client.get_session_token(),
    account_id=account.id,
    config=config  # ProjectX Gateway endpoints
)
""")


def demo_environment_configuration():
    """Demonstrate environment-based configuration."""

    print("\n🌍 Environment-Based Configuration")
    print("=" * 60)

    print("""
The configuration system supports environment variables for easy deployment:

Environment Variables:
  PROJECTX_USER_HUB_URL      - User hub WebSocket URL
  PROJECTX_MARKET_HUB_URL    - Market hub WebSocket URL
  PROJECTX_API_URL           - REST API base URL
  PROJECTX_TIMEOUT_SECONDS   - Request timeout
  PROJECTX_RATE_LIMIT        - Requests per minute

Example .env file for TopStepX:
  PROJECTX_USER_HUB_URL=https://rtc.topstepx.com/hubs/user
  PROJECTX_MARKET_HUB_URL=https://rtc.topstepx.com/hubs/market
  PROJECTX_API_URL=https://api.topstepx.com/api

Example .env file for ProjectX Gateway:
  PROJECTX_USER_HUB_URL=https://gateway-rtc-demo.s2f.projectx.com/hubs/user
  PROJECTX_MARKET_HUB_URL=https://gateway-rtc-demo.s2f.projectx.com/hubs/market

The load_default_config() function will automatically use these environment variables
if they are set, making it easy to deploy the same code to different platforms.
""")


def main():
    """Run all configuration demos."""
    try:
        demo_configuration_options()
        demo_realtime_client_configuration()
        demo_trading_suite_configuration()
        demo_environment_configuration()

        print("\n" + "=" * 60)
        print("✅ Platform Configuration Demo Complete!")
        print("\nKey Takeaways:")
        print("- Use load_topstepx_config() for TopStepX endpoints")
        print("- Use load_projectx_gateway_config() for ProjectX Gateway")
        print("- Use create_custom_config() for custom endpoints")
        print("- Environment variables override default settings")
        print("- Manual URL parameters override config settings")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
