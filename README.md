# SEO Tools

Extension Chrome SEO freemium + Service de scraping e-commerce B2B.

## Quick Start

```bash
make install
make run
```

## Products

### 🔍 SEO Inspector (Chrome Extension)
Analyse SEO on-page en un clic. Version gratuite + premium (5-10€/mois).

### 📊 Scraping E-commerce (Service B2B)
Extraction de données produits, veille prix, rapports concurrentiels pour e-commerçants.

## Structure

```
seo-tools/
├── extension/          # Chrome Extension Manifest V3
├── backend/            # API FastAPI
├── scraping-service/   # Moteur de scraping Playwright
├── docs/               # Documentation
└── docker/             # Déploiement
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET /api/health | Health check |
| POST /api/seo/analyze | Analyse SEO d'une page |
| POST /api/auth/register | Inscription |
| POST /api/auth/login | Connexion JWT |
| POST /api/scraping/product | Scraper un produit |

## License

MIT
