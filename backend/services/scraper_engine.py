import asyncio
import json
import csv
import io
from datetime import datetime

class ScraperEngine:
    def __init__(self):
        self.browser = None
        self.context = None
        self._lock = asyncio.Lock()

    async def start(self, headless=True):
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self.browser = await self._pw.chromium.launch(headless=headless)
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        except Exception:
            raise RuntimeError("Playwright not available. Install with: playwright install chromium")

    async def stop(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if hasattr(self, "_pw"):
            await self._pw.stop()

    async def scrape_product(self, url, selectors=None):
        if not self.browser:
            async with self._lock:
                if not self.browser:
                    await self.start()
        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            selectors = selectors or {}
            title_sel = selectors.get("title", "h1")
            price_sel = selectors.get("price", "[data-price], .price, .product-price, span.price")
            desc_sel = selectors.get("description", "[data-description], .description, .product-description")
            image_sel = selectors.get("images", ".product-image img, .gallery img, img[src*='product']")
            variant_sel = selectors.get("variants", "[data-variant], .variant, select option")
            title = await self._safe_text(page, title_sel)
            price = await self._safe_text(page, price_sel)
            description = await self._safe_text(page, desc_sel)
            images = await self._safe_attrs(page, image_sel, "src")
            variants = await self._safe_all_text(page, variant_sel)
            return {
                "url": url,
                "title": title,
                "price": price,
                "description": description,
                "images": images,
                "variants": variants,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        finally:
            await page.close()

    async def scrape_competitors(self, urls, selectors=None):
        results = []
        for url in urls:
            try:
                product = await self.scrape_product(url, selectors)
                results.append({"status": "success", **product})
            except Exception as e:
                results.append({"url": url, "status": "error", "error": str(e)})
        return {
            "total": len(urls),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "results": results,
        }

    async def price_history(self, url, selectors=None):
        current = await self.scrape_product(url, selectors)
        return {
            "url": url,
            "current_price": current.get("price"),
            "title": current.get("title"),
            "history": [{"price": current.get("price"), "date": datetime.utcnow().isoformat()}],
        }

    async def export_data(self, data, fmt="json"):
        if fmt == "csv":
            output = io.StringIO()
            if isinstance(data, dict) and "results" in data:
                data = data["results"]
            if not data:
                return ""
            if isinstance(data, list):
                fieldnames = list(data[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            return output.getvalue()
        return json.dumps(data, indent=2, default=str)

    async def _safe_text(self, page, selector):
        try:
            el = await page.query_selector(selector)
            if el:
                return (await el.text_content()).strip()
        except Exception:
            pass
        return None

    async def _safe_attrs(self, page, selector, attr):
        try:
            els = await page.query_selector_all(selector)
            return list(set(
                (await el.get_attribute(attr))
                for el in els
                if await el.get_attribute(attr)
            ))[:10]
        except Exception:
            return []

    async def _safe_all_text(self, page, selector):
        try:
            els = await page.query_selector_all(selector)
            return [(await el.text_content()).strip() for el in els]
        except Exception:
            return []


scraper = ScraperEngine()
