import asyncio
import signal
from datetime import datetime
from pathlib import Path

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("⚠️ Plotly not installed. Charts will not be generated.")

from project_x_py import TradingSuite
from project_x_py.event_bus import EventType

TIMEFRAME = "15sec"


def create_candlestick_chart(bars_data, instrument: str, timeframe: str, filename: str):
    """Create a candlestick chart from bar data using Plotly"""
    if not PLOTLY_AVAILABLE:
        return False

    try:
        # Convert Polars DataFrame to dict for easier access
        data_dict = bars_data.to_dict()

        # Create figure with secondary y-axis for volume
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f"{instrument} - {timeframe} Candlestick Chart", "Volume"),
            row_heights=[0.7, 0.3],
        )

        # Add candlestick chart with proper price formatting
        fig.add_trace(
            go.Candlestick(
                x=data_dict["timestamp"],
                open=data_dict["open"],
                high=data_dict["high"],
                low=data_dict["low"],
                close=data_dict["close"],
                name="OHLC",
                increasing_line_color="green",
                decreasing_line_color="red",
            ),
            row=1,
            col=1,
        )

        # Add volume bars
        colors = [
            "green" if close >= open_ else "red"
            for close, open_ in zip(data_dict["close"], data_dict["open"], strict=False)
        ]

        fig.add_trace(
            go.Bar(
                x=data_dict["timestamp"],
                y=data_dict["volume"],
                name="Volume",
                marker_color=colors,
                showlegend=False,
                hovertemplate="<b>%{x}</b><br>"
                + "Volume: %{y:,}<br>"
                + "<extra></extra>",
            ),
            row=2,
            col=1,
        )

        # Update layout
        fig.update_layout(
            title=f"{instrument} - Last {bars_data.height} {timeframe} Bars",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=800,
            showlegend=False,
        )

        # Update y-axes with proper formatting
        fig.update_yaxes(
            title_text="Price ($)",
            row=1,
            col=1,
            tickformat="$,.2f",  # Format y-axis ticks as currency with 2 decimals
        )
        fig.update_yaxes(title_text="Volume", row=2, col=1, tickformat=",")

        # Generate HTML filename
        html_filename = filename.replace(".csv", ".html")

        # Save the chart
        fig.write_html(html_filename)

        print(f"📈 Candlestick chart saved to {html_filename}")

        # Also try to open in browser (optional)
        try:
            import webbrowser

            webbrowser.open(f"file://{Path(html_filename).absolute()}")
            print("📊 Chart opened in browser")
        except Exception:
            pass  # Silently fail if browser can't be opened

        return True

    except Exception as e:
        print(f"⚠️ Could not create chart: {e}")
        return False


async def export_bars_to_csv(
    suite: TradingSuite, timeframe: str, bars_count: int = 100
):
    """Export the last N bars to a CSV file"""
    try:
        # Get the last 100 bars
        bars_data = await suite["NQ"].data.get_data(timeframe=timeframe, bars=bars_count)

        if bars_data is None or bars_data.is_empty():
            print("No data available to export.")
            return False

        if suite["NQ"].instrument_info is None:
            print("Suite instrument is None, skipping chart creation")
            return True

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bars_export_{suite['NQ'].instrument_info.name}_{timeframe}_{timestamp}.csv"
        filepath = Path(filename)

        # Write to CSV
        bars_data.write_csv(filepath)

        print(f"\n✅ Successfully exported {bars_data.height} bars to {filename}")

        if suite["NQ"].instrument_info is None:
            print("Suite instrument is None, skipping chart creation")
            return True

        # Create candlestick chart
        create_candlestick_chart(bars_data, suite["NQ"].instrument_info.name, timeframe, filename)

        return True

    except Exception as e:
        print(f"❌ Error exporting data: {e}")
        return False


async def prompt_for_csv_export(suite, timeframe: str):
    """Prompt user to export CSV in a non-blocking way"""
    print("\n" + "=" * 80)
    print("📊 10 new bars have been received!")
    print(
        "Would you like to export the last 100 bars to CSV and generate a candlestick chart?"
    )
    print("Type 'y' or 'yes' to export, or press Enter to continue monitoring...")
    print("=" * 80)

    # Create a task to wait for user input without blocking
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    def handle_input():
        try:
            # Non-blocking input using asyncio
            response = input().strip().lower()
            future.set_result(response)
        except Exception as e:
            future.set_exception(e)

    # Run input in executor to avoid blocking
    loop.run_in_executor(None, handle_input)

    try:
        # Wait for input with a timeout
        response = await asyncio.wait_for(future, timeout=10.0)

        if response in ["y", "yes"]:
            await export_bars_to_csv(suite, timeframe)
            return True
    except TimeoutError:
        print("\nNo response received. Continuing to monitor...")
    except Exception as e:
        print(f"\nError handling input: {e}")

    return False


async def main():
    print("Creating TradingSuite...")
    # Note: Use "MNQ" for Micro E-mini Nasdaq-100 futures
    # "NQ" resolves to E-mini Nasdaq (ENQ) which may have different data characteristics
    suite = await TradingSuite.create(
        "NQ",  # Works best with MNQ for consistent real-time updates
        timeframes=[TIMEFRAME],
    )
    print("TradingSuite created!")

    # No need to call connect() - it's already connected via auto_connect=True
    print("Suite is already connected!")

    # Set up signal handler for clean exit
    shutdown_event = asyncio.Event()

    # Bar counter
    bar_counter = {"count": 0, "export_prompted": False}

    def signal_handler(_signum, _frame):
        print("\n\nReceived interrupt signal. Shutting down gracefully...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Define the event handler as an async function
    async def on_new_bar(event):
        """Handle new bar events"""
        # Increment bar counter
        bar_counter["count"] += 1

        print(f"\n📊 New bar #{bar_counter['count']} received")

        try:
            current_price = await suite["NQ"].data.get_current_price()
        except Exception as e:
            print(f"Error getting current price: {e}")
            return

        try:
            last_bars = await suite["NQ"].data.get_data(timeframe=TIMEFRAME, bars=6)
        except Exception as e:
            print(f"Error getting data: {e}")
            return

        print(f"Current price: ${current_price:,.2f}")
        print("=" * 80)

        if last_bars is not None and not last_bars.is_empty():
            print("Last 6 bars (oldest to newest):")
            print("Oldest bar is first, current bar is last")
            print("-" * 80)

            # Get the last 5 bars and iterate through them
            for row in last_bars.tail(6).iter_rows(named=True):
                timestamp = row["timestamp"]
                open_price = row["open"]
                high = row["high"]
                low = row["low"]
                close = row["close"]
                volume = row["volume"]

                print(
                    f"Time: {timestamp} | O: ${open_price:,.2f} | H: ${high:,.2f} | L: ${low:,.2f} | C: ${close:,.2f} | Vol: {volume:,}"
                )
        else:
            print("No bar data available yet")

        # Check if we should prompt for CSV export
        if bar_counter["count"] == 10 and not bar_counter["export_prompted"]:
            bar_counter["export_prompted"] = True
            # Run the prompt in a separate task to avoid blocking
            asyncio.create_task(prompt_for_csv_export(suite, TIMEFRAME))

        # Reset the prompt flag after 20 bars so it can prompt again
        if bar_counter["count"] >= 20:
            bar_counter["count"] = 0
            bar_counter["export_prompted"] = False

    # Register the event handler
    print("About to register event handler...")
    await suite.on(EventType.NEW_BAR, on_new_bar)
    print("Event handler registered!")

    print(f"\nMonitoring {suite['NQ'].instrument_info.name} {TIMEFRAME} bars. Press CTRL+C to exit.")
    print("📊 CSV export and chart generation will be prompted after 10 new bars.")
    print("Event handler registered and waiting for new bars...\n")

    try:
        # Keep the program running
        while not shutdown_event.is_set():
            await asyncio.sleep(1)
    finally:
        print("Disconnecting from real-time feeds...")
        await suite.disconnect()
        print("Clean shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
