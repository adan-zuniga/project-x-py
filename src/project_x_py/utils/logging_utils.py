"""Logging configuration utilities.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides basic logging configuration utilities for the ProjectX SDK.
    Includes simple logging setup with configurable levels, formats, and
    file output options for basic logging requirements.

Key Features:
    - Basic logging configuration with customizable levels
    - Configurable log format strings
    - Optional file logging support
    - Simple setup for basic logging needs
    - Consistent logger naming across the SDK
    - Easy integration with existing logging systems

Logging Setup:
    - Configurable logging levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Custom format strings for log messages
    - Optional file output for log persistence
    - Consistent logger naming with "project_x_py" prefix
    - Basic logging configuration for simple use cases

Example Usage:
    ```python
    from project_x_py.utils import setup_logging

    # Basic setup with default configuration
    logger = setup_logging()

    # Custom level and format
    logger = setup_logging(
        level="DEBUG",
        format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # With file output
    logger = setup_logging(level="INFO", filename="projectx.log")

    # Use the logger
    logger.info("Application started")
    logger.error("An error occurred")
    ```

Configuration Options:
    - level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - format_string: Custom format for log messages
    - filename: Optional file path for log output
    - Consistent logger naming and configuration

Performance Characteristics:
    - Minimal overhead for basic logging setup
    - Efficient logging configuration
    - Memory-efficient logger management
    - Thread-safe logging operations
    - Optimized for simple logging requirements

See Also:
    - `utils.logging_config`: Advanced logging configuration and monitoring
    - `utils.error_handler`: Error handling with logging integration
"""

import logging


def setup_logging(
    level: str = "INFO",
    format_string: str | None = None,
    filename: str | None = None,
) -> logging.Logger:
    """
    Set up logging configuration for the ProjectX client.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
        filename: Optional filename to write logs to

    Returns:
        Logger instance
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper()), format=format_string, filename=filename
    )

    return logging.getLogger("project_x_py")
