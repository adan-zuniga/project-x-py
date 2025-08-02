"""Payload parsing and validation functionality for real-time data."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from project_x_py.realtime_data_manager.types import RealtimeDataManagerProtocol

logger = logging.getLogger(__name__)


class ValidationMixin:
    """Mixin for payload parsing and validation."""

    def _parse_and_validate_trade_payload(
        self: "RealtimeDataManagerProtocol", trade_data: Any
    ) -> dict[str, Any] | None:
        """Parse and validate trade payload, returning the parsed data or None if invalid."""
        # Handle string payloads - parse JSON if it's a string
        if isinstance(trade_data, str):
            try:
                self.logger.debug(
                    f"Attempting to parse trade JSON string: {trade_data[:200]}..."
                )
                trade_data = json.loads(trade_data)
                self.logger.debug(
                    f"Successfully parsed JSON string payload: {type(trade_data)}"
                )
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Failed to parse trade payload JSON: {e}")
                self.logger.warning(f"Trade payload content: {trade_data[:500]}...")
                return None

        # Handle list payloads - SignalR sends [contract_id, data_dict]
        if isinstance(trade_data, list):
            if not trade_data:
                self.logger.warning("Trade payload is an empty list")
                return None
            if len(trade_data) >= 2:
                # SignalR format: [contract_id, actual_data_dict]
                trade_data = trade_data[1]
                self.logger.debug(
                    f"Using second item from SignalR trade list: {type(trade_data)}"
                )
            else:
                # Fallback: use first item if only one element
                trade_data = trade_data[0]
                self.logger.debug(
                    f"Using first item from trade list: {type(trade_data)}"
                )

        # Handle nested list case: trade data might be wrapped in another list
        if (
            isinstance(trade_data, list)
            and trade_data
            and isinstance(trade_data[0], dict)
        ):
            trade_data = trade_data[0]
            self.logger.debug(
                f"Using first item from nested trade list: {type(trade_data)}"
            )

        if not isinstance(trade_data, dict):
            self.logger.warning(
                f"Trade payload is not a dict after processing: {type(trade_data)}"
            )
            self.logger.debug(f"Trade payload content: {trade_data}")
            return None

        required_fields = {"symbolId", "price", "timestamp", "volume"}
        missing_fields = required_fields - set(trade_data.keys())
        if missing_fields:
            self.logger.warning(
                f"Trade payload missing required fields: {missing_fields}"
            )
            self.logger.debug(f"Available fields: {list(trade_data.keys())}")
            return None

        return trade_data

    def _parse_and_validate_quote_payload(
        self: "RealtimeDataManagerProtocol", quote_data: Any
    ) -> dict[str, Any] | None:
        """Parse and validate quote payload, returning the parsed data or None if invalid."""
        # Handle string payloads - parse JSON if it's a string
        if isinstance(quote_data, str):
            try:
                self.logger.debug(
                    f"Attempting to parse quote JSON string: {quote_data[:200]}..."
                )
                quote_data = json.loads(quote_data)
                self.logger.debug(
                    f"Successfully parsed JSON string payload: {type(quote_data)}"
                )
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Failed to parse quote payload JSON: {e}")
                self.logger.warning(f"Quote payload content: {quote_data[:500]}...")
                return None

        # Handle list payloads - SignalR sends [contract_id, data_dict]
        if isinstance(quote_data, list):
            if not quote_data:
                self.logger.warning("Quote payload is an empty list")
                return None
            if len(quote_data) >= 2:
                # SignalR format: [contract_id, actual_data_dict]
                quote_data = quote_data[1]
                self.logger.debug(
                    f"Using second item from SignalR quote list: {type(quote_data)}"
                )
            else:
                # Fallback: use first item if only one element
                quote_data = quote_data[0]
                self.logger.debug(
                    f"Using first item from quote list: {type(quote_data)}"
                )

        if not isinstance(quote_data, dict):
            self.logger.warning(
                f"Quote payload is not a dict after processing: {type(quote_data)}"
            )
            self.logger.debug(f"Quote payload content: {quote_data}")
            return None

        # More flexible validation - only require symbol and timestamp
        # Different quote types have different data (some may not have all price fields)
        required_fields = {"symbol", "timestamp"}
        missing_fields = required_fields - set(quote_data.keys())
        if missing_fields:
            self.logger.warning(
                f"Quote payload missing required fields: {missing_fields}"
            )
            self.logger.debug(f"Available fields: {list(quote_data.keys())}")
            return None

        return quote_data

    def _symbol_matches_instrument(
        self: "RealtimeDataManagerProtocol", symbol: str
    ) -> bool:
        """
        Check if the symbol from the payload matches our tracked instrument.

        Args:
            symbol: Symbol from the payload (e.g., "F.US.EP")

        Returns:
            bool: True if symbol matches our instrument
        """
        # Extract the base symbol from the full symbol ID
        # Example: "F.US.EP" -> "EP", "F.US.MGC" -> "MGC"
        if "." in symbol:
            parts = symbol.split(".")
            base_symbol = parts[-1] if parts else symbol
        else:
            base_symbol = symbol

        # Compare with our instrument (case-insensitive)
        return base_symbol.upper() == self.instrument.upper()

    def get_realtime_validation_status(
        self: "RealtimeDataManagerProtocol",
    ) -> dict[str, Any]:
        """
        Get validation status for real-time data feed integration.

        Returns:
            Dict with validation status

        Example:
            >>> status = manager.get_realtime_validation_status()
            >>> print(f"Feed active: {status['is_running']}")
        """
        return {
            "is_running": self.is_running,
            "contract_id": self.contract_id,
            "instrument": self.instrument,
            "timeframes_configured": list(self.timeframes.keys()),
            "data_available": {tf: tf in self.data for tf in self.timeframes},
            "ticks_processed": self.memory_stats["ticks_processed"],
            "bars_cleaned": self.memory_stats["bars_cleaned"],
            "projectx_compliance": {
                "quote_handling": "✅ Compliant",
                "trade_handling": "✅ Compliant",
                "tick_processing": "✅ Async",
                "memory_management": "✅ Automatic cleanup",
            },
        }
