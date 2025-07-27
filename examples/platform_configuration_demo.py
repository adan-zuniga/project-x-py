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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from project_x_py import (
    ProjectX,
    ProjectXRealtimeClient,
    create_custom_config,
    create_trading_suite,
    load_default_config,
    load_projectx_gateway_config,
    load_topstepx_config,
)


def demo_configuration_options():
    """Demonstrate different configuration options for platform endpoints."""
    
    print("🔧 ProjectX Python SDK - Platform Configuration Demo")
    print("=" * 60)
    
    # 1. Default Configuration (TopStepX)
    print("\n1️⃣ Default Configuration (TopStepX)")
    print("-" * 40)
    default_config = load_default_config()
    print(f"User Hub URL: {default_config.user_hub_url}")
    print(f"Market Hub URL: {default_config.market_hub_url}")
    print(f"API URL: {default_config.api_url}")
    
    # 2. ProjectX Gateway Configuration
    print("\n2️⃣ ProjectX Gateway Configuration")
    print("-" * 40)
    gateway_config = load_projectx_gateway_config()
    print(f"User Hub URL: {gateway_config.user_hub_url}")
    print(f"Market Hub URL: {gateway_config.market_hub_url}")
    print(f"API URL: {gateway_config.api_url}")
    
    # 3. TopStepX Configuration (explicit)
    print("\n3️⃣ TopStepX Configuration (explicit)")
    print("-" * 40)
    topstep_config = load_topstepx_config()
    print(f"User Hub URL: {topstep_config.user_hub_url}")
    print(f"Market Hub URL: {topstep_config.market_hub_url}")
    print(f"API URL: {topstep_config.api_url}")
    
    # 4. Custom Configuration
    print("\n4️⃣ Custom Configuration")
    print("-" * 40)
    custom_config = create_custom_config(
        user_hub_url="https://my-custom-platform.com/hubs/user",
        market_hub_url="https://my-custom-platform.com/hubs/market",
        api_url="https://my-custom-platform.com/api",
        timeout_seconds=60,
        requests_per_minute=120
    )
    print(f"User Hub URL: {custom_config.user_hub_url}")
    print(f"Market Hub URL: {custom_config.market_hub_url}")
    print(f"API URL: {custom_config.api_url}")
    print(f"Timeout: {custom_config.timeout_seconds}s")
    print(f"Rate Limit: {custom_config.requests_per_minute} req/min")


def demo_realtime_client_configuration():
    """Demonstrate realtime client configuration for different platforms."""
    
    print("\n🌐 Realtime Client Configuration Examples")
    print("=" * 60)
    
    # Mock JWT token and account ID for demo
    jwt_token = "demo_jwt_token_12345"
    account_id = "12345"
    
    # 1. Using TopStepX configuration
    print("\n1️⃣ TopStepX Realtime Client")
    print("-" * 30)
    topstep_config = load_topstepx_config()
    client1 = ProjectXRealtimeClient(jwt_token, account_id, config=topstep_config)
    print(f"Configured for: {client1.base_user_url}")
    
    # 2. Using ProjectX Gateway configuration
    print("\n2️⃣ ProjectX Gateway Realtime Client")
    print("-" * 35)
    gateway_config = load_projectx_gateway_config()
    client2 = ProjectXRealtimeClient(jwt_token, account_id, config=gateway_config)
    print(f"Configured for: {client2.base_user_url}")
    
    # 3. Manual URL override
    print("\n3️⃣ Manual URL Override")
    print("-" * 25)
    client3 = ProjectXRealtimeClient(
        jwt_token, 
        account_id,
        user_hub_url="https://custom-rtc.example.com/hubs/user",
        market_hub_url="https://custom-rtc.example.com/hubs/market"
    )
    print(f"Configured for: {client3.base_user_url}")
    
    # 4. Default (no config - uses ProjectX Gateway)
    print("\n4️⃣ Default Configuration")
    print("-" * 25)
    client4 = ProjectXRealtimeClient(jwt_token, account_id)
    print(f"Configured for: {client4.base_user_url}")


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