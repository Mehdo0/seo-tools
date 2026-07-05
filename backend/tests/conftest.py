import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

os.environ.setdefault("RATE_LIMIT_REQUESTS", "999999")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def app():
    from main import app
    return app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    import time
    resp = client.post("/api/auth/register", json={
        "email": f"test_{time.time()}@example.com",
        "password": "password123",
        "name": "Test User",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_stripe():
    with patch("stripe.checkout.Session") as mock_session:
        mock_session.create.return_value = MagicMock(
            url="https://checkout.stripe.com/test",
            id="cs_test_123",
        )
        yield mock_session


@pytest.fixture
def mock_scraper():
    from api import scraping as _scraping
    with patch.object(_scraping, "scraper") as mock:
        mock.scrape_product = AsyncMock(return_value={
            "url": "https://example.com/product",
            "title": "Test Product",
            "price": "$99.99",
            "description": "A great product",
            "images": ["https://example.com/img1.jpg"],
            "variants": ["Small", "Medium", "Large"],
            "scraped_at": "2024-01-01T00:00:00",
        })
        mock.scrape_competitors = AsyncMock(return_value={
            "total": 2,
            "successful": 2,
            "results": [
                {"status": "success", "url": "https://example.com/1", "title": "Product 1", "price": "$10"},
                {"status": "success", "url": "https://example.com/2", "title": "Product 2", "price": "$20"},
            ],
        })
        mock.price_history = AsyncMock(return_value={
            "url": "https://example.com/product",
            "current_price": "$99.99",
            "title": "Test Product",
            "history": [{"price": "$99.99", "date": "2024-01-01T00:00:00"}],
        })
        mock.export_data = AsyncMock(return_value='{"exported": true}')
        yield mock


@pytest.fixture
def real_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Ultimate Guide to SEO Optimization in 2024</title>
    <meta name="description" content="Learn the best SEO practices for 2024. This comprehensive guide covers on-page optimization, technical SEO, and link building strategies.">
    <meta property="og:title" content="Ultimate SEO Guide 2024">
    <meta property="og:description" content="Comprehensive SEO guide covering all aspects of search engine optimization.">
    <meta property="og:image" content="https://example.com/og-image.jpg">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="SEO Guide 2024">
    <meta name="twitter:description" content="Master SEO in 2024 with our complete guide.">
    <meta name="twitter:image" content="https://example.com/twitter-image.jpg">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://example.com/seo-guide-2024">
</head>
<body>
    <h1>Welcome to SEO Mastery</h1>
    <p>Search engine optimization is crucial for online success. In this guide, we will explore the most effective strategies for ranking higher in search results.</p>
    <p>Keyword research is the foundation of any successful SEO campaign. Understanding what your audience searches for helps create targeted content.</p>
    <h2>On-Page Optimization</h2>
    <p>On-page optimization involves optimizing individual web pages to rank higher. This includes title tags, meta descriptions, and header tags.</p>
    <h2>Technical SEO</h2>
    <p>Technical SEO focuses on improving the technical aspects of a website. Page speed, mobile-friendliness, and crawlability are critical factors.</p>
    <h3>Page Speed Optimization</h3>
    <p>Fast loading pages provide better user experience and rank higher. Optimize images, minify code, and leverage browser caching.</p>
    <h3>Mobile Responsiveness</h3>
    <p>Mobile-friendly websites are essential since most searches now happen on mobile devices. Use responsive design principles.</p>
    <h2>Link Building Strategies</h2>
    <p>Building high-quality backlinks remains one of the most important ranking factors. Focus on earning links from authoritative websites.</p>
    <h3>Guest Posting</h3>
    <p>Guest posting on relevant blogs helps build authority and referral traffic. Choose quality over quantity.</p>
    <h4>Finding Guest Post Opportunities</h4>
    <p>Search for blogs in your niche that accept guest contributions. Use advanced search operators to find opportunities.</p>
    <h5>Pitching Your Ideas</h5>
    <p>Craft compelling pitches that show value to the host blog's audience. Personalize each outreach email.</p>
    <h6>Tracking Results</h6>
    <p>Monitor referral traffic and backlink growth from guest posting efforts.</p>
    <img src="/images/seo-chart.png" alt="SEO growth chart showing traffic increase">
    <img src="/images/keyword-research.png" alt="Keyword research dashboard">
    <img src="/images/broken-link.png">
    <a href="https://example.com/blog">Our Blog</a>
    <a href="/services">Services</a>
    <a href="/about">About Us</a>
    <a href="https://external-site.com">External Resource</a>
    <a href="https://other-site.com/tools">Another External</a>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": "The Ultimate Guide to SEO Optimization",
        "author": {"@type": "Person", "name": "SEO Expert"}
    }
    </script>
</body>
</html>"""
