"""
Environment variable utilities.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides environment variable utilities for configuration management.
    Includes safe environment variable access with validation, default values,
    and error handling for application configuration.

Key Features:
    - Safe environment variable access with defaults
    - Required variable validation with clear error messages
    - Type-safe environment variable handling
    - Comprehensive error handling for missing variables
    - Support for optional and required configuration

Environment Configuration:
    - Optional variables with default values
    - Required variables with validation
    - Clear error messages for missing variables
    - Type-safe return values
    - Comprehensive error handling

Example Usage:
    ```python
    from project_x_py.utils import get_env_var

    # Optional variable with default
    api_key = get_env_var("PROJECTX_API_KEY", default="")

    # Required variable with validation
    try:
        username = get_env_var("PROJECTX_USERNAME", required=True)
    except ValueError as e:
        print(f"Configuration error: {e}")

    # With type conversion
    port = int(get_env_var("PROJECTX_PORT", default="8080"))

    # Environment-specific configuration
    env = get_env_var("PROJECTX_ENV", default="development")
    if env == "production":
        debug = False
    else:
        debug = True
    ```

Configuration Best Practices:
    - Use descriptive variable names with PROJECTX_ prefix
    - Provide sensible defaults for optional variables
    - Validate required variables early in application startup
    - Use type conversion for numeric configuration values
    - Handle missing variables gracefully with clear error messages

Error Handling:
    - Clear error messages for missing required variables
    - Graceful handling of optional variables
    - Type-safe return values
    - Comprehensive validation and error reporting

See Also:
    - `utils.logging_config`: Logging configuration utilities
    - `utils.error_handler`: Error handling for configuration issues
"""

import os
from typing import Any


def get_env_var(name: str, default: Any = None, required: bool = False) -> str:
    """
    Get environment variable with optional default and validation.

    Args:
        name: Environment variable name
        default: Default value if not found
        required: Whether the variable is required

    Returns:
        Environment variable value

    Raises:
        ValueError: If required variable is missing
    """
    value = os.getenv(name, default)
    if required and value is None:
        raise ValueError(f"Required environment variable '{name}' not found")
    return value
