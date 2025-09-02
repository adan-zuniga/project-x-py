#!/usr/bin/env python
"""
Real-time data export with CSV logging and Plotly visualization
"""

import asyncio
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from project_x_py import EventType, TradingSuite


class RealTimeDataExporter:
    def __init__(self, suite: TradingSuite, export_dir: str = "data_exports"):
        self.suite = suite
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)

        # Data storage
        self.tick_data = []
        self.bar_data = []
        self.trade_data = []

        # File handles
        self.csv_files = {}
        self.export_interval = 60  # Export every 60 seconds

    async def initialize_export_files(self):
        """Initialize CSV files for data export."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Bar data CSV
        bar_file = self.export_dir / f"bars_{timestamp}.csv"
        bar_csv = open(bar_file, "w", newline="")
        bar_writer = csv.writer(bar_csv)
        bar_writer.writerow(
            ["timestamp", "timeframe", "open", "high", "low", "close", "volume"]
        )
        self.csv_files["bars"] = {"file": bar_csv, "writer": bar_writer}

        print(f"Export files initialized in {self.export_dir}")

    async def process_bar(self, event):
        """Process and export bar data."""
        timestamp = datetime.now().isoformat()

        # Get the real data for the timeframe
        # Data from the event is from the new bar that was just started, so we need to get the previous bar
        real_data = await self.suite["MNQ"].data.get_data(
            event.data.get("timeframe", "unknown")
        )

        if real_data is None:
            return

        # Store in memory
        bar_record = {
            "timestamp": timestamp,
            "bar_timestamp": real_data["timestamp"][-2],
            "timeframe": event.data.get("timeframe", "unknown"),
            "open": real_data["open"][-2],
            "high": real_data["high"][-2],
            "low": real_data["low"][-2],
            "close": real_data["close"][-2],
            "volume": real_data["volume"][-2],
        }

        self.bar_data.append(bar_record)

        # Write to CSV
        if "bars" in self.csv_files:
            writer = self.csv_files["bars"]["writer"]
            writer.writerow(
                [
                    bar_record["bar_timestamp"] or timestamp,
                    bar_record["timeframe"],
                    bar_record["open"],
                    bar_record["high"],
                    bar_record["low"],
                    bar_record["close"],
                    bar_record["volume"],
                ]
            )
            self.csv_files["bars"]["file"].flush()

        print(f"Exported {bar_record['timeframe']} bar: ${bar_record['close']:.2f}")

    async def export_json_snapshot(self):
        """Export current data snapshot as JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        snapshot = {
            "export_timestamp": datetime.now().isoformat(),
            "data_summary": {
                "bar_count": len(self.bar_data),
            },
            "recent_data": {
                "bars": self.bar_data[-5:],  # Last 5 bars
            },
        }

        json_file = self.export_dir / f"snapshot_{timestamp}.json"
        with open(json_file, "w") as f:
            json.dump(snapshot, f, indent=2)

        print(f"JSON snapshot exported: {json_file}")
        return json_file

    def close_files(self):
        """Close all open CSV files."""
        for file_info in self.csv_files.values():
            file_info["file"].close()
        print("Export files closed")


async def main():
    # Create suite for data export
    suite = await TradingSuite.create(
        "MNQ", timeframes=["15sec", "1min", "5min"], initial_days=1
    )

    mnq_context = suite["MNQ"]

    exporter = RealTimeDataExporter(suite)
    await exporter.initialize_export_files()

    # Event handlers
    await suite.on(EventType.NEW_BAR, exporter.process_bar)

    print("Real-time Data Exporter Active")
    print(f"Exporting to: {exporter.export_dir}")
    print("Streaming data...")

    try:
        export_timer = 0

        while True:
            await asyncio.sleep(10)
            export_timer += 10

            # Periodic status
            current_price = await mnq_context.data.get_current_price()
            if current_price is None:
                continue

            print(f"Price: ${current_price:.2f} | Bars: {len(exporter.bar_data)}")

            # Auto-export JSON snapshot every 5 minutes
            if export_timer >= 300:  # 5 minutes
                await exporter.export_json_snapshot()
                export_timer = 0

    except KeyboardInterrupt:
        print("\nShutting down data exporter...")

        # Final exports
        print("Creating final exports...")
        await exporter.export_json_snapshot()

        # Close files
        exporter.close_files()

        print("Data export complete!")


if __name__ == "__main__":
    asyncio.run(main())
