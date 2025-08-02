"""Unit tests for order_manager.utils."""

from unittest.mock import MagicMock

import pytest

from project_x_py.order_manager import utils


class TestAlignPriceToTick:
    """Tests for align_price_to_tick utility."""

    def test_aligns_up(self):
        """Price rounds to nearest tick size (upwards)."""
        assert utils.align_price_to_tick(100.07, 0.1) == 100.1

    def test_aligns_down(self):
        """Price rounds to nearest tick size (downwards)."""
        assert utils.align_price_to_tick(99.92, 0.25) == 100.0

    def test_zero_tick_size(self):
        """Returns price unchanged if tick size is zero."""
        assert utils.align_price_to_tick(50.0, 0.0) == 50.0

    def test_negative_tick_size(self):
        """Returns price unchanged if tick size is negative."""
        assert utils.align_price_to_tick(50.0, -1.0) == 50.0


@pytest.mark.asyncio
async def test_align_price_to_tick_size_returns_input(monkeypatch):
    """Patch get_instrument to always return tickSize=0.5; should align price to 100.0."""

    class DummyClient:
        async def get_instrument(self, contract_id):
            class Instrument:
                tickSize = 0.5

            return Instrument()

    price = await utils.align_price_to_tick_size(100.2, "MGC", DummyClient())
    assert price == 100.0


@pytest.mark.asyncio
async def test_align_price_to_tick_size_price_none():
    """Returns None if price is None."""
    result = await utils.align_price_to_tick_size(None, "MGC", MagicMock())
    assert result is None


@pytest.mark.asyncio
async def test_align_price_to_tick_size_handles_missing_instrument(monkeypatch):
    """Returns original price if instrument lookup fails."""

    class DummyClient:
        async def get_instrument(self, contract_id):
            return None

    price = await utils.align_price_to_tick_size(101.5, "FOO", DummyClient())
    assert price == 101.5


@pytest.mark.asyncio
async def test_resolve_contract_id(monkeypatch):
    """resolve_contract_id fetches instrument and returns expected dict."""

    class DummyInstrument:
        id = "X"
        name = "X"
        tickSize = 0.1
        tickValue = 1.0
        activeContract = True

    class DummyClient:
        async def get_instrument(self, contract_id):
            return DummyInstrument()

    result = await utils.resolve_contract_id("X", DummyClient())
    assert result == {
        "id": "X",
        "name": "X",
        "tickSize": 0.1,
        "tickValue": 1.0,
        "activeContract": True,
    }


@pytest.mark.asyncio
async def test_resolve_contract_id_handles_missing(monkeypatch):
    """Returns None if instrument not found."""

    class DummyClient:
        async def get_instrument(self, contract_id):
            return None

    assert await utils.resolve_contract_id("X", DummyClient()) is None
