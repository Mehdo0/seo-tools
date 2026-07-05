#!/usr/bin/env python3
import argparse
import csv
import json
import os
import time
from datetime import datetime, timedelta

from scraper import EcommerceScraper


class ProductMonitor:
    def __init__(self, data_dir="price_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def _product_key(self, url):
        return str(abs(hash(url)))

    def track(self, url, label=None):
        key = self._product_key(url)
        filepath = f"{self.data_dir}/{key}.json"

        history = []
        if os.path.exists(filepath):
            with open(filepath) as f:
                history = json.load(f)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "label": label or url,
        }
        history.append(entry)
        return filepath, history, entry

    def save_track(self, filepath, history):
        with open(filepath, "w") as f:
            json.dump(history, f, indent=2)

    async def check_now(self, url, label=None, threshold=None):
        filepath, history, entry = self.track(url, label)
        scraper = EcommerceScraper(headless=True, output_dir=self.data_dir)
        try:
            data = await scraper.scrape_product(url)
            entry["price"] = data.get("price", "")
            entry["title"] = data.get("title", "")
            entry["error"] = data.get("error", "")
        except Exception as e:
            entry["error"] = str(e)
        finally:
            await scraper._close_browser()

        self.save_track(filepath, history)

        alerts = self.check_alerts(history, threshold)
        return {"url": url, "entry": entry, "history": history, "alerts": alerts}

    def check_alerts(self, history, threshold=None):
        alerts = []
        prices = []
        for entry in history:
            try:
                p = entry.get("price", "").replace("$", "").replace(",", "").replace("€", "").replace("£", "")
                prices.append(float(p))
            except (ValueError, TypeError):
                continue

        if len(prices) >= 2:
            prev = prices[-2]
            curr = prices[-1]
            if curr < prev:
                pct = ((prev - curr) / prev) * 100
                alerts.append(f"Price dropped {pct:.1f}%: ${prev:.2f} -> ${curr:.2f}")
            elif curr > prev:
                pct = ((curr - prev) / prev) * 100
                alerts.append(f"Price increased {pct:.1f}%: ${prev:.2f} -> ${curr:.2f}")

        if threshold and prices:
            curr = prices[-1]
            if curr <= threshold:
                alerts.append(f"Price ${curr:.2f} at or below threshold ${threshold:.2f}")

        return alerts

    def generate_chart(self, url, output_file=None):
        key = self._product_key(url)
        filepath = f"{self.data_dir}/{key}.json"

        if not os.path.exists(filepath):
            return "No data available."

        with open(filepath) as f:
            history = json.load(f)

        timestamps = []
        prices = []
        for entry in history:
            try:
                p = float(entry.get("price", "").replace("$", "").replace(",", "").replace("€", "").replace("£", ""))
                ts = entry.get("timestamp", "")
                prices.append(p)
                timestamps.append(ts[:10])
            except (ValueError, TypeError):
                continue

        if not prices:
            return "No price data available."

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            plt.figure(figsize=(10, 5))
            plt.plot(timestamps, prices, marker="o", linewidth=2, markersize=6)
            plt.xlabel("Date")
            plt.ylabel("Price ($)")
            plt.title(f"Price History: {history[0].get('label', url)[:60]}")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.grid(True, alpha=0.3)

            out = output_file or f"{self.data_dir}/chart_{key}.png"
            plt.savefig(out, dpi=100)
            plt.close()
            return out
        except ImportError:
            return self._ascii_chart(timestamps, prices)

    def _ascii_chart(self, timestamps, prices):
        if len(prices) < 2:
            return "Need at least 2 data points for chart."

        height = 15
        width = 60
        min_p = min(prices) * 0.95
        max_p = max(prices) * 1.05
        price_range = max_p - min_p or 1

        lines = []
        lines.append(f"Price History ({timestamps[0]} -> {timestamps[-1]})")
        lines.append(f"Min: ${min(prices):.2f}  Max: ${max(prices):.2f}")
        lines.append("-" * width)

        chart = [[" " for _ in range(len(prices))] for _ in range(height)]
        for x, price in enumerate(prices):
            y = int((price - min_p) / price_range * (height - 1))
            chart[height - 1 - y][x] = "*"

        for row in chart:
            lines.append("".join(row))
        lines.append("-" * width)
        return "\n".join(lines)

    def export_csv(self, url, output_file=None):
        key = self._product_key(url)
        filepath = f"{self.data_dir}/{key}.json"

        if not os.path.exists(filepath):
            return None

        with open(filepath) as f:
            history = json.load(f)

        out = output_file or f"{self.data_dir}/history_{key}.csv"
        with open(out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "price", "title", "error"])
            writer.writeheader()
            for entry in history:
                writer.writerow({
                    "timestamp": entry.get("timestamp", ""),
                    "price": entry.get("price", ""),
                    "title": entry.get("title", ""),
                    "error": entry.get("error", ""),
                })
        return out


async def main():
    parser = argparse.ArgumentParser(description="Product Price Monitor")
    parser.add_argument("--url", required=True, help="Product URL to monitor")
    parser.add_argument("--label", help="Product label for reports")
    parser.add_argument("--threshold", type=float, help="Alert when price drops below this value")
    parser.add_argument("--chart", action="store_true", help="Generate price history chart")
    parser.add_argument("--csv", help="Export to CSV file")
    parser.add_argument("--data-dir", default="price_data", help="Data directory")

    args = parser.parse_args()

    monitor = ProductMonitor(data_dir=args.data_dir)
    result = await monitor.check_now(args.url, label=args.label, threshold=args.threshold)

    print(json.dumps({
        "url": result["url"],
        "price": result["entry"].get("price", "N/A"),
        "title": result["entry"].get("title", "N/A"),
        "alerts": result["alerts"],
        "history_points": len(result["history"]),
    }, indent=2))

    if args.chart:
        chart_out = monitor.generate_chart(args.url)
        if chart_out:
            print(f"\nChart saved: {chart_out}")

    if args.csv:
        csv_out = monitor.export_csv(args.url, output_file=args.csv)
        if csv_out:
            print(f"CSV exported: {csv_out}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
