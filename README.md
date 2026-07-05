<p align="center">
  <img src="extension/icons/icon-128.png" alt="SEO Inspector Logo" width="128" height="128" />
</p>

<h1 align="center">SEO Inspector — Votre Audit SEO en 1 Clic</h1>

<p align="center">
  <strong>Analysez le SEO de n'importe quelle page en 1 clic. Méta-tags, mots-clés, structure, score. Gratuit. Extension Chrome Manifest V3.</strong>
</p>

<p align="center">
  <a href="https://chromewebstore.google.com"><img src="https://img.shields.io/badge/Chrome-Extension-blue?logo=googlechrome&logoColor=white" alt="Chrome Extension" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Manifest-V3-brightgreen" alt="Manifest V3" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python 3.11" /></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Payments-Stripe-635BFF?logo=stripe&logoColor=white" alt="Stripe" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Scraping-Playwright-2EAD33?logo=playwright&logoColor=white" alt="Playwright" /></a>
  <a href="#"><img src="https://img.shields.io/badge/docs-Fran%C3%A7ais-0055A4?logo=readthedocs&logoColor=white" alt="Docs en Français" /></a>
</p>

---

## 📖 Présentation

**SEO Tools** est une plateforme SaaS comprenant deux produits :

| Produit | Description | Cible |
|---|---|---|
| 🔍 **SEO Inspector** | Extension Chrome d'audit SEO on-page | Marketeurs, SEO, développeurs |
| 📊 **Scraping E-Commerce** | Service B2B d'extraction de données produits | E-commerçants, dropshippers, agences |

---

## 🚀 Quick Start

```bash
# Cloner le projet
git clone https://github.com/votre-compte/seo-tools.git
cd seo-tools

# Installer les dépendances
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Démarrer l'API backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# (Optionnel) Installer l'extension Chrome
# 1. Ouvrir chrome://extensions/
# 2. Activer le Mode développeur
# 3. Charger l'extension non empaquetée -> dossier seo-tools/extension/
```

Documentation interactive Swagger : [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🌐 SEO Title & Description

```
SEO title       : SEO Inspector — Chrome Extension SEO Gratuite | Analyse On-Page
SEO description : Analysez le SEO de n'importe quelle page en 1 clic. Méta-tags, mots-clés,
                  structure, score. Gratuit. Extension Chrome Manifest V3.
H1              : SEO Inspector — Votre Audit SEO en 1 Clic
```

---

## 📚 Documentation

| Document | Description |
|---|---|
| [Guide Extension SEO](docs/SEO-EXTENSION.md) | Guide utilisateur complet de l'extension Chrome |
| [Service de Scraping](docs/SCRAPING-SERVICE.md) | Offre, cas d'usage, packages et livrables |
| [Tarifs](docs/PRICING.md) | Free vs Premium, packages scraping, FAQ paiement |
| [Architecture](ARCHITECTURE.md) | Architecture technique globale |

---

## 🏗️ Architecture

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

---

## 🔌 API Reference

Base URL : `https://api.votre-domaine.com`

### Authentication

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Inscription (email + mot de passe) |
| `POST` | `/api/auth/login` | Connexion — retourne un token JWT |

Tous les endpoints protégés nécessitent le header :  
`Authorization: Bearer <jwt_token>`

### SEO Analysis

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/seo/analyze` | ✗ | Analyse SEO complète d'une page HTML |
| `GET` | `/api/seo/score` | ✗ | (Déprécié — utiliser `/analyze`) |

**POST /api/seo/analyze**

```json
// Request
{
  "url": "https://example.com",
  "html": "<html>...</html>"
}

// Response (200)
{
  "url": "https://example.com",
  "meta_tags": { "title": "...", "description": "...", ... },
  "headings": { "h1": { "count": 1, "content": ["..."] }, ... },
  "keywords": { "top_words": [...], "top_2grams": [...], "top_3grams": [...] },
  "readability": { "flesch_kincaid": 65.2, "word_count": 450, ... },
  "images": { "total": 12, "without_alt": 3 },
  "links": { "internal": 45, "external": 8, "total": 53 },
  "structured_data": { "has_structured_data": true, "types": ["Article"] },
  "mobile_viewport": { "has_viewport": true, "content": "width=device-width" },
  "score": 78
}
```

### Scraping (Authentification requise)

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/scraping/product` | Scraper un produit unique |
| `POST` | `/api/scraping/competitors` | Comparaison multi-boutiques (max 10 URLs) |
| `POST` | `/api/scraping/price-history` | Suivi de prix avec historique |
| `POST` | `/api/scraping/export` | Exporter des données en JSON ou CSV |

**POST /api/scraping/product**

```json
// Request
{
  "url": "https://boutique.com/produit",
  "selectors": {
    "title": "h1",
    "price": ".product-price"
  }
}

// Response (200)
{
  "url": "https://boutique.com/produit",
  "title": "T-shirt Premium",
  "price": "29.99€",
  "description": "T-shirt en coton bio...",
  "images": ["https://boutique.com/img/tshirt.jpg"],
  "variants": ["S", "M", "L", "XL"],
  "scraped_at": "2026-07-05T10:30:00Z"
}
```

### Payments (Authentification requise)

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/payments/create-checkout` | Créer une session de paiement Stripe |
| `POST` | `/api/payments/webhook` | Webhook Stripe (appelé par Stripe) |

### System

| Méthode | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/health` | ✗ | Health check |

---

## 🛠️ Tech Stack

| Couche | Technologie |
|---|---|
| Backend API | Python 3.11, FastAPI, Uvicorn |
| Chrome Extension | JavaScript, Manifest V3, Chrome APIs |
| SEO Analysis | BeautifulSoup4, NLTK |
| Scraping Engine | Playwright (async), Pandas |
| Authentication | JWT (HS256), bcrypt |
| Payments | Stripe Checkout + Webhooks |
| Rate Limiting | SlowAPI |
| Deployment | Docker, Systemd |

---

## 📂 Structure du projet

```
seo-tools/
├── extension/                  # Chrome Extension Manifest V3
│   ├── manifest.json
│   ├── popup/                  # Interface de l'extension
│   ├── content/                # Content script injecté
│   ├── background/             # Service worker
│   └── icons/                  # Icônes (16, 48, 128)
├── backend/                    # API FastAPI
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── config.py               # Configuration (env vars)
│   ├── api/                    # Routeurs
│   │   ├── auth.py             # JWT + bcrypt
│   │   ├── seo.py              # Analyse SEO
│   │   ├── scraping.py         # Scraping produits
│   │   └── payments.py         # Stripe
│   ├── services/               # Logique métier
│   │   ├── seo_analyzer.py     # Moteur d'analyse SEO
│   │   └── scraper_engine.py   # Moteur Playwright
│   └── tests/                  # Tests unitaires
├── scraping-service/           # Moteur de scraping standalone
│   ├── scraper.py              # CLI + core engine
│   ├── product_monitor.py      # Suivi de prix
│   └── templates/              # Templates HTML
├── docs/                       # Documentation
│   ├── SEO-EXTENSION.md
│   ├── SCRAPING-SERVICE.md
│   └── PRICING.md
├── docker/                     # Déploiement Docker
└── ARCHITECTURE.md
```

---

## 💰 Pricing Summary

| Produit | Gratuit | Payant |
|---|---|---|
| **SEO Inspector** | 50 analyses/mois, fonctionnalités de base | **5 €/mois** (ou 50 €/an) — Premium illimité |
| **Scraping B2B** | — | Basic **500 €**, Pro **1 500 €**, Enterprise **sur devis** |

👉 [Voir la page de tarifs complète](docs/PRICING.md)

---

## 📞 Contact

- **Email** : `contact@votre-domaine.com`
- **Extension Premium** : `premium@votre-domaine.com`
- **Scraping B2B** : `scraping@votre-domaine.com`
- **Support** : réponse sous 24h ouvrées

---

## 📄 License

MIT © 2026 SEO Tools
