# 🚀 SEO Tools — Double Revenue Engine

[![Chrome](https://img.shields.io/badge/Chrome-MV3-4285F4?logo=googlechrome)](https://chrome.google.com/webstore)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33?logo=playwright)](https://playwright.dev)
[![Tests](https://img.shields.io/badge/tests-76%2F76-2E8B57)](#)
[![License](https://img.shields.io/badge/license-MIT-C9A84C)](LICENSE)

Two revenue-generating products sharing a common backend, built in 2 weeks by Mehdi + Hernest AI.

---

## 📦 Products

### 🔍 SEO Inspector — Chrome Extension

Professional on-page SEO analysis in one click. Freemium model.

| Tier | Features | Price |
|------|----------|-------|
| **Free** | Meta tags, headings, word count, basic SEO score (0-100) | 0€ |
| **Premium** | Keyword density, backlink analysis, competitor comparison, export reports | 5€/month |

**No account required. No data leaves your browser.** All analysis runs locally.

### 🕷️ Scraping Engine — B2B Service

E-commerce data extraction service for businesses.

| Package | Scope | Price |
|---------|-------|-------|
| **Basic** | 1 product, 1 competitor, CSV export | 500€ |
| **Pro** | Up to 5 products, price monitoring, HTML report | 1,500€ |
| **Enterprise** | Custom volume, API access, dedicated support | Quote |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────┐
│           SEO Inspector (Chrome MV3)      │
│  popup.js ←→ content-script ←→ DOM      │
└────────────────┬─────────────────────────┘
                 │
┌────────────────▼─────────────────────────┐
│           Backend API (FastAPI)           │
│  /api/seo/*  /api/auth/*  /api/scraping/*│
│  /api/payments/* (Stripe)                │
└────────────────┬─────────────────────────┘
                 │
┌────────────────▼─────────────────────────┐
│           Scraping Engine                 │
│  Playwright → Anti-bot → CSV/JSON/HTML  │
└──────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| SEO Analysis | BeautifulSoup4, NLTK |
| Scraping | Playwright (stealth), Pandas |
| Auth | JWT, bcrypt |
| Payments | Stripe Checkout + Webhooks |
| Extension | JavaScript, Manifest V3, Chrome APIs |
| Deployment | Docker Compose, Systemd |

## 📁 Project Structure

```
seo-tools/
├── extension/               # Chrome Extension Manifest V3
│   ├── manifest.json
│   ├── popup/               # SPA-like popup (350×500px)
│   │   ├── popup.html       # Clean UI, cream/navy/gold
│   │   ├── popup.js         # Local SEO analysis engine
│   │   └── popup.css        # 15KB design system
│   ├── background/          # Service worker
│   ├── content/             # Page content extraction
│   └── icons/               # 16/48/128px PNG
│
├── backend/                 # FastAPI backend
│   ├── main.py              # App entry, CORS, routers
│   ├── config.py            # Env-based settings
│   ├── api/
│   │   ├── seo.py           # POST /api/seo/analyze
│   │   ├── auth.py          # JWT auth (register/login/me)
│   │   ├── payments.py      # Stripe webhook + checkout
│   │   └── scraping.py      # Scraping endpoints
│   ├── services/
│   │   ├── seo_analyzer.py  # HTML parser, keyword extraction, scoring
│   │   └── scraper_engine.py # Playwright-based scraper
│   └── tests/               # 76 pytest tests
│
├── scraping-service/        # Standalone scraping engine
│   ├── scraper.py           # EcommerceScraper class
│   ├── product_monitor.py   # Price tracking + alerts
│   └── templates/           # Client report HTML
│
├── docs/                    # Client-facing documentation
│   ├── SEO-EXTENSION.md     # User guide (FR)
│   ├── SCRAPING-SERVICE.md  # Service offering (FR)
│   └── PRICING.md           # Complete pricing (FR)
│
├── docker/                  # Docker Compose
├── Makefile                 # Single-command startup
└── ARCHITECTURE.md          # Technical architecture
```

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/Mehdo0/seo-tools.git
cd seo-tools

# Install & run
make install
make run
```

API available at `http://localhost:8000` — see `/api/health` for status.

## 🔌 API Reference

### Health
```http
GET /api/health
```

### SEO Analysis
```http
POST /api/seo/analyze
Content-Type: application/json

{
  "url": "https://example.com",
  "html": "<!DOCTYPE html><html>..."
}
```

Returns: meta tags, headings, keywords, readability, images, links, structured data, mobile viewport, overall score.

### Auth
```http
POST /api/auth/register  → { username, password, email }
POST /api/auth/login     → JWT cookie
GET  /api/auth/me        → User profile
```

### Scraping (auth required)
```http
POST /api/scraping/product     → { url, selectors? }
POST /api/scraping/competitors → { urls: [] }
POST /api/scraping/price-history → { url }
POST /api/scraping/export      → { data: [], format: "csv"|"json" }
```

### Payments
```http
POST /api/payments/create-checkout → Stripe session
POST /api/payments/webhook        → Stripe events
```

## 🧪 Testing

```bash
pip install pytest httpx
python -m pytest backend/tests/ -v
```

**76 tests, 0 failures.**

## 🚢 Deployment

```bash
# Docker
make docker-up

# Or systemd
sudo cp seo-api.service /etc/systemd/system/
sudo systemctl enable --now seo-api
```

## 🔒 Security

- ✅ Rate limiting (slowapi, 60 req/min)
- ✅ SSRF protection (URL validation, blocked private IPs)
- ✅ Generic error messages (no stack traces)
- ✅ Auto-generated JWT secret
- ✅ Path traversal prevention (file exports)
- ✅ bcrypt password hashing
- ✅ Stripe webhook signature verification
- ✅ CORS restricted (no wildcard + credentials)
- ✅ 0 dependency CVEs (pip-audit clean)

## 📊 Performance

| Metric | Value |
|--------|-------|
| API response time | <50ms (avg) |
| SEO analysis | <200ms per page |
| Scraping | 2-5s per product (respected delays) |
| Concurrent users | 100+ (FastAPI async) |
| Test coverage | 76 test cases |
| Bundle size (extension) | 124 KB zipped |

## 👥 Credits

Built by **Mehdi Mouaffak** + **Hernest** (AI agent). 6 specialized AI sub-agents orchestrated in parallel.

## 📄 License

MIT
