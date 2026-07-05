# E-Commerce Scraping Engine

Professional Playwright-based scraping engine for e-commerce price monitoring, product data extraction, and competitor analysis. Designed to be sold as a freelance service.

## Features

- **Multi-platform**: Shopify, WooCommerce, Amazon, and generic store support
- **Anti-bot bypass**: Rotating user agents, request delays, browser fingerprint evasion
- **JS rendering**: Full Playwright browser automation for dynamic content
- **Price monitoring**: Track price changes over time with alerts
- **Export**: JSON, CSV, and professional HTML client reports
- **CLI-first**: Fully usable from command line for easy automation

## Installation

```bash
cd scraping-service
pip install -r requirements.txt
playwright install chromium
```

## Quick Start

### Scrape a single product

```bash
python scraper.py --url "https://example.com/products/widget" --mode product
```

### Scrape a collection/category page

```bash
python scraper.py --url "https://example.com/collections/all" --mode collection --max-items 20 --format both
```

### Compare prices across stores

```bash
python scraper.py --mode compare \
  --compare-urls "https://store1.com/product" "https://store2.com/product" "https://store3.com/product" \
  --format both
```

### Monitor a product price

```bash
python product_monitor.py --url "https://example.com/products/widget" --threshold 49.99 --chart
```

### Run with visible browser (debug mode)

```bash
python scraper.py --url "https://example.com/product" --no-headless
```

## Output

All data is saved to `scraped_data/` (configurable with `--output`):

```
scraped_data/
├── collection_products.json     # Full collection data
├── collection_products.csv      # CSV export
├── price_comparison.json        # Cross-store comparison
├── price_comparison.csv         # CSV export
└── price_history_<hash>.json    # Price history per product
```

## Pricing Guide (Freelance Service)

| Tier | Price | Includes |
|------|-------|----------|
| **Starter** | $199/mo | 10 products, weekly checks, CSV exports |
| **Professional** | $499/mo | 50 products, daily checks, HTML reports, price alerts |
| **Enterprise** | $999/mo | 250+ products, hourly checks, competitor matrix, API access |

### One-time projects

- **Market analysis**: $499 — 50 products across 10 competitors
- **Migration audit**: $799 — Full catalog extraction + data mapping
- **Price intelligence setup**: $1,499 — Custom dashboard + alert configuration

## Architecture

```
scraping-service/
├── scraper.py              # Core scraping engine (Playwright + BS4)
├── product_monitor.py      # Price tracking + alerts + charts
├── templates/
│   └── report.html         # Client-ready HTML report template
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

### Key Classes

**EcommerceScraper** (`scraper.py`)
- `scrape_product(url)` — Extract title, price, images, description, variants
- `scrape_collection(url, max_items=50)` — Paginate and scrape category pages
- `compare_prices(product_urls)` — Cross-store price comparison
- `monitor_price(url, interval_hours=24)` — Track price over time

**ProductMonitor** (`product_monitor.py`)
- `check_now(url, threshold)` — Immediate price check with alerts
- `generate_chart(url)` — Price history chart (PNG or ASCII)
- `export_csv(url)` — Export price history to CSV

## Anti-Bot Techniques

- Rotating user-agent pool (Chrome, Firefox, Safari, Edge)
- Randomized request delays (1.5-4.0 seconds)
- Browser fingerprint evasion (webdriver, plugins, languages, chrome.runtime)
- Geolocation and timezone spoofing
- Scroll behavior simulation

## Platform Detection

The engine auto-detects the store platform:

- **Shopify**: Detected via `myshopify` in URL or Shopify-specific HTML markers
- **WooCommerce**: Detected via `woocommerce` or `wp-content` markers
- **Amazon**: Detected via domain name
- **Generic**: Falls back to intelligent meta/structured data extraction

## Limitations

- Cloudflare-protected sites may block automated access
- CAPTCHA challenges require manual intervention
- Rate limiting — built-in delays help but aggressive scraping may trigger blocks
- Some stores use JavaScript price obfuscation

## Requirements

- Python 3.9+
- Playwright (Chromium)
- Dependencies in `requirements.txt`
