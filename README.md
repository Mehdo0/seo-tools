# SEO Inspector

Chrome extension + backend API for on-page SEO auditing.

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Extension | JavaScript, Manifest V3 |
| SEO Analysis | BeautifulSoup4, NLTK, readability-lxml |
| Scraping | Playwright, Pandas |
| Auth | JWT, bcrypt, SQLite |
| Payments | Stripe Checkout + Webhooks |

## Quick Start

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn main:app --host 0.0.0.0 --port 8080
```

## Architecture

```
Chrome Extension → API (/api/seo/analyze) → SEO Analyzer → Score
                                     └→ Scraper Engine → E-commerce data
                                     └→ Auth (/api/auth/*) → SQLite
                                     └→ Payments (/api/payments/*) → Stripe
```

## Features

- On-page SEO audit: titles, meta, headings, images, links
- Readability scores: Flesch-Kincaid, SMOG
- Keyword density & extraction
- Mobile-friendly check
- HTTPS enforcement check
- E-commerce product scraping (Playwright)
- JWT auth with persistent SQLite users
- Stripe payments (test mode)
- Rate limiting on auth endpoints

## API

| Endpoint | Auth | Description |
|---|---|---|
| POST /api/seo/analyze | No | Full SEO audit |
| GET /api/seo/history | Yes | User audit history |
| POST /api/auth/register | No | Create account |
| POST /api/auth/login | No | Login (5 req/min) |
| GET /api/auth/me | Yes | Current user |
| POST /api/scraping/product | No | Scrape product page |
| POST /api/scraping/competitors | No | Batch competitor scrape |
| GET /api/health | No | Health check |

## Development

```bash
# Tests
cd backend && python -m pytest tests/ -v

# Lint
ruff check backend/

# Build extension
zip -r seo-inspector-chrome.zip extension/ -x "*.py"
```
