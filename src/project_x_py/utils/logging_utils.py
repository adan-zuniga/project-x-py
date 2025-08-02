"""Logging configuration utilities."""

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
