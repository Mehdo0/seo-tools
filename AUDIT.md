# SEO Inspector — Audit Complet

**Date**: 2026-07-15
**Auditeur**: Hernest (VM Dev)
**Périmètre**: backend (FastAPI), extension Chrome (MV3), scraping-service

---

## 1. Bugs Logiques

### HIGH — Race condition dans ScraperEngine (backend/services/scraper_engine.py)
`scraper` est un singleton global. `scrape_product()` appelle `self.start()` si le browser est null, sans lock. Deux requetes concurrentes declenchent deux `start()` en parallele → crash Playwright.
`scrape_competitors()` itere sequentiellement mais partage le meme browser — si un autre appel concurrent ferme le browser, l'autre crashe.

### HIGH — USERS_DB en RAM volatile (backend/api/auth.py:13)
Dict Python, aucune persistence. Au moindre restart du serveur, tous les utilisateurs disparaissent. Leurs tokens JWT restent valides mais `get_current_user` leve 401 car l'utilisateur n'est plus dans `USERS_DB`. Experience utilisateur catastrophique.

### MEDIUM — `compute_seo_score` condition buggee (backend/services/seo_analyzer.py:225)
```python
elif 50 <= fk or 70 <= fk:
    score += 4
```
`50 <= fk` est True pour TOUT fk >= 50. Un score de 80 recoit +4 au lieu de potentiellement +8. La condition voulue etait probablement `elif 50 <= fk < 60 or 70 < fk`.

### MEDIUM — `sumLoad` affiche la taille de la popup, pas de la page (extension/popup/popup.js:534)
```javascript
document.getElementById('sumLoad').textContent =
  `${(new TextEncoder().encode(document.documentElement?.outerHTML || '').length / 1024).toFixed(0) || '--'} KB`;
```
Dans le contexte d'une popup d'extension, `document` = `popup.html` (~8KB), pas la page analysee. La feature "Load time" est inutile.

### LOW — `scrape_competitors` pas atomique (backend/services/scraper_engine.py:59-71)
Si une URL sur 10 echoue, les 9 autres resultats sont retournes mais le scrape de l'URL foireuse a quand meme consomme du temps/reseau. Pas de rollback ou gestion partielle propre (c'est intentionnel mais a noter).

---

## 2. Failles de Securite

### HIGH — Token JWT transite en HTTP clair avec la nouvelle API
`API_BASE = 'http://hernestagent.duckdns.org'` — pas de TLS. Le token Bearer est envoye en clair sur le reseau a chaque requete. Interceptable par n'importe qui sur le chemin reseau (WiFi public, MITM, etc.).

### HIGH — Rate limiting insuffisant sur /api/auth/login
Pas de rate limit specifique sur les endpoints d'authentification. Le rate limit global (60/min) est insuffisant contre le brute-force cible. Un attaquant peut tester 60 mots de passe par minute sans blocage.

### MEDIUM — TOCTOU dans la validation SSRF (backend/api/scraping.py:38-49)
La resolution DNS est faite au moment de la validation, mais Playwright utilise sa propre resolution DNS au moment du scraping. Un attaquant peut faire pointer un domaine vers une IP publique lors de la validation, puis vers 127.0.0.1 lors du scraping. Time-of-check-time-of-use classique.

### MEDIUM — `secret_key` auto-genere non partage entre instances (backend/config.py:11-21)
Si on scale horizontalement (plusieurs instances), chaque instance genere son propre `SECRET_KEY`. Les tokens signes par l'instance A sont rejects par l'instance B.

### LOW — `/api/seo/analyze` public sans rate limit (backend/api/seo.py:37)
Pas d'authentification requise pour analyser du HTML. Un abus peut saturer le CPU (parsing BeautifulSoup + analyse de texte).

### LOW — Info disclosure sur `/api/health` (backend/main.py:49-52)
Expose le nom du service: `"SEO Tools API"`. Information mineure mais inutile.

---

## 3. Fonctionnalites a risque en Production

### HIGH — Playwright jamais stoppe proprement
`scraper.start()` est appele automatiquement mais `scraper.stop()` n'est jamais appele, ni dans le `lifespan` de FastAPI ni ailleurs. Au shutdown du serveur, les processus Chromium restent orphelins → fuite memoire + processus zombies.

### MEDIUM — Service Worker tue par Chrome apres 30s (extension/background/service-worker.js)
Manifest V3 tue les service workers inactifs. L'alarme `premiumCheck` de 24h ne se declenchera jamais si l'utilisateur n'ouvre pas regulierement l'extension. Le check premium devient inefficace.

### MEDIUM — Echec sur pages chrome:// (extension/popup/popup.js:180-193)
`chrome.scripting.executeScript` echoue sur les pages systeme Chrome. Le fallback `chrome.tabs.sendMessage` suppose que le content script est deja injecte, mais il est seulement injecte sur `document_idle` (pages web normales). Double echec → popup bloquee sans message clair.

### LOW — Double systeme de cache (extension)
Le popup gere son propre cache (`seo_cache_*`) ET le service worker aussi (`seo_analysis_*`). Duplication de stockage, incoherence potentielle entre les deux caches.

---

## 4. Performance

### MEDIUM — `scrape_competitors` sequentiel (backend/services/scraper_engine.py:59-71)
Boucle `for url in urls` sequentielle. Pour 10 URLs avec 30s timeout par URL = 5 minutes. Devrait utiliser `asyncio.gather()`.

### MEDIUM — HTML complet envoye a l'API pour chaque analyse (extension/popup/popup.js:452-465)
Pas de compression, pas de streaming. Une page de 2MB = 2MB d'upload par clic.

### LOW — `extract_keywords` complexite O(n*m) avec sliding window (backend/services/seo_analyzer.py:83-99)
Sur des pages de 10000+ mots, la generation des n-grams devient couteuse. Pas critique mais notable.

---

## 5. Code Mort / Fonctions Vides

| Fichier | Ligne | Description |
|---------|-------|-------------|
| `extension/content/content-script.js` | 29-42 | `extractMetaTags()` — le popup ne l'utilise jamais, refait l'extraction dans `analyzeLocally()` |
| `extension/background/service-worker.js` | 203-206 | `chrome.action.onClicked` — fonction vide, le popup s'ouvre via `default_popup` |
| `extension/popup/popup.js` | 137-146 | `loadSettings()` — lit les settings mais ne les applique pas |
| `extension/popup/popup.js` | 148-150 | `toggleSettings()` — fonction vide |
| `backend/api/seo.py` | 52-57 | `GET /api/seo/score` — retourne toujours 400, existe juste pour dire d'utiliser POST |
| `backend/config.py` | 29 | `frontend_dir` — jamais utilise |

---

## Resume

| Categorie | HIGH | MEDIUM | LOW |
|-----------|------|--------|-----|
| Bugs logiques | 2 | 2 | 1 |
| Failles securite | 2 | 2 | 2 |
| Risques prod | 1 | 2 | 1 |
| Performance | 0 | 2 | 1 |
| Code mort | 0 | 0 | 6 |

**Total**: 5 HIGH, 8 MEDIUM, 11 LOW — 24 findings.
