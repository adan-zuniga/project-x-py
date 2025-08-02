"""
Test suite for Utility Functions
"""

from datetime import datetime

import polars as pl

from project_x_py.indicators import (
    ATR,
    BBANDS,
    EMA,
    MACD,
    RSI,
    SMA,
)
from project_x_py.utils import (
    calculate_position_value,
    extract_symbol_from_contract_id,
    format_price,
    round_to_tick_size,
    validate_contract_id,
)


class TestTechnicalAnalysis:
    """Test cases for technical analysis functions"""

    def test_calculate_sma(self):
        """Test Simple Moving Average calculation"""
        # Arrange
        data = pl.DataFrame(
            {
                "close": [
                    100.0,
                    101.0,
                    102.0,
                    103.0,
                    104.0,
                    105.0,
                    106.0,
                    107.0,
                    108.0,
                    109.0,
                ]
            }
        )

        # Act
        sma_indicator = SMA(period=5)
        result = sma_indicator(data)
        sma = result["sma"]

        # Assert
        assert len(sma) == len(data)
        # First 4 values should be null
        assert sma[:4].is_null().sum() == 4
        # 5th value should be average of first 5: (100+101+102+103+104)/5 = 102
        assert sma[4] == 102.0
        # Last value should be average of last 5: (105+106+107+108+109)/5 = 107
        assert sma[9] == 107.0

    def test_calculate_ema(self):
        """Test Exponential Moving Average calculation"""
        # Arrange
        data = pl.DataFrame(
            {
                "close": [
                    100.0,
                    101.0,
                    102.0,
                    103.0,
                    104.0,
                    105.0,
                    106.0,
                    107.0,
                    108.0,
                    109.0,
                ]
            }
        )

        # Act
        ema_indicator = EMA(period=5)
        result = ema_indicator(data)
        ema = result["ema"]

        # Assert
        assert len(ema) == len(data)
        # First value should equal the close price
        assert ema[0] == 100.0
        # EMA should be smoother than price, last value should be less than 109
        assert ema[9] < 109.0
        assert ema[9] > 105.0  # But higher than 5 bars ago

    def test_calculate_rsi(self):
        """Test Relative Strength Index calculation"""
        # Arrange
        # Create data with clear up and down moves
        prices = [
            100,
            102,
            101,
            103,
            105,
            104,
            106,
            108,
            107,
            109,
            111,
            110,
            112,
            114,
            113,
        ]
        data = pl.DataFrame({"close": prices})

        # Act
        rsi_indicator = RSI(period=14)
        result = rsi_indicator(data)
        rsi = result["rsi"]

        # Assert
        assert len(rsi) == len(data)
        # First 14 values should be null
        assert rsi[:14].is_null().sum() == 14
        # RSI should be between 0 and 100
        non_null_rsi = rsi[14:]
        assert all(0 <= val <= 100 for val in non_null_rsi if val is not None)

    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        # Arrange
        data = pl.DataFrame(
            {
                "close": [
                    100.0,
                    101.0,
                    99.0,
                    102.0,
                    98.0,
                    103.0,
                    97.0,
                    104.0,
                    96.0,
                    105.0,
                ]
                * 3
            }
        )

        # Act
        bb_indicator = BBANDS(period=20, std_dev=2.0)
        bb = bb_indicator(data)

        # Assert
        assert "upper_band" in bb.columns
        assert "lower_band" in bb.columns
        assert "middle_band" in bb.columns

        # Check relationships
        idx = 25  # Check after enough data
        assert bb["upper_band"][idx] > bb["middle_band"][idx]
        assert bb["middle_band"][idx] > bb["lower_band"][idx]

    def test_calculate_macd(self):
        """Test MACD calculation"""
        # Arrange
        # Create trending data
        trend_data = [100 + i * 0.5 for i in range(50)]
        data = pl.DataFrame({"close": trend_data})

        # Act
        macd_indicator = MACD(fast_period=12, slow_period=26, signal_period=9)
        macd = macd_indicator(data)

        # Assert
        assert "macd" in macd.columns
        assert "signal" in macd.columns
        assert "histogram" in macd.columns

        # In an uptrend, MACD should be positive after enough bars
        assert macd["macd"][45] > 0

    def test_calculate_atr(self):
        """Test Average True Range calculation"""
        # Arrange
        data = pl.DataFrame(
            {
                "high": [105, 107, 106, 108, 110, 109, 111, 113, 112, 114],
                "low": [100, 102, 101, 103, 105, 104, 106, 108, 107, 109],
                "close": [102, 105, 103, 106, 108, 107, 109, 111, 110, 112],
            }
        )

        # Act
        atr_indicator = ATR(period=5)
        result = atr_indicator(data)
        atr = result["atr"]

        # Assert
        assert len(atr) == len(data)
        # ATR should be positive
        non_null_atr = [val for val in atr if val is not None]
        assert all(val > 0 for val in non_null_atr)


class TestUtilityFunctions:
    """Test cases for utility functions"""

    def test_format_price(self):
        """Test price formatting"""
        # Act & Assert
        assert format_price(2045.75) == "2045.75"
        assert format_price(2045.0) == "2045.00"
        assert format_price(2045.123456) == "2045.12"  # Should round to 2 decimals

    def test_validate_contract_id(self):
        """Test contract ID validation"""
        # Act & Assert
        assert validate_contract_id("CON.F.US.MGC.M25") is True
        assert validate_contract_id("CON.F.US.MES.H25") is True
        assert validate_contract_id("invalid_contract") is False
        assert validate_contract_id("CON.F.US") is False  # Too few parts
        assert validate_contract_id("") is False

    def test_extract_symbol_from_contract_id(self):
        """Test symbol extraction from contract ID"""
        # Act & Assert
        assert extract_symbol_from_contract_id("CON.F.US.MGC.M25") == "MGC"
        assert extract_symbol_from_contract_id("CON.F.US.MES.H25") == "MES"
        assert extract_symbol_from_contract_id("invalid") is None
        assert extract_symbol_from_contract_id("") is None

    def test_round_to_tick_size(self):
        """Test price rounding to tick size"""
        # Act & Assert
        # Test with tick size 0.1
        assert round_to_tick_size(2045.23, 0.1) == 2045.2
        assert round_to_tick_size(2045.27, 0.1) == 2045.3
        assert round_to_tick_size(2045.25, 0.1) == 2045.3  # Round up on .5

        # Test with tick size 0.25
        assert round_to_tick_size(5400.10, 0.25) == 5400.00
        assert round_to_tick_size(5400.30, 0.25) == 5400.25
        assert round_to_tick_size(5400.60, 0.25) == 5400.50
        assert round_to_tick_size(5400.90, 0.25) == 5401.00

    def test_calculate_position_value(self):
        """Test position value calculation"""
        # Act & Assert
        # Long position
        value = calculate_position_value(
            quantity=5,
            entry_price=2045.0,
            current_price=2050.0,
            tick_value=10.0,
            tick_size=0.1,
        )
        # 5 contracts * (2050-2045) / 0.1 * 10 = 5 * 50 * 10 = 2500
        assert value == 2500.0

        # Short position (negative quantity)
        value = calculate_position_value(
            quantity=-3,
            entry_price=5400.0,
            current_price=5395.0,
            tick_value=5.0,
            tick_size=0.25,
        )
        # -3 contracts * (5395-5400) / 0.25 * 5 = -3 * -20 * 5 = 300
        assert value == 300.0
