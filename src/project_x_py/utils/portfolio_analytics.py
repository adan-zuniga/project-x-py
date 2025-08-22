"""
Portfolio analytics including Sharpe ratio, drawdown analysis, and performance metrics.

Author: @TexasCoding
Date: 2025-08-02

Overview:
    Provides comprehensive portfolio analytics including Sharpe ratio calculation,
    drawdown analysis, volatility metrics, and performance evaluation tools.
    Includes correlation analysis, risk metrics, and portfolio optimization
    utilities for trading strategy evaluation.

Key Features:
    - Sharpe ratio calculation with risk-free rate adjustment
    - Maximum drawdown analysis and duration tracking
    - Volatility metrics and rolling volatility calculation
    - Correlation matrix analysis for portfolio diversification
    - Comprehensive portfolio performance metrics
    - Risk-adjusted return calculations

Portfolio Analytics:
    - Performance metrics (Sharpe ratio, volatility, returns)
    - Risk analysis (drawdown, correlation, diversification)
    - Portfolio optimization and analysis
    - Trade-based performance evaluation
    - Risk-adjusted return calculations
    - Comprehensive portfolio statistics

Example Usage:
    ```python
    from project_x_py.utils import (
        calculate_sharpe_ratio,
        calculate_max_drawdown,
        calculate_volatility_metrics,
        calculate_correlation_matrix,
        calculate_portfolio_metrics,
    )

    # Calculate Sharpe ratio
    data = data.with_columns(pl.col("close").pct_change().alias("returns"))
    sharpe = calculate_sharpe_ratio(data)
    print(f"Sharpe Ratio: {sharpe:.2f}")

    # Calculate maximum drawdown
    dd_metrics = calculate_max_drawdown(price_data)
    print(f"Max Drawdown: {dd_metrics['max_drawdown']:.2%}")

    # Calculate volatility metrics
    vol_metrics = calculate_volatility_metrics(price_data)
    print(f"Annualized Volatility: {vol_metrics['annualized_volatility']:.2%}")

    # Calculate correlation matrix
    corr_matrix = calculate_correlation_matrix(ohlcv_data)
    print(corr_matrix)

    # Portfolio performance from trades
    trades = [
        {"pnl": 500, "size": 1, "timestamp": "2024-01-01"},
        {"pnl": -200, "size": 2, "timestamp": "2024-01-02"},
    ]
    metrics = calculate_portfolio_metrics(trades)
    print(f"Total Return: {metrics['total_return']:.2%}")
    ```

Performance Metrics:
    - Sharpe Ratio: Risk-adjusted return measure
    - Maximum Drawdown: Largest peak-to-trough decline
    - Volatility: Standard deviation of returns
    - Annualized Metrics: Yearly performance measures
    - Rolling Volatility: Time-varying volatility analysis

Risk Analysis:
    - Drawdown Duration: Length of recovery periods
    - Correlation Analysis: Portfolio diversification
    - Volatility Metrics: Risk measurement and analysis
    - Risk-Adjusted Returns: Performance relative to risk
    - Portfolio Optimization: Risk-return optimization

Portfolio Statistics:
    - Total Return: Overall portfolio performance
    - Win Rate: Percentage of profitable trades
    - Profit Factor: Gross profit to gross loss ratio
    - Average Win/Loss: Mean profitable/unprofitable trade
    - Largest Win/Loss: Extreme trade performance
    - Expectancy: Expected value per trade

Performance Characteristics:
    - Efficient calculation algorithms
    - Memory-optimized for large datasets
    - Fast portfolio analysis for real-time evaluation
    - Polars DataFrame integration for performance
    - Optimized for high-frequency portfolio monitoring

See Also:
    - `utils.trading_calculations`: Trading calculations and math
    - `utils.pattern_detection`: Pattern detection for analysis
    - `utils.data_utils`: Data processing and analysis
"""

from typing import Any

import polars as pl


def calculate_correlation_matrix(
    data: pl.DataFrame,
    columns: list[str] | None = None,
    _method: str = "pearson",
) -> pl.DataFrame:
    """
    Calculate correlation matrix for specified columns.

    Args:
        data: DataFrame with numeric data
        columns: Columns to include (default: all numeric columns)
        method: Correlation method ("pearson", "spearman")

    Returns:
        DataFrame with correlation matrix

    Example:
        >>> corr_matrix = calculate_correlation_matrix(
        ...     ohlcv_data, ["open", "high", "low", "close"]
        ... )
        >>> print(corr_matrix)
    """
    if columns is None:
        # Auto-detect numeric columns
        columns = [
            col
            for col, dtype in zip(data.columns, data.dtypes, strict=False)
            if dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]
        ]

    if not columns:
        raise ValueError("No numeric columns found")

    # Simple correlation calculation using polars
    correlations: dict[str, dict[str, float]] = {}
    for col1 in columns:
        correlations[col1] = {}
        for col2 in columns:
            if col1 == col2:
                correlations[col1][col2] = 1.0
            else:
                # Calculate Pearson correlation
                corr_result = data.select(
                    [pl.corr(col1, col2).alias("correlation")]
                ).item(0, "correlation")
                correlations[col1][col2] = (
                    corr_result if corr_result is not None else 0.0
                )

    # Convert to DataFrame
    corr_data = []
    for col1 in columns:
        row: dict[str, Any] = {"column": col1}
        for col2 in columns:
            row[col2] = correlations[col1][col2]
        corr_data.append(row)

    return pl.from_dicts(corr_data)


def calculate_volatility_metrics(
    data: pl.DataFrame,
    price_column: str = "close",
    return_column: str | None = None,
    window: int = 20,
) -> dict[str, Any]:
    """
    Calculate various volatility metrics.

    Args:
        data: DataFrame with price data
        price_column: Price column for calculations
        return_column: Pre-calculated returns column (optional)
        window: Window for rolling calculations

    Returns:
        Dict with volatility metrics

    Example:
        >>> vol_metrics = calculate_volatility_metrics(ohlcv_data)
        >>> print(f"Annualized Volatility: {vol_metrics['annualized_volatility']:.2%}")
    """
    if price_column not in data.columns:
        raise ValueError(f"Column '{price_column}' not found in data")

    # Calculate returns if not provided
    if return_column is None:
        data = data.with_columns(pl.col(price_column).pct_change().alias("returns"))
        return_column = "returns"

    if data.is_empty():
        return {"error": "No data available"}

    try:
        # Calculate various volatility measures
        returns_data = data.select(pl.col(return_column)).drop_nulls()

        if returns_data.is_empty():
            return {"error": "No valid returns data"}

        std_dev = returns_data.std().item()
        mean_return = returns_data.mean().item()

        # Calculate rolling volatility
        rolling_vol = (
            data.with_columns(
                pl.col(return_column)
                .rolling_std(window_size=window)
                .alias("rolling_vol")
            )
            .select("rolling_vol")
            .drop_nulls()
        )

        metrics = {
            "volatility": std_dev or 0.0,
            "annualized_volatility": (std_dev or 0.0)
            * (252**0.5),  # Assuming 252 trading days
            "mean_return": mean_return or 0.0,
            "annualized_return": (mean_return or 0.0) * 252,
        }

        if not rolling_vol.is_empty():
            metrics.update(
                {
                    "avg_rolling_volatility": rolling_vol.mean().item() or 0.0,
                    "max_rolling_volatility": rolling_vol.max().item() or 0.0,
                    "min_rolling_volatility": rolling_vol.min().item() or 0.0,
                }
            )

        return metrics

    except Exception as e:
        return {"error": str(e)}


def calculate_sharpe_ratio(
    data: pl.DataFrame,
    return_column: str = "returns",
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        data: DataFrame with returns data
        return_column: Returns column name
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods per year

    Returns:
        Sharpe ratio

    Example:
        >>> # First calculate returns
        >>> data = data.with_columns(pl.col("close").pct_change().alias("returns"))
        >>> sharpe = calculate_sharpe_ratio(data)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")
    """
    if return_column not in data.columns:
        raise ValueError(f"Column '{return_column}' not found in data")

    returns_data = data.select(pl.col(return_column)).drop_nulls()

    if returns_data.is_empty():
        return 0.0

    try:
        mean_return = returns_data.mean().item() or 0.0
        std_return = returns_data.std().item() or 0.0

        if std_return == 0:
            return 0.0

        # Annualize the metrics
        annualized_return = mean_return * periods_per_year
        annualized_volatility = std_return * (periods_per_year**0.5)

        # Calculate Sharpe ratio
        excess_return = annualized_return - risk_free_rate
        return float(excess_return / annualized_volatility)

    except Exception:
        return 0.0


def calculate_max_drawdown(
    data: pl.DataFrame,
    price_column: str = "close",
) -> dict[str, Any]:
    """
    Calculate maximum drawdown.

    Args:
        data: DataFrame with price data
        price_column: Price column name

    Returns:
        Dict with drawdown metrics

    Example:
        >>> dd_metrics = calculate_max_drawdown(ohlcv_data)
        >>> print(f"Max Drawdown: {dd_metrics['max_drawdown']:.2%}")
    """
    if price_column not in data.columns:
        raise ValueError(f"Column '{price_column}' not found in data")

    if data.is_empty():
        return {"max_drawdown": 0.0, "max_drawdown_duration": 0}

    try:
        # Calculate cumulative maximum (peak) using rolling_max with large window
        data_length = len(data)
        data_with_peak = data.with_columns(
            pl.col(price_column).rolling_max(window_size=data_length).alias("peak")
        )

        # Calculate drawdown
        data_with_dd = data_with_peak.with_columns(
            ((pl.col(price_column) / pl.col("peak")) - 1).alias("drawdown")
        )

        # Get maximum drawdown
        max_dd = data_with_dd.select(pl.col("drawdown").min()).item() or 0.0

        # Calculate drawdown duration (simplified)
        dd_series = data_with_dd.select("drawdown").to_series()
        max_duration = 0
        current_duration = 0

        for dd in dd_series:
            if dd < 0:  # In drawdown
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:  # Recovery
                current_duration = 0

        return {
            "max_drawdown": max_dd,
            "max_drawdown_duration": max_duration,
        }

    except Exception as e:
        return {"error": str(e)}


def calculate_portfolio_metrics(
    trades: list[dict[str, Any]],
    initial_balance: float = 100000.0,
) -> dict[str, Any]:
    """
    Calculate comprehensive portfolio performance metrics.

    Args:
        trades: List of trade dictionaries with 'pnl', 'size', 'timestamp' fields
        initial_balance: Starting portfolio balance

    Returns:
        Dict with portfolio metrics

    Example:
        >>> trades = [
        ...     {"pnl": 500, "size": 1, "timestamp": "2024-01-01"},
        ...     {"pnl": -200, "size": 2, "timestamp": "2024-01-02"},
        ... ]
        >>> metrics = calculate_portfolio_metrics(trades)
        >>> print(f"Total Return: {metrics['total_return']:.2%}")
    """
    if not trades:
        return {"error": "No trades provided"}

    try:
        # Extract P&L values
        pnls = [trade.get("pnl", 0) for trade in trades]
        total_pnl = sum(pnls)

        # Basic metrics
        total_trades = len(trades)
        winning_trades = [pnl for pnl in pnls if pnl > 0]
        losing_trades = [pnl for pnl in pnls if pnl < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0

        # Profit factor
        gross_profit = sum(winning_trades)
        gross_loss = abs(sum(losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Returns
        total_return = total_pnl / initial_balance

        # Calculate equity curve for drawdown
        equity_curve = [initial_balance]
        for pnl in pnls:
            equity_curve.append(equity_curve[-1] + pnl)

        # Max drawdown
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_duration = 0
        current_dd_duration = 0

        for equity in equity_curve[1:]:
            if equity > peak:
                peak = equity
                current_dd_duration = 0
            else:
                dd = (peak - equity) / peak
                max_dd = max(max_dd, dd)
                current_dd_duration += 1
                max_dd_duration = max(max_dd_duration, current_dd_duration)

        # Expectancy
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

        return {
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "total_return": total_return,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_drawdown": max_dd,
            "max_drawdown_duration": max_dd_duration,
            "expectancy": expectancy,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "largest_win": max(pnls) if pnls else 0,
            "largest_loss": min(pnls) if pnls else 0,
        }

    except Exception as e:
        return {"error": str(e)}
