# SEO Tools — Architecture

## Overview

SEO Inspector — Chrome extension + FastAPI backend for on-page SEO auditing.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Extension | JavaScript, Manifest V3, Chrome APIs |
| SEO Analysis | BeautifulSoup4, NLTK, readability-lxml |
| Scraping | Playwright, Pandas |
| Auth | JWT, bcrypt, SQLite (persistent) |
| Payments | Stripe Checkout + Webhooks |
| Rate Limiting | SlowAPI |

## Architecture

```
Chrome Extension (Manifest V3)
    popup.js ←→ content-script.js ←→ API
         │ HTTPS (hernestagent.duckdns.org)
         ▼
FastAPI Backend
    ├── api/auth.py        — JWT auth, SQLite users, rate limited
    ├── api/seo.py          — SEO analysis endpoint
    ├── api/payments.py     — Stripe checkout
    ├── api/scraping.py     — E-commerce scraping
    ├── services/seo_analyzer.py  — HTML parsing, scoring
    ├── services/scraper_engine.py — Playwright (async lock)
    ├── database.py         — SQLite (users + audit_history)
    ├── rate_limit.py       — SlowAPI limiter
    └── config.py           — Settings, persistent SECRET_KEY
```

## Data Flow

```
1. User clicks extension → popup.js extracts page HTML
2. popup.js → POST /api/seo/analyze → seo_analyzer.py
3. seo_analyzer.py → parse HTML, compute scores
4. Response → popup.js renders audit results
5. (Premium) Audit saved to SQLite audit_history
```

## Key Design Decisions

- SQLite for persistence (no Redis/Postgres needed)
- SECRET_KEY saved to file between restarts
- Playwright browser lifecycle managed via FastAPI lifespan
- asyncio.Lock protects concurrent scraper access
- Rate limiting: 5/min on login, 60/min global
