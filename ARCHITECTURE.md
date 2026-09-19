# SEO Tools — Architecture

## Overview

SEO Inspector — Chrome extension + FastAPI backend for on-page SEO auditing, plus an
e-commerce scraping service.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Extension | JavaScript, Manifest V3, Chrome APIs |
| Analysis | BeautifulSoup4, own rule engine |
| Scraping | Playwright |
| Auth | JWT, bcrypt, SQLite (persistent) |
| Payments | Stripe Checkout + Webhooks |
| Rate Limiting | SlowAPI, configuration-driven |

## Architecture

```
Chrome Extension (Manifest V3)
    popup.js ←→ content-script.js ←→ API
         │ HTTPS
         ▼
FastAPI Backend
    ├── api/auth.py          — JWT auth, SQLite users, premium flag, rate limited
    ├── api/seo.py           — analyze / batch / keyword difficulty / rules / history
    ├── api/payments.py      — Stripe checkout, webhook, subscription state
    ├── api/scraping.py      — product, competitors, price history, export
    ├── services/seo_analyzer.py  — extraction only: facts about the document
    ├── services/audit.py         — rules and scoring: findings, categories, verdict
    ├── services/url_guard.py     — the single gate for every outbound URL
    ├── services/scraper_engine.py — Playwright (request guard, parallel batches)
    ├── database.py          — SQLite: users, audit_history, price_history (self-migration)
    ├── rate_limit.py        — SlowAPI limiter fed from settings
    └── config.py            — settings (.env honoured)
```

## Data Flow

```
1. The popup extracts the page HTML and analyses it locally (instant, offline)
2. POST /api/seo/analyze (optional bearer token) → seo_analyzer → audit
3. The response is normalised by the popup and rendered: overview, audit, meta, headings,
   keywords, links, images
4. With a token, the audit summary is stored in the account history
5. Batch mode and the scraper fetch through url_guard, which validates every hop
```

## Key Design Decisions

- **Extraction and judgement are separate.** `seo_analyzer` reports facts and never states
  an opinion; `audit` judges them. That separation is what lets rules, weights and
  thresholds evolve without touching the parser, and it is why every finding can carry the
  measured evidence next to the advice.
- **The document is never modified during extraction.** Boilerplate tags are skipped when
  building the visible text, not removed from the tree: the previous version counted
  headings, links and images on an already-trimmed document, which silently dropped every
  navigation link and every header/footer heading from the report.
- **One outbound gate.** `url_guard.check_url` serves the batch analyser, the scraper entry
  point and the browser request handler. Validating only at the API boundary leaves the
  TOCTOU window open, because the browser resolves the name again at request time.
- **Two scores, on purpose.** `score` (historical, additive) is kept untouched for deployed
  clients; `audit.score` is the weighted one to display, with a category breakdown. Removing
  the old field would silently break every installed copy of the extension.
- **SQLite with self-migration.** `init_db` adds missing columns and indexes at start-up, so
  a database already in production keeps serving without a migration script.
- **Premium and history persist, and belong to someone.** Subscription state is a column
  keyed by the Stripe customer id, and an audit is stored under the account that requested
  it (the history feature used to write every row as "anonymous", so it always read empty).
- **Rate limits come from settings** (`rate_limit_requests`, `rate_limit_window`,
  `rate_limit_enabled`), with per-route limits configurable: the previous hard-coded value
  ignored configuration entirely, so the test harness was throttled despite setting the
  variable it believed disarmed the limit.
- **Playwright lifecycle** is managed through the FastAPI lifespan, with one shared context,
  a bounded parallel batch, and a request guard that also refuses media/font resources the
  scraper never reads.
- **Analysis runs off the event loop** (`asyncio.to_thread`): parsing five megabytes of HTML
  is CPU work and used to freeze every other request for its duration.
