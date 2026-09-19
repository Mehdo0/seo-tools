import asyncio
import json
import csv
import io
from datetime import datetime

from services.url_guard import UnsafeUrlError, check_url

# Ressources dont le contenu n'est jamais lu : les charger ne sert qu'à ralentir la page.
# Les images restent autorisées (certains sites ne renseignent `src` que lorsqu'elles chargent).
BLOCKED_RESOURCE_TYPES = frozenset({"media", "font", "websocket", "manifest"})
ALLOWED_LOCAL_SCHEMES = ("data:", "blob:", "about:")


class ScraperEngine:
    def __init__(self):
        self.browser = None
        self.context = None
        self._lock = asyncio.Lock()
        self._validated_hosts = set()

    async def start(self, headless=True):
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self.browser = await self._pw.chromium.launch(headless=headless)
            self.context = await self.browser.new_context(
                viewport={"width": 1366, "height": 900},
                locale="en-US",
            )
        except Exception:
            raise RuntimeError("Playwright not available. Install with: playwright install chromium")

    async def stop(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if hasattr(self, "_pw"):
            await self._pw.stop()

    async def _guard_requests(self, page):
        """Re-valide chaque requête du navigateur, y compris les redirections.

        La validation faite à l'entrée de l'API ne suffit pas : le navigateur résout les noms
        une seconde fois au moment de la requête (TOCTOU), et une redirection peut viser une
        adresse interne que le contrôle initial n'a jamais vue. Ici la décision est prise au
        moment de la requête, et le nom d'hôte validé est mémorisé pour ne pas refaire une
        résolution DNS à chaque sous-ressource.
        """
        async def handler(route):
            request = route.request
            url = request.url
            if not url.startswith(("http://", "https://")):
                await route.continue_() if url.startswith(ALLOWED_LOCAL_SCHEMES) else await route.abort()
                return
            if request.resource_type in BLOCKED_RESOURCE_TYPES:
                await route.abort()
                return
            host = url.split("/")[2].lower()
            if host not in self._validated_hosts:
                try:
                    check_url(url)
                except UnsafeUrlError:
                    await route.abort()
                    return
                self._validated_hosts.add(host)
            await route.continue_()

        await page.route("**/*", handler)

    async def _new_page(self):
        if not self.browser:
            async with self._lock:
                if not self.browser:
                    await self.start()
        page = await self.context.new_page()
        page.set_default_timeout(30000)
        await self._guard_requests(page)
        return page

    async def scrape_product(self, url, selectors=None):
        page = await self._new_page()
        try:
            # `networkidle` est déconseillé par Playwright et coûte plusieurs secondes sur les
            # pages qui gardent une connexion ouverte : on attend le DOM, puis le sélecteur visé.
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            selectors = selectors or {}
            title_sel = selectors.get("title", "h1")
            price_sel = selectors.get("price", "[data-price], .price, .product-price, span.price")
            desc_sel = selectors.get("description", "[data-description], .description, .product-description")
            image_sel = selectors.get("images", ".product-image img, .gallery img, img[src*='product']")
            variant_sel = selectors.get("variants", "[data-variant], .variant, select option")
            try:
                await page.wait_for_selector(title_sel, timeout=5000)
            except Exception:
                pass
            title = await self._safe_text(page, title_sel)
            price = await self._safe_text(page, price_sel)
            description = await self._safe_text(page, desc_sel)
            images = await self._safe_attrs(page, image_sel, "src")
            variants = await self._safe_all_text(page, variant_sel)
            return {
                "url": page.url or url,
                "title": title,
                "price": price,
                "description": description,
                "images": images,
                "variants": variants,
                "scraped_at": datetime.utcnow().isoformat(),
            }
        finally:
            await page.close()

    async def scrape_competitors(self, urls, selectors=None, concurrency=3):
        """Aspire plusieurs pages en parallèle, avec une borne.

        La boucle séquentielle d'origine coûtait le temps de chargement multiplié par le
        nombre d'URL (jusqu'à cinq minutes pour dix concurrents). Chaque page reste isolée
        dans son onglet, et l'échec d'une URL n'affecte pas les autres.
        """
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def one(url):
            async with semaphore:
                try:
                    product = await self.scrape_product(url, selectors)
                    return {"status": "success", **product}
                except Exception as exc:
                    return {"url": url, "status": "error", "error": str(exc)}

        results = await asyncio.gather(*[one(url) for url in urls])
        return {
            "total": len(urls),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "results": list(results),
        }

    async def price_history(self, url, selectors=None):
        """Relevé de prix : on enregistre le point et on rend l'historique réellement stocké.

        L'implémentation précédente fabriquait une « historique » d'un seul point, celui de
        l'instant, sans jamais rien persister : la fonctionnalité ne pouvait pas répondre à
        la question qu'elle pose (« le prix a-t-il bougé ? »).
        """
        import database

        current = await self.scrape_product(url, selectors)
        price = current.get("price")
        currency = ""
        if price:
            import re
            match = re.search(r"(?:[$€£¥]|EUR|USD|CHF|GBP)", str(price), re.IGNORECASE)
            currency = match.group(0) if match else ""
        database.save_price_point(url, price, currency, current["scraped_at"], current.get("title") or "")
        points = database.get_price_history(url)
        values = [point["price_value"] for point in points if point["price_value"] is not None]
        return {
            "url": url,
            "title": current.get("title"),
            "current_price": price,
            "currency": currency,
            "points": len(points),
            "lowest": min(values) if values else None,
            "highest": max(values) if values else None,
            "history": list(reversed(points)),
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
        """Attributs d'une liste d'éléments.

        `list(set((await el.get_attribute(a)) for el in els if await el.get_attribute(a)))`
        lève TypeError (« async_generator object is not iterable ») : l'exception était
        avalée et la liste revenait donc toujours vide — les images d'un produit scrapé
        n'ont jamais été renvoyées. Boucle explicite, ordre conservé, doublons retirés.
        """
        try:
            elements = await page.query_selector_all(selector)
            values = []
            for element in elements:
                value = await element.get_attribute(attr)
                if value:
                    values.append(value)
            return list(dict.fromkeys(values))[:10]
        except Exception:
            return []

    async def _safe_all_text(self, page, selector):
        try:
            els = await page.query_selector_all(selector)
            return [(await el.text_content()).strip() for el in els]
        except Exception:
            return []


scraper = ScraperEngine()
