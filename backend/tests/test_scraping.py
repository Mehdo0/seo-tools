import pytest
from unittest.mock import patch, AsyncMock


class TestScrapingProduct:
    def test_scrape_product_authenticated(self, client, auth_headers, mock_scraper):
        resp = client.post("/api/scraping/product", json={
            "url": "https://example.com/product",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Product"
        assert data["price"] == "$99.99"
        assert data["url"] == "https://example.com/product"

    def test_scrape_product_unauthenticated(self, client):
        resp = client.post("/api/scraping/product", json={
            "url": "https://example.com/product",
        })
        assert resp.status_code == 401

    def test_scrape_product_missing_url(self, client, auth_headers):
        resp = client.post("/api/scraping/product", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_scrape_product_with_selectors(self, client, auth_headers, mock_scraper):
        resp = client.post("/api/scraping/product", json={
            "url": "https://example.com/product",
            "selectors": {"title": ".custom-title", "price": ".custom-price"},
        }, headers=auth_headers)
        assert resp.status_code == 200

    def test_scrape_product_invalid_url(self, client, auth_headers, mock_scraper):
        resp = client.post("/api/scraping/product", json={
            "url": "not-a-valid-url",
        }, headers=auth_headers)
        assert resp.status_code == 200

    def test_scrape_product_scraper_error(self, client, auth_headers):
        with patch("services.scraper_engine.scraper.scrape_product", new_callable=AsyncMock) as mock:
            mock.side_effect = RuntimeError("Browser not available")
            resp = client.post("/api/scraping/product", json={
                "url": "https://example.com/product",
            }, headers=auth_headers)
            assert resp.status_code == 500
            assert "Browser not available" in resp.json()["detail"]


class TestScrapingCompetitors:
    def test_scrape_competitors_authenticated(self, client, auth_headers, mock_scraper):
        resp = client.post("/api/scraping/competitors", json={
            "urls": ["https://example.com/1", "https://example.com/2"],
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["successful"] == 2
        assert len(data["results"]) == 2

    def test_scrape_competitors_unauthenticated(self, client):
        resp = client.post("/api/scraping/competitors", json={
            "urls": ["https://example.com/1"],
        })
        assert resp.status_code == 401

    def test_scrape_competitors_empty_urls(self, client, auth_headers):
        resp = client.post("/api/scraping/competitors", json={
            "urls": [],
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "no urls" in resp.json()["detail"].lower()

    def test_scrape_competitors_too_many_urls(self, client, auth_headers):
        urls = [f"https://example.com/{i}" for i in range(11)]
        resp = client.post("/api/scraping/competitors", json={
            "urls": urls,
        }, headers=auth_headers)
        assert resp.status_code == 400
        assert "max 10" in resp.json()["detail"].lower()

    def test_scrape_competitors_missing_urls(self, client, auth_headers):
        resp = client.post("/api/scraping/competitors", json={}, headers=auth_headers)
        assert resp.status_code == 422


class TestPriceHistory:
    def test_price_history_authenticated(self, client, auth_headers, mock_scraper):
        resp = client.post("/api/scraping/price-history", json={
            "url": "https://example.com/product",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com/product"
        assert data["current_price"] == "$99.99"
        assert "history" in data

    def test_price_history_unauthenticated(self, client):
        resp = client.post("/api/scraping/price-history", json={
            "url": "https://example.com/product",
        })
        assert resp.status_code == 401


class TestExport:
    def test_export_json_authenticated(self, client, auth_headers, mock_scraper):
        resp = client.post("/api/scraping/export", json={
            "data": [{"name": "item1", "price": 10}],
            "format": "json",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "json"

    def test_export_csv_authenticated(self, client, auth_headers, mock_scraper):
        resp = client.post("/api/scraping/export", json={
            "data": [{"name": "item1", "price": 10}],
            "format": "csv",
        }, headers=auth_headers)
        assert resp.status_code == 200

    def test_export_unauthenticated(self, client):
        resp = client.post("/api/scraping/export", json={
            "data": [{"name": "test"}],
            "format": "json",
        })
        assert resp.status_code == 401


class TestRateLimiting:
    @pytest.mark.skip(reason="Rate limiter mocked at session scope for test isolation")
    def test_rate_limit_applied(self, client):
        responses = []
        for _ in range(65):
            resp = client.get("/api/health")
            responses.append(resp.status_code)
        assert 429 in responses
