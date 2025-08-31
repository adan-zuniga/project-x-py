import asyncio

from project_x_py import TradingSuite
from project_x_py.indicators import RSI, SMA


async def main():
    # V3.5: Multi-instrument TradingSuite for advanced strategies
    suite = await TradingSuite.create(
        instruments=["MNQ", "ES", "MGC"],  # Multiple instruments
        timeframes=["1min", "5min"],
        features=["orderbook", "risk_manager"],
        initial_days=30,
    )

    # Access specific instruments
    mnq_context = suite["MNQ"]
    es_context = suite["ES"]
    mgc_context = suite["MGC"]

    # Get market data with technical analysis
    print("\n📊 Loading historical data and calculating indicators for MNQ...")
    print(
        f"MNQ: {mnq_context.instrument_info.symbolId} from Multi-Instrument TradingSuite"
    )
    mnq_data = await mnq_context.data.get_data("1min")
    if mnq_data is None:
        raise Exception("No data available")

    mnq_data = mnq_data.pipe(RSI, period=14).pipe(SMA, period=20)

    # Display latest indicator values
    if not mnq_data.is_empty():
        print(f"Total bars for MNQ: {len(mnq_data)}")
        latest = mnq_data.row(-1)
        print("\nMNQ Latest Bar:")
        print(f"  Time: {latest[0]}")  # timestamp
        print(f"  Close: ${latest[4]:.2f}")  # close
        if "rsi_14" in mnq_data.columns:
            print(f"  RSI(14): {latest[mnq_data.columns.index('rsi_14')]:.2f}")
        if "sma_20" in mnq_data.columns:
            print(f"  SMA(20): ${latest[mnq_data.columns.index('sma_20')]:.2f}")

    print("\n📊 Loading historical data and calculating indicators for ES...")
    print(
        f"ES: {es_context.instrument_info.symbolId} from Multi-Instrument TradingSuite"
    )
    es_data = await es_context.data.get_data("1min")
    if es_data is None:
        raise Exception("No data available")

    es_data = es_data.pipe(RSI, period=14).pipe(SMA, period=20)

    if not es_data.is_empty():
        print(f"Total bars for ES: {len(es_data)}")
        latest = es_data.row(-1)
        print("\nES Latest Bar:")
        print(f"  Time: {latest[0]}")  # timestamp
        print(f"  Close: ${latest[4]:.2f}")  # close

        if "rsi_14" in es_data.columns:
            print(f"  RSI(14): {latest[es_data.columns.index('rsi_14')]:.2f}")
        if "sma_20" in es_data.columns:
            print(f"  SMA(20): ${latest[es_data.columns.index('sma_20')]:.2f}")

    print("\n📊 Loading historical data and calculating indicators for MGC...")
    print(
        f"MGC: {mgc_context.instrument_info.symbolId} from Multi-Instrument TradingSuite"
    )
    mgc_data = await mgc_context.data.get_data("1min")
    if mgc_data is None:
        raise Exception("No data available")

    mgc_data = mgc_data.pipe(RSI, period=14).pipe(SMA, period=20)

    if not mgc_data.is_empty():
        print(f"Total bars for MGC: {len(mgc_data)}")
        latest = mgc_data.row(-1)
        print("\nMGC Latest Bar:")
        print(f"  Time: {latest[0]}")  # timestamp
        print(f"  Close: ${latest[4]:.2f}")  # close

        if "rsi_14" in mgc_data.columns:
            print(f"  RSI(14): {latest[mgc_data.columns.index('rsi_14')]:.2f}")
        if "sma_20" in mgc_data.columns:
            print(f"  SMA(20): ${latest[mgc_data.columns.index('sma_20')]:.2f}")

    # Portfolio-level analytics - show last known prices
    print("\n💼 Portfolio Overview:")
    for symbol in suite.keys():  # Just iterate over symbols, not context
        try:
            # Get historical data for each instrument (use more days to ensure we have data)
            bars = await suite.client.get_bars(symbol, days=5, interval=60)
            if not bars.is_empty():
                last_close = bars.row(-1)[4]  # Get last close price
                last_time = bars.row(-1)[0]  # Get timestamp
                print(f"  {symbol}: ${last_close:.2f} (last close at {last_time})")
            else:
                print(f"  {symbol}: No recent data available")
        except Exception as e:
            print(f"  {symbol}: Error getting data - {e}")

    await suite.disconnect()
    print("\n✅ Example completed successfully!")


# Run the async function
asyncio.run(main())
