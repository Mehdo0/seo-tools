# SEO Inspector

Chrome extension + backend API for on-page SEO auditing.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Extension | JavaScript, Manifest V3 |
| Analysis | BeautifulSoup4, own rule engine (`services/audit.py`) |
| Scraping | Playwright |
| Auth | JWT, bcrypt, SQLite |
| Payments | Stripe Checkout + Webhooks |

## Quick Start

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium            # only needed for the scraping endpoints
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Architecture

```
Chrome Extension → POST /api/seo/analyze → seo_analyzer (facts) → audit (rules + score)
                                       └→ url_guard → fetch_checked (batch mode)
                                       └→ Scraper Engine (Playwright) → e-commerce data
                                       └→ Auth (/api/auth/*) → SQLite
                                       └→ Payments (/api/payments/*) → Stripe
```

Two scores are returned. `score` is the historical additive score, kept for existing
clients. `audit.score` is the one to display: a weighted score over seven categories with
one entry per finding, explaining what is wrong and what it costs — `GET /api/seo/rules`
documents the ruleset.

## Features

- **Audit report**: findings with severity, measured evidence, the fix to apply and the
  points lost; per-category scores (content, indexability, structure, performance, social,
  mobile, media).
- On-page checks: titles and meta descriptions (length, repetition), headings (single H1,
  skipped levels, empty), content length and readability (Flesch reading ease and
  Flesch-Kincaid grade), images (alt, dimensions, lazy loading, srcset, modern formats),
  links (internal/external by hostname, anchor text, nofollow, `#` links).
- Technical checks: robots directives (noindex), canonical (absolute, self-referencing,
  cross-domain), `hreflang`, `lang`, meta refresh, structured data validation (context,
  known types, properties Google requires), Open Graph and Twitter cards, viewport quality.
- Rendering signals: render-blocking resources, `defer`/`async`, inline byte weight, DOM
  node count, third-party hosts, preconnect/preload, LCP/FCP/CLS estimates (markup-derived,
  not field data).
- E-commerce scraping through Playwright: product pages, competitor batches in parallel,
  and a persisted price history (lowest/highest/current).
- JWT auth with SQLite persistence, Stripe subscriptions with real persistence, per-account
  audit history.
- Single hardened gate for every outbound request (`services/url_guard.py`): SSRF checks on
  every resolved address, port allowlist, redirect re-validation, body size cap, and a
  request-level guard inside the browser so a DNS record cannot change between check and
  fetch.

## API

| Endpoint | Auth | Description |
|---|---|---|
| POST /api/seo/analyze | optional | Audit a page (`html` required, `url` for relative links). With a token, the audit is stored in that account's history. |
| POST /api/seo/batch-analyze | No | Fetch and audit up to 50 URLs (each hop validated), `format=json\|csv` |
| POST /api/seo/keyword-difficulty | No | Intrinsic keyword difficulty estimate (no SERP queried) |
| GET /api/seo/rules | No | Ruleset: categories, weights, what each rule checks |
| GET /api/seo/score | No | Deprecated — answers 400 and points at POST /analyze |
| GET /api/seo/history | Yes | Audit history of the account |
| POST /api/auth/register, /login | No | Create an account / sign in (5 req/min) |
| GET /api/auth/me | Yes | Current account (includes `premium`) |
| POST /api/scraping/product | Yes | Scrape one product page |
| POST /api/scraping/competitors | Yes | Scrape up to 10 competitors in parallel |
| POST /api/scraping/price-history | Yes | Scrape and store a price point, return the series |
| POST /api/scraping/export | Yes | Export scraped data (json/csv) |
| POST /api/payments/create-checkout, /webhook | Yes / Stripe | Subscription |
| GET /api/payments/status | Yes | Subscription state |
| GET /api/payments/config | No | Publishable key and price id (public by nature) |
| GET /api/health | No | Health check |

Rate limits come from configuration (`RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`,
`ANALYZE_RATE_LIMIT`, `BATCH_RATE_LIMIT`) and `RATE_LIMIT_ENABLED=false` disables the
limiter entirely — which is what the test suite does.

## Development

```bash
# Tests (127 passed, 1 skipped)
cd backend && python -m pytest tests/ -v

# Lint
ruff check backend/

# Build extension
zip -r seo-inspector-chrome.zip extension/ -x "*.py"
```

## Status

Pre-alpha. See `CHANGELOG.md` for what changed in the current round.
