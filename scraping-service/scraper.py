#!/usr/bin/env python3
import argparse
import asyncio
import csv
import json
import os
import random
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class EcommerceScraper:
    def __init__(self, headless=True, timeout=30000, output_dir="scraped_data"):
        self.headless = headless
        self.timeout = timeout
        self.output_dir = output_dir
        self.browser = None
        self.context = None
        os.makedirs(output_dir, exist_ok=True)

    async def _launch_browser(self):
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
        )
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """)

    async def _close_browser(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def _fetch_page(self, url, wait_selector=None):
        if not self.browser:
            await self._launch_browser()
        page = await self.context.new_page()
        try:
            delay = random.uniform(1.5, 4.0)
            await asyncio.sleep(delay)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            if response and response.status >= 400:
                return None, f"HTTP {response.status}"
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    pass
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.5, 1.5))
            content = await page.content()
            return content, None
        except Exception as e:
            return None, str(e)
        finally:
            await page.close()

    def _parse_shopify(self, soup, url):
        data = {}
        title_el = soup.select_one("h1.product-title, h1.product-single__title, h1[data-product-title]")
        if not title_el:
            title_el = soup.find("h1")
        data["title"] = title_el.get_text(strip=True) if title_el else ""

        price_el = soup.select_one("[data-product-price], .product__price, .price__current, .price-item--regular, span.money")
        data["price"] = price_el.get_text(strip=True) if price_el else ""

        desc_el = soup.select_one(".product__description, .product-single__description, [data-product-description]")
        data["description"] = desc_el.get_text(strip=True) if desc_el else ""

        imgs = []
        for img in soup.select("img.product-featured-img, .product-single__photo img, [data-product-featured-image]"):
            src = img.get("src") or img.get("data-src") or ""
            if src and not src.startswith("data:"):
                imgs.append(urljoin(url, src))
        data["images"] = imgs

        variants = []
        for opt in soup.select("select[data-option] option, .variant-option"):
            val = opt.get("value") or opt.get_text(strip=True)
            if val:
                variants.append(val)
        data["variants"] = variants
        data["currency"] = "USD"
        data["platform"] = "shopify"
        return data

    def _parse_woocommerce(self, soup, url):
        data = {}
        title_el = soup.select_one("h1.product_title, h1.entry-title")
        data["title"] = title_el.get_text(strip=True) if title_el else ""

        price_el = soup.select_one(".price .amount, .woocommerce-Price-amount, .summary .price")
        data["price"] = price_el.get_text(strip=True) if price_el else ""

        desc_el = soup.select_one(".woocommerce-product-details__short-description, .woocommerce-Tabs-panel--description")
        data["description"] = desc_el.get_text(strip=True) if desc_el else ""

        imgs = []
        for img in soup.select(".woocommerce-product-gallery__image img, .wp-post-image"):
            src = img.get("src") or img.get("data-src") or ""
            if src and not src.startswith("data:"):
                imgs.append(urljoin(url, src))
        data["images"] = imgs

        variants = []
        for opt in soup.select(".variations select option, .variations_form select option"):
            val = opt.get("value") or opt.get_text(strip=True)
            if val:
                variants.append(val)
        data["variants"] = variants
        data["currency"] = "USD"
        data["platform"] = "woocommerce"
        return data

    def _parse_amazon(self, soup, url):
        data = {}
        title_el = soup.select_one("#productTitle")
        data["title"] = title_el.get_text(strip=True) if title_el else ""

        price_whole = soup.select_one(".a-price-whole")
        price_fraction = soup.select_one(".a-price-fraction")
        if price_whole:
            price = price_whole.get_text(strip=True)
            if price_fraction:
                price += "." + price_fraction.get_text(strip=True)
            currency_el = soup.select_one(".a-price-symbol")
            data["currency"] = currency_el.get_text(strip=True) if currency_el else "USD"
        else:
            price_el = soup.select_one("#priceblock_ourprice, .a-price .a-offscreen")
            price = price_el.get_text(strip=True) if price_el else ""
            data["currency"] = "USD"
        data["price"] = price

        desc_el = soup.select_one("#productDescription, #feature-bullets")
        data["description"] = desc_el.get_text(strip=True)[:500] if desc_el else ""

        imgs = []
        img_el = soup.select_one("#landingImage, #imgTagWrapperId img")
        if img_el:
            src = img_el.get("src") or img_el.get("data-old-hires") or ""
            if src and not src.startswith("data:"):
                imgs.append(urljoin(url, src))
        data["images"] = imgs

        variants = []
        for opt in soup.select("#variation_size_name .a-size-base, .swatchSelect"):
            val = opt.get_text(strip=True)
            if val:
                variants.append(val)
        data["variants"] = variants
        data["platform"] = "amazon"
        return data

    def _parse_generic(self, soup, url):
        data = {}
        title_el = soup.find("h1")
        data["title"] = title_el.get_text(strip=True) if title_el else ""

        price_patterns = [
            ".price", ".product-price", "[data-price]", ".current-price",
            ".sales-price", ".offer-price", "[itemprop='price']",
            "meta[property='product:price:amount']", ".price--main"
        ]
        price = ""
        for pat in price_patterns:
            el = soup.select_one(pat)
            if el:
                price = el.get("content") or el.get_text(strip=True)
                if price:
                    break
        data["price"] = price

        desc_patterns = [".product-description", "[itemprop='description']", ".description",
                         "#description", ".product-details"]
        desc = ""
        for pat in desc_patterns:
            el = soup.select_one(pat)
            if el:
                desc = el.get_text(strip=True)[:500]
                break
        data["description"] = desc

        imgs = []
        seen = set()
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if src and not src.startswith("data:") and src not in seen:
                full = urljoin(url, src)
                if any(kw in full.lower() for kw in ["product", "main", "large", "zoom"]):
                    imgs.insert(0, full)
                elif len(imgs) < 10:
                    imgs.append(full)
                seen.add(src)
        data["images"] = imgs[:10]

        data["variants"] = []
        data["currency"] = "USD"
        data["platform"] = "generic"
        return data

    def _detect_platform(self, soup, url):
        html = str(soup).lower()
        if "shopify" in html or "myshopify" in url:
            return "shopify"
        if "woocommerce" in html or "wp-content" in html:
            return "woocommerce"
        if "amazon" in urlparse(url).netloc:
            return "amazon"
        return "generic"

    async def scrape_product(self, url):
        content, error = await self._fetch_page(url)
        if error:
            return {"url": url, "error": error, "scraped_at": datetime.now().isoformat()}

        soup = BeautifulSoup(content, "lxml")
        platform = self._detect_platform(soup, url)

        parsers = {
            "shopify": self._parse_shopify,
            "woocommerce": self._parse_woocommerce,
            "amazon": self._parse_amazon,
            "generic": self._parse_generic,
        }
        data = parsers[platform](soup, url)
        data["url"] = url
        data["scraped_at"] = datetime.now().isoformat()
        return data

    async def scrape_collection(self, url, max_items=50):
        content, error = await self._fetch_page(url)
        if error:
            return {"url": url, "error": error, "products": []}

        soup = BeautifulSoup(content, "lxml")
        product_links = []

        link_selectors = [
            "a[href*='/products/']", "a[href*='/product/']",
            "a.product-link", "a.product__link", ".product-card a",
            "a.woocommerce-LoopProduct-link", "h2.product-title a",
            ".product-item__title a", "a.product-item-link",
            ".s-result-item a.a-link-normal[href*='/dp/']",
        ]
        seen = set()
        for selector in link_selectors:
            for a in soup.select(selector):
                href = a.get("href", "")
                if href and "/product" in href and href not in seen:
                    full = urljoin(url, href)
                    seen.add(href)
                    product_links.append(full)
                    if len(product_links) >= max_items:
                        break
            if len(product_links) >= max_items:
                break

        products = []
        for i, link in enumerate(product_links[:max_items]):
            try:
                product = await self.scrape_product(link)
                products.append(product)
                await asyncio.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                products.append({"url": link, "error": str(e)})
        return {"url": url, "total_found": len(product_links), "products": products}

    async def compare_prices(self, product_urls):
        results = []
        for url in product_urls:
            data = await self.scrape_product(url)
            results.append(data)
            await asyncio.sleep(random.uniform(1.0, 2.0))
        return results

    async def monitor_price(self, url, interval_hours=24):
        data = await self.scrape_product(url)
        filename = f"{self.output_dir}/price_history_{hash(url)}.json"

        history = []
        if os.path.exists(filename):
            with open(filename) as f:
                history = json.load(f)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "price": data.get("price", ""),
            "title": data.get("title", ""),
        }
        history.append(entry)

        with open(filename, "w") as f:
            json.dump(history, f, indent=2)

        alerts = []
        if len(history) >= 2:
            try:
                prev_price = float(history[-2]["price"].replace("$", "").replace(",", ""))
                curr_price = float(history[-1]["price"].replace("$", "").replace(",", ""))
                if curr_price < prev_price:
                    drop_pct = ((prev_price - curr_price) / prev_price) * 100
                    alerts.append(f"Price dropped {drop_pct:.1f}% from ${prev_price:.2f} to ${curr_price:.2f}")
            except (ValueError, KeyError):
                pass

        return {"url": url, "entry": entry, "history": history, "alerts": alerts}

    def export_json(self, data, filename):
        filepath = f"{self.output_dir}/{filename}"
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return filepath

    def export_csv(self, data, filename):
        filepath = f"{self.output_dir}/{filename}"
        if isinstance(data, list) and len(data) > 0:
            keys = data[0].keys()
            with open(filepath, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
        elif isinstance(data, dict):
            flat = []
            for key, val in data.items():
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict):
                            flat.append(item)
            if flat:
                keys = flat[0].keys()
                with open(filepath, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=keys)
                    writer.writeheader()
                    writer.writerows(flat)
        return filepath


async def main():
    parser = argparse.ArgumentParser(description="E-commerce Scraping Engine")
    parser.add_argument("--url", required=True, help="Product or collection URL to scrape")
    parser.add_argument("--mode", default="product", choices=["product", "collection", "compare", "monitor"],
                        help="Scraping mode")
    parser.add_argument("--max-items", type=int, default=50, help="Max items for collection mode")
    parser.add_argument("--output", default="scraped_data", help="Output directory")
    parser.add_argument("--format", default="json", choices=["json", "csv", "both"], help="Output format")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Show browser")
    parser.add_argument("--compare-urls", nargs="*", help="URLs to compare prices (for compare mode)")

    args = parser.parse_args()

    scraper = EcommerceScraper(headless=args.headless, output_dir=args.output)

    try:
        if args.mode == "product":
            result = await scraper.scrape_product(args.url)
            print(json.dumps(result, indent=2))

        elif args.mode == "collection":
            result = await scraper.scrape_collection(args.url, max_items=args.max_items)
            if args.format in ("csv", "both"):
                scraper.export_csv(result["products"], "collection_products.csv")
            if args.format in ("json", "both"):
                scraper.export_json(result, "collection_products.json")
            print(json.dumps({"total": result["total_found"], "scraped": len(result["products"])}, indent=2))

        elif args.mode == "compare":
            urls = args.compare_urls or [args.url]
            result = await scraper.compare_prices(urls)
            if args.format in ("csv", "both"):
                scraper.export_csv(result, "price_comparison.csv")
            if args.format in ("json", "both"):
                scraper.export_json(result, "price_comparison.json")
            print(json.dumps(result, indent=2))

        elif args.mode == "monitor":
            result = await scraper.monitor_price(args.url)
            print(json.dumps(result, indent=2))

    finally:
        await scraper._close_browser()


if __name__ == "__main__":
    asyncio.run(main())
