Error Handling & Logging
========================

The ProjectX Python SDK (v2.0.5+) includes a comprehensive error handling and logging system designed for production use.

Overview
--------

The SDK provides:

* Centralized error handling with decorators
* Structured logging with JSON support
* Automatic retry logic for network operations
* Rate limit management with backoff
* Standardized error messages and codes
* Context-aware logging for debugging

Error Handling Decorators
-------------------------

The SDK uses decorators to provide consistent error handling across all modules:

@handle_errors
~~~~~~~~~~~~~~

Wraps methods to catch and log errors consistently:

.. code-block:: python

   from project_x_py.utils import handle_errors
   
   @handle_errors("fetch market data")
   async def get_market_data(self):
       # Method implementation
       pass

Parameters:

* ``operation``: Description of the operation for logging
* ``logger``: Optional logger instance (defaults to method's module logger)
* ``reraise``: Whether to re-raise the exception (default: True)
* ``default_return``: Value to return on error if not re-raising

@retry_on_network_error
~~~~~~~~~~~~~~~~~~~~~~~

Automatically retries network operations with exponential backoff:

.. code-block:: python

   from project_x_py.utils import retry_on_network_error
   
   @retry_on_network_error(max_attempts=3, initial_delay=1.0)
   async def make_api_call(self):
       # API call implementation
       pass

Parameters:

* ``max_attempts``: Maximum number of retry attempts (default: 3)
* ``backoff_factor``: Multiplier for delay between retries (default: 2.0)
* ``initial_delay``: Initial delay in seconds (default: 1.0)
* ``max_delay``: Maximum delay between retries (default: 60.0)

@handle_rate_limit
~~~~~~~~~~~~~~~~~~

Manages API rate limits with automatic backoff:

.. code-block:: python

   from project_x_py.utils import handle_rate_limit
   
   @handle_rate_limit()
   async def api_method(self):
       # Rate-limited API call
       pass

@validate_response
~~~~~~~~~~~~~~~~~~

Validates API response structure:

.. code-block:: python

   from project_x_py.utils import validate_response
   
   @validate_response(required_fields=["orderId", "status"])
   async def place_order(self):
       # Returns response that must contain orderId and status
       pass

Structured Logging
------------------

ProjectXLogger
~~~~~~~~~~~~~~

Factory for creating configured loggers:

.. code-block:: python

   from project_x_py.utils import ProjectXLogger
   
   logger = ProjectXLogger.get_logger(__name__)
   logger.info("Starting operation")

LogContext
~~~~~~~~~~

Context manager for adding structured context to logs:

.. code-block:: python

   from project_x_py.utils import LogContext, LogMessages
   
   with LogContext(logger, operation="place_order", symbol="MGC", size=1):
       logger.info(LogMessages.ORDER_PLACE)
       # All logs within this context include the extra fields

Standard Log Messages
~~~~~~~~~~~~~~~~~~~~~

Use predefined log messages for consistency:

.. code-block:: python

   from project_x_py.utils import LogMessages
   
   logger.info(LogMessages.AUTH_START)
   logger.info(LogMessages.ORDER_PLACED, extra={"order_id": "12345"})
   logger.error(LogMessages.DATA_ERROR, extra={"error": str(e)})

Configuration
-------------

SDK-Wide Logging Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure logging for your entire application:

.. code-block:: python

   from project_x_py.utils import configure_sdk_logging
   import logging
   
   # Development configuration
   configure_sdk_logging(
       level=logging.DEBUG,
       format_json=False,  # Human-readable format
   )
   
   # Production configuration
   configure_sdk_logging(
       level=logging.INFO,
       format_json=True,  # JSON format for log aggregation
       log_file="/var/log/projectx/trading.log"
   )

Environment Variables
~~~~~~~~~~~~~~~~~~~~~

Control logging via environment:

.. code-block:: bash

   export PROJECTX_LOG_LEVEL=DEBUG
   export PROJECTX_LOG_FORMAT=json
   export PROJECTX_MAX_RETRIES=5
   export PROJECTX_RETRY_DELAY=2.0

Error Types
-----------

The SDK defines specific exception types for different error scenarios:

.. code-block:: python

   from project_x_py.exceptions import (
       ProjectXError,              # Base exception
       ProjectXAuthenticationError, # Authentication failures
       ProjectXOrderError,         # Order-related errors
       ProjectXDataError,          # Data/parsing errors
       ProjectXRateLimitError,     # Rate limit exceeded
       ProjectXConnectionError,    # Network/connection issues
       ProjectXServerError,        # Server-side errors
   )

Best Practices
--------------

1. **Use decorators consistently**: Apply appropriate decorators to all async methods
2. **Add context to logs**: Use LogContext and extra fields for debugging
3. **Handle specific exceptions**: Catch specific exception types when needed
4. **Let decorators handle retries**: Don't implement manual retry logic
5. **Use standard messages**: Prefer LogMessages and ErrorMessages constants

Example: Complete Error Handling
--------------------------------

.. code-block:: python

   from project_x_py.utils import (
       handle_errors,
       retry_on_network_error,
       validate_response,
       LogContext,
       LogMessages,
       ProjectXLogger,
   )
   
   class TradingStrategy:
       def __init__(self):
           self.logger = ProjectXLogger.get_logger(__name__)
       
       @handle_errors("execute trade")
       @retry_on_network_error(max_attempts=3)
       @validate_response(required_fields=["orderId"])
       async def execute_trade(self, symbol: str, size: int):
           with LogContext(
               self.logger,
               operation="execute_trade",
               symbol=symbol,
               size=size
           ):
               self.logger.info(LogMessages.ORDER_PLACE)
               
               # Place order
               response = await self.client.place_order(
                   contract_id=symbol,
                   order_type=1,  # Limit
                   side=0,        # Buy
                   size=size,
                   limit_price=current_price
               )
               
               self.logger.info(
                   LogMessages.ORDER_PLACED,
                   extra={"order_id": response.orderId}
               )
               
               return response

Production Monitoring
---------------------

The structured logging format enables easy integration with log aggregation tools:

* **Elasticsearch/Kibana**: Parse JSON logs for searching and dashboards
* **Splunk**: Index structured fields for alerts and analytics
* **CloudWatch**: Stream logs to AWS for monitoring
* **Datadog**: Aggregate logs with APM traces

Example log entry in production:

.. code-block:: json

   {
       "timestamp": "2025-08-03T10:30:45.123Z",
       "level": "INFO",
       "logger": "project_x_py.order_manager",
       "message": "Order placed successfully",
       "operation": "place_order",
       "symbol": "MGC",
       "size": 1,
       "order_id": "12345",
       "duration_ms": 150.5
   }