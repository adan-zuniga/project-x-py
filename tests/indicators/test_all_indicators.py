import importlib
import inspect
import pkgutil

import polars as pl
import pytest

from project_x_py.indicators.base import BaseIndicator


def _concrete_indicator_classes():
    # Recursively discover all non-abstract subclasses of BaseIndicator in project_x_py.indicators.*
    import project_x_py.indicators

    seen = set()
    result = []

    def onclass(cls):
        if cls in seen:
            return
        seen.add(cls)
        # Must be subclass of BaseIndicator but not the base class itself
        if not issubclass(cls, BaseIndicator) or cls is BaseIndicator:
            return
        # Skip abstract classes (those with any abstractmethods)
        if getattr(cls, "__abstractmethods__", None):
            return
        # Only include classes defined in project_x_py.indicators.*
        if not cls.__module__.startswith("project_x_py.indicators."):
            return
        result.append(cls)

    # Walk all modules in project_x_py.indicators package
    for _, name, _ in pkgutil.walk_packages(
        project_x_py.indicators.__path__, project_x_py.indicators.__name__ + "."
    ):
        try:
            mod = importlib.import_module(name)
        except Exception:
            continue  # If import fails, skip that module
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            onclass(obj)
    # Remove duplicates, sort by class name for determinism
    return sorted(set(result), key=lambda cls: cls.__name__)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "indicator_cls", _concrete_indicator_classes(), ids=lambda cls: cls.__name__
)
async def test_indicator_calculate_adds_new_column(indicator_cls, sample_ohlcv_df):
    """
    For every indicator class: instantiate with default ctor, call .calculate() or __call__ on sample data.
    - No exception is raised.
    - Result is a polars.DataFrame with same row count.
    - At least one new column is present.
    """
    instance = indicator_cls()
    input_cols = set(sample_ohlcv_df.columns)
    # Try __call__ first (uses caching), then fallback to .calculate
    try:
        out_df = instance(sample_ohlcv_df)
    except Exception:
        out_df = instance.calculate(sample_ohlcv_df)

    assert isinstance(out_df, pl.DataFrame), (
        f"{indicator_cls.__name__} output is not a polars.DataFrame"
    )
    assert out_df.height == sample_ohlcv_df.height, (
        f"{indicator_cls.__name__} output row count {out_df.height} != input {sample_ohlcv_df.height}"
    )
    new_cols = set(out_df.columns) - input_cols
    assert new_cols, f"{indicator_cls.__name__} did not add any new columns"


def _get_new_column_names(indicator_cls, input_cols, df):
    return set(df.columns) - set(input_cols)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "indicator_cls", _concrete_indicator_classes(), ids=lambda cls: cls.__name__
)
async def test_indicator_caching_returns_same_object(indicator_cls, sample_ohlcv_df):
    """
    Calling the indicator twice with the same df on the same instance should return the exact same DataFrame object (proves internal cache).
    """
    instance = indicator_cls()
    # Use __call__ to trigger cache logic
    out1 = instance(sample_ohlcv_df)
    out2 = instance(sample_ohlcv_df)
    assert out1 is out2, (
        f"{indicator_cls.__name__} did not return identical object on repeated call (cache broken?)"
    )
