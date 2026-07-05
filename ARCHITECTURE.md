# SEO Tools — Architecture

## Overview

Two revenue-generating products sharing a common backend:

1. **Chrome Extension SEO** — Freemium SEO analysis tool (Manifest V3)
2. **Scraping B2B Service** — E-commerce data extraction for clients

## Architecture

```
┌──────────────────────────────────────────────────┐
│                 Chrome Extension                  │
│  popup.html ←→ content-script.js ←→ API         │
└────────────────────┬─────────────────────────────┘
                     │ HTTPS
┌────────────────────▼─────────────────────────────┐
│              Backend API (FastAPI)                │
│  /api/seo/*    /api/auth/*    /api/scraping/*    │
│  /api/payments/*  (Stripe)                       │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│              Scraping Engine                      │
│  Playwright → E-commerce data → CSV/JSON/HTML    │
└──────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Extension | JavaScript, Manifest V3, Chrome APIs |
| SEO Analysis | BeautifulSoup4, NLTK |
| Scraping | Playwright, Pandas |
| Auth | JWT, bcrypt |
| Payments | Stripe Checkout + Webhooks |
| Deployment | Docker, Systemd |
