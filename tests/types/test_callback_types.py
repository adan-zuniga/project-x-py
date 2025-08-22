"""
Tests for callback data TypedDict definitions.

Author: @TexasCoding
Date: 2025-08-17
"""

from datetime import datetime
from typing import get_type_hints

from project_x_py.models import Order, Position
from project_x_py.types.callback_types import (
    AccountUpdateData,
    ConnectionStatusData,
    ErrorData,
    MarketDepthData,
    MarketTradeData,
    NewBarData,
    OrderFilledData,
    OrderUpdateData,
    PositionAlertData,
    PositionClosedData,
    PositionUpdateData,
    QuoteUpdateData,
    SystemStatusData,
    TradeExecutionData,
)


class TestCallbackTypes:
    """Test suite for callback data TypedDict definitions."""

    def test_order_update_data_structure(self):
        """Test OrderUpdateData structure."""
        hints = get_type_hints(OrderUpdateData, include_extras=True)

        assert "order_id" in hints
        assert hints["order_id"] == int
        assert "status" in hints
        assert hints["status"] == int
        assert "timestamp" in hints
        assert hints["timestamp"] == str

        # Optional fields
        assert "order" in hints
        assert "fill_volume" in hints
        assert "filled_price" in hints

    def test_order_filled_data_structure(self):
        """Test OrderFilledData structure."""
        hints = get_type_hints(OrderFilledData, include_extras=True)

        assert "order_id" in hints
        assert hints["order_id"] == int
        assert "order" in hints
        assert hints["order"] == Order
        assert "filled_price" in hints
        assert hints["filled_price"] == float
        assert "filled_volume" in hints
        assert hints["filled_volume"] == int

    def test_position_update_data_structure(self):
        """Test PositionUpdateData structure."""
        hints = get_type_hints(PositionUpdateData, include_extras=True)

        assert "position_id" in hints
        assert hints["position_id"] == int
        assert "position" in hints
        assert hints["position"] == Position
        assert "contract_id" in hints
        assert hints["contract_id"] == str
        assert "size" in hints
        assert hints["size"] == int
        assert "average_price" in hints
        assert hints["average_price"] == float
        assert "type" in hints
        assert hints["type"] == int

        # Optional
        assert "old_position" in hints

    def test_position_closed_data_structure(self):
        """Test PositionClosedData structure."""
        hints = get_type_hints(PositionClosedData, include_extras=True)

        assert "contract_id" in hints
        assert hints["contract_id"] == str
        assert "position" in hints
        assert hints["position"] == Position
        assert "timestamp" in hints

        # Optional P&L
        assert "pnl" in hints

    def test_position_alert_data_structure(self):
        """Test PositionAlertData structure."""
        hints = get_type_hints(PositionAlertData, include_extras=True)

        assert "contract_id" in hints
        assert "message" in hints
        assert hints["message"] == str
        assert "position" in hints
        assert hints["position"] == Position
        assert "alert" in hints

    def test_quote_update_data_structure(self):
        """Test QuoteUpdateData structure."""
        hints = get_type_hints(QuoteUpdateData, include_extras=True)

        assert "contract_id" in hints
        assert hints["contract_id"] == str
        assert "timestamp" in hints

        # Optional quote fields
        assert "bid" in hints
        assert "ask" in hints
        assert "last" in hints
        assert "bid_size" in hints
        assert "ask_size" in hints

    def test_market_trade_data_structure(self):
        """Test MarketTradeData structure."""
        hints = get_type_hints(MarketTradeData, include_extras=True)

        assert "contract_id" in hints
        assert "price" in hints
        assert hints["price"] == float
        assert "size" in hints
        assert hints["size"] == int
        assert "side" in hints
        assert hints["side"] == int
        assert "timestamp" in hints

        # Optional trade ID
        assert "trade_id" in hints

    def test_market_depth_data_structure(self):
        """Test MarketDepthData structure."""
        hints = get_type_hints(MarketDepthData, include_extras=True)

        assert "contract_id" in hints
        assert "bids" in hints
        assert "asks" in hints
        assert "timestamp" in hints

    def test_new_bar_data_structure(self):
        """Test NewBarData structure."""
        hints = get_type_hints(NewBarData, include_extras=True)

        assert "timeframe" in hints
        assert hints["timeframe"] == str
        assert "data" in hints
        assert "timestamp" in hints

    def test_account_update_data_structure(self):
        """Test AccountUpdateData structure."""
        hints = get_type_hints(AccountUpdateData, include_extras=True)

        assert "account_id" in hints
        assert hints["account_id"] == int
        assert "balance" in hints
        assert hints["balance"] == float
        assert "timestamp" in hints

        # Optional fields
        assert "equity" in hints
        assert "margin" in hints

    def test_trade_execution_data_structure(self):
        """Test TradeExecutionData structure."""
        hints = get_type_hints(TradeExecutionData, include_extras=True)

        assert "trade_id" in hints
        assert hints["trade_id"] == int
        assert "order_id" in hints
        assert hints["order_id"] == int
        assert "contract_id" in hints
        assert "price" in hints
        assert hints["price"] == float
        assert "size" in hints
        assert hints["size"] == int
        assert "fees" in hints
        assert hints["fees"] == float

        # Optional P&L
        assert "pnl" in hints

    def test_connection_status_data_structure(self):
        """Test ConnectionStatusData structure."""
        hints = get_type_hints(ConnectionStatusData, include_extras=True)

        assert "hub" in hints
        assert hints["hub"] == str
        assert "connected" in hints
        assert hints["connected"] == bool
        assert "timestamp" in hints

        # Optional error
        assert "error" in hints

    def test_error_data_structure(self):
        """Test ErrorData structure."""
        hints = get_type_hints(ErrorData, include_extras=True)

        assert "error_type" in hints
        assert hints["error_type"] == str
        assert "message" in hints
        assert hints["message"] == str
        assert "timestamp" in hints

        # Optional details
        assert "details" in hints

    def test_system_status_data_structure(self):
        """Test SystemStatusData structure."""
        hints = get_type_hints(SystemStatusData, include_extras=True)

        assert "status" in hints
        assert hints["status"] == str
        assert "timestamp" in hints

        # Optional message
        assert "message" in hints

    def test_real_world_callback_data(self):
        """Test creating callback data with real-world values."""
        # Order update callback
        order_update: OrderUpdateData = {
            "order_id": 12345,
            "status": 2,  # FILLED
            "fill_volume": 5,
            "filled_price": 16500.25,
            "timestamp": "2024-01-01T10:00:00Z",
        }

        assert order_update["order_id"] == 12345
        assert order_update["status"] == 2

        # Position update with model
        position = Position(
            id=67890,
            accountId=1001,
            contractId="CON.F.US.MNQ.U25",
            creationTimestamp="2024-01-01T09:00:00Z",
            type=1,  # LONG
            size=5,
            averagePrice=16500.0,
        )

        position_update: PositionUpdateData = {
            "position_id": 67890,
            "position": position,
            "contract_id": "CON.F.US.MNQ.U25",
            "size": 5,
            "average_price": 16500.0,
            "type": 1,
            "timestamp": "2024-01-01T10:00:00Z",
        }

        assert position_update["position"].size == 5
        assert position_update["position"].is_long

    def test_quote_callback_data(self):
        """Test quote update callback data."""
        # Full quote update
        full_quote: QuoteUpdateData = {
            "contract_id": "CON.F.US.MNQ.U25",
            "bid": 16519.75,
            "bid_size": 10,
            "ask": 16520.00,
            "ask_size": 15,
            "last": 16519.90,
            "last_size": 2,
            "timestamp": "2024-01-01T10:00:00Z",
        }

        assert full_quote["bid"] == 16519.75
        assert full_quote["ask"] == 16520.00
        spread = full_quote["ask"] - full_quote["bid"]
        assert spread == 0.25

        # Partial quote update (only bid/ask)
        partial_quote: QuoteUpdateData = {
            "contract_id": "CON.F.US.MNQ.U25",
            "bid": 16519.75,
            "ask": 16520.00,
            "timestamp": "2024-01-01T10:00:01Z",
        }

        assert "last" not in partial_quote
        assert "bid_size" not in partial_quote

    def test_market_depth_callback_data(self):
        """Test market depth callback data."""
        depth_data: MarketDepthData = {
            "contract_id": "CON.F.US.MNQ.U25",
            "bids": [
                (16519.75, 10),
                (16519.50, 25),
                (16519.25, 50),
            ],
            "asks": [
                (16520.00, 15),
                (16520.25, 30),
                (16520.50, 45),
            ],
            "timestamp": "2024-01-01T10:00:00Z",
        }

        assert len(depth_data["bids"]) == 3
        assert depth_data["bids"][0][0] == 16519.75  # Best bid price
        assert depth_data["bids"][0][1] == 10  # Best bid size

    def test_new_bar_callback_data(self):
        """Test new bar creation callback data."""
        bar_data: NewBarData = {
            "timeframe": "5min",
            "data": {
                "timestamp": "2024-01-01T10:00:00Z",
                "open": 16500.0,
                "high": 16525.0,
                "low": 16495.0,
                "close": 16520.0,
                "volume": 1250,
            },
            "timestamp": "2024-01-01T10:00:00Z",
        }

        assert bar_data["timeframe"] == "5min"
        assert bar_data["data"]["close"] == 16520.0

    def test_error_callback_data(self):
        """Test error callback data."""
        # Connection error
        connection_error: ErrorData = {
            "error_type": "ConnectionError",
            "message": "Failed to connect to market hub",
            "details": {
                "hub": "market",
                "reason": "timeout",
                "retry_count": "3",
            },
            "timestamp": datetime.now().isoformat(),
        }

        assert connection_error["error_type"] == "ConnectionError"
        assert "retry_count" in connection_error["details"]

        # Simple error without details
        simple_error: ErrorData = {
            "error_type": "ValidationError",
            "message": "Invalid order size",
            "timestamp": datetime.now().isoformat(),
        }

        assert "details" not in simple_error

    def test_connection_status_callback_data(self):
        """Test connection status callback data."""
        # Connected status
        connected: ConnectionStatusData = {
            "hub": "user",
            "connected": True,
            "timestamp": datetime.now().isoformat(),
        }

        assert connected["connected"] is True
        assert "error" not in connected

        # Disconnected with error
        disconnected: ConnectionStatusData = {
            "hub": "market",
            "connected": False,
            "error": "Authentication failed",
            "timestamp": datetime.now().isoformat(),
        }

        assert disconnected["connected"] is False
        assert disconnected["error"] == "Authentication failed"

    def test_position_alert_callback_data(self):
        """Test position alert callback data."""
        position = Position(
            id=67890,
            accountId=1001,
            contractId="CON.F.US.MNQ.U25",
            creationTimestamp="2024-01-01T09:00:00Z",
            type=1,  # LONG
            size=5,
            averagePrice=16500.0,
        )

        alert_data: PositionAlertData = {
            "contract_id": "CON.F.US.MNQ.U25",
            "message": "Position breached max loss threshold",
            "position": position,
            "alert": {
                "max_loss": -500.0,
                "current_pnl": -525.50,
                "triggered": True,
                "created": "2024-01-01T09:00:00Z",
            },
        }

        assert alert_data["position"].size == 5
        assert alert_data["alert"]["triggered"] is True
        assert alert_data["alert"]["current_pnl"] < alert_data["alert"]["max_loss"]
