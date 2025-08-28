"""
Tests for trading session configuration system.

This test file defines the EXPECTED behavior for trading sessions (ETH/RTH).
Following strict TDD methodology - these tests define the specification,
not the current behavior. Implementation must be changed to match these tests.

Author: TDD Implementation
Date: 2025-08-28
"""

import pytest
from datetime import time, datetime, timezone, timedelta
from typing import Dict, Any

# Note: These imports will fail initially - that's expected in RED phase
from project_x_py.sessions import (
    SessionConfig,
    SessionTimes,
    DEFAULT_SESSIONS,
    SessionType
)


class TestSessionConfig:
    """Test session configuration creation and validation."""

    def test_default_session_config_creation(self):
        """Session config should default to ETH with correct timezone."""
        config = SessionConfig()
        assert config.session_type == SessionType.ETH
        assert config.market_timezone == "America/New_York"
        assert config.use_exchange_timezone is True

    def test_rth_session_config_creation(self):
        """RTH session config should be creatable with correct defaults."""
        config = SessionConfig(session_type=SessionType.RTH)
        assert config.session_type == SessionType.RTH
        assert config.market_timezone == "America/New_York"
        assert config.use_exchange_timezone is True

    def test_custom_timezone_config(self):
        """Should support custom timezone configuration."""
        config = SessionConfig(
            session_type=SessionType.RTH,
            market_timezone="Europe/London",
            use_exchange_timezone=False
        )
        assert config.market_timezone == "Europe/London"
        assert config.use_exchange_timezone is False

    def test_session_config_validation(self):
        """Should validate session configuration parameters."""
        # Invalid timezone should raise ValueError
        with pytest.raises(ValueError, match="Invalid timezone"):
            SessionConfig(market_timezone="Invalid/Timezone")

        # Invalid session type should raise ValueError
        with pytest.raises(ValueError, match="Invalid session type"):
            SessionConfig(session_type="INVALID")


class TestSessionTimes:
    """Test session time definitions and validation."""

    def test_session_times_creation(self):
        """Should create session times with proper validation."""
        times = SessionTimes(
            rth_start=time(9, 30),
            rth_end=time(16, 0),
            eth_start=time(18, 0),
            eth_end=time(17, 0)
        )
        assert times.rth_start == time(9, 30)
        assert times.rth_end == time(16, 0)
        assert times.eth_start == time(18, 0)
        assert times.eth_end == time(17, 0)

    def test_session_times_validation(self):
        """Should validate session times for logical consistency."""
        # ETH start and end must both be provided or both be None
        with pytest.raises(ValueError, match="ETH start and end must both be provided or both be None"):
            SessionTimes(
                rth_start=time(9, 30),
                rth_end=time(16, 0),
                eth_start=time(18, 0),
                eth_end=None  # Only one ETH time provided
            )

    def test_session_overlap_validation(self):
        """Should validate that RTH is contained within ETH."""
        # RTH should be subset of ETH trading hours
        times = SessionTimes(
            rth_start=time(9, 30),
            rth_end=time(16, 0),
            eth_start=time(18, 0),  # Previous day
            eth_end=time(17, 0)     # Current day
        )
        # This should be valid - RTH (9:30-16:00) is within ETH (18:00 prev - 17:00 curr)
        assert times.is_rth_within_eth()


class TestDefaultSessions:
    """Test default session configurations for major products."""

    def test_default_sessions_exist(self):
        """DEFAULT_SESSIONS should contain all major futures products."""
        required_products = ["ES", "NQ", "YM", "RTY", "MNQ", "MES", "CL", "GC", "SI", "ZN"]
        for product in required_products:
            assert product in DEFAULT_SESSIONS, f"Missing session config for {product}"

    def test_equity_index_futures_sessions(self):
        """ES/NQ should have correct RTH times: 9:30 AM - 4:00 PM ET."""
        for product in ["ES", "NQ", "YM", "RTY", "MNQ", "MES"]:
            times = DEFAULT_SESSIONS[product]
            assert times.rth_start == time(9, 30), f"{product} RTH start incorrect"
            assert times.rth_end == time(16, 0), f"{product} RTH end incorrect"
            assert times.eth_start == time(18, 0), f"{product} ETH start incorrect"
            assert times.eth_end == time(17, 0), f"{product} ETH end incorrect"

    def test_commodity_futures_sessions(self):
        """CL should have correct RTH times: 9:00 AM - 2:30 PM ET."""
        times = DEFAULT_SESSIONS["CL"]
        assert times.rth_start == time(9, 0)
        assert times.rth_end == time(14, 30)
        # ETH for commodities typically Sunday 6 PM ET to Friday 5 PM ET
        assert times.eth_start == time(18, 0)
        assert times.eth_end == time(17, 0)

    def test_precious_metals_sessions(self):
        """GC/SI should have correct RTH times: 8:20 AM - 1:30 PM ET."""
        for product in ["GC", "SI"]:
            times = DEFAULT_SESSIONS[product]
            assert times.rth_start == time(8, 20), f"{product} RTH start incorrect"
            assert times.rth_end == time(13, 30), f"{product} RTH end incorrect"

    def test_treasury_futures_sessions(self):
        """ZN should have correct RTH times: 8:20 AM - 3:00 PM ET."""
        times = DEFAULT_SESSIONS["ZN"]
        assert times.rth_start == time(8, 20)
        assert times.rth_end == time(15, 0)


class TestSessionConfigOverrides:
    """Test custom session overrides and product-specific configurations."""

    def test_custom_session_override(self):
        """Custom session times should override defaults."""
        custom_times = SessionTimes(
            rth_start=time(8, 0),
            rth_end=time(15, 0),
            eth_start=time(17, 0),
            eth_end=time(16, 0)
        )
        config = SessionConfig(
            session_type=SessionType.RTH,
            product_sessions={"MNQ": custom_times}
        )
        assert config.product_sessions["MNQ"].rth_start == time(8, 0)
        assert config.product_sessions["MNQ"].rth_end == time(15, 0)

    def test_multiple_product_overrides(self):
        """Should support overrides for multiple products."""
        custom_es = SessionTimes(
            rth_start=time(9, 0),
            rth_end=time(15, 30),
            eth_start=time(17, 30),
            eth_end=time(16, 30)
        )
        custom_cl = SessionTimes(
            rth_start=time(8, 30),
            rth_end=time(14, 0),
            eth_start=time(17, 0),
            eth_end=time(16, 0)
        )

        config = SessionConfig(
            product_sessions={
                "ES": custom_es,
                "CL": custom_cl
            }
        )

        assert config.product_sessions["ES"].rth_start == time(9, 0)
        assert config.product_sessions["CL"].rth_start == time(8, 30)

    def test_fallback_to_defaults(self):
        """Should fall back to defaults for products not in overrides."""
        config = SessionConfig(
            product_sessions={"MNQ": SessionTimes(
                rth_start=time(10, 0),
                rth_end=time(15, 0),
                eth_start=time(18, 0),
                eth_end=time(17, 0)
            )}
        )

        # MNQ should use custom times
        mnq_times = config.get_session_times("MNQ")
        assert mnq_times.rth_start == time(10, 0)

        # ES should use defaults
        es_times = config.get_session_times("ES")
        assert es_times.rth_start == time(9, 30)  # Default for ES


class TestSessionTypeEnum:
    """Test SessionType enumeration."""

    def test_session_type_values(self):
        """SessionType enum should have correct values."""
        assert SessionType.ETH == "ETH"
        assert SessionType.RTH == "RTH"
        assert SessionType.CUSTOM == "CUSTOM"

    def test_session_type_string_conversion(self):
        """Should support string conversion and comparison."""
        assert str(SessionType.ETH) == "ETH"
        assert SessionType.RTH.value == "RTH"

    def test_session_type_from_string(self):
        """Should create SessionType from string values."""
        assert SessionType("ETH") == SessionType.ETH
        assert SessionType("RTH") == SessionType.RTH

        with pytest.raises(ValueError):
            SessionType("INVALID")


class TestSessionConfigMethods:
    """Test SessionConfig utility methods."""

    def test_get_session_times_default(self):
        """get_session_times should return default times for standard products."""
        config = SessionConfig()
        es_times = config.get_session_times("ES")

        # Should return default ES times
        assert es_times.rth_start == time(9, 30)
        assert es_times.rth_end == time(16, 0)

    def test_get_session_times_custom(self):
        """get_session_times should return custom times when overridden."""
        custom_times = SessionTimes(
            rth_start=time(10, 0),
            rth_end=time(15, 0),
            eth_start=time(18, 0),
            eth_end=time(17, 0)
        )
        config = SessionConfig(product_sessions={"ES": custom_times})

        es_times = config.get_session_times("ES")
        assert es_times.rth_start == time(10, 0)

    def test_get_session_times_unknown_product(self):
        """get_session_times should handle unknown products gracefully."""
        config = SessionConfig()

        # Should return generic session times or raise appropriate error
        with pytest.raises(ValueError, match="Unknown product"):
            config.get_session_times("UNKNOWN_PRODUCT")

    def test_is_market_open_method(self):
        """Should provide method to check if market is open."""
        config = SessionConfig(session_type=SessionType.RTH)

        # RTH hours (10 AM ET = 3 PM UTC on trading day)
        trading_time = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)
        assert config.is_market_open(trading_time, "ES") is True

        # Outside RTH hours (7 PM ET = 12 AM UTC next day)
        after_hours = datetime(2024, 1, 16, 0, 0, tzinfo=timezone.utc)
        assert config.is_market_open(after_hours, "ES") is False

    def test_get_current_session_method(self):
        """Should provide method to get current session type."""
        config = SessionConfig(session_type=SessionType.ETH)

        # During RTH hours
        rth_time = datetime(2024, 1, 15, 15, 0, tzinfo=timezone.utc)  # 10 AM ET
        current_session = config.get_current_session(rth_time, "ES")
        assert current_session == "RTH"

        # During overnight hours
        overnight_time = datetime(2024, 1, 16, 2, 0, tzinfo=timezone.utc)  # 9 PM ET
        current_session = config.get_current_session(overnight_time, "ES")
        assert current_session == "ETH"

        # During maintenance break
        maintenance_time = datetime(2024, 1, 15, 22, 30, tzinfo=timezone.utc)  # 5:30 PM ET
        current_session = config.get_current_session(maintenance_time, "ES")
        assert current_session == "BREAK"
