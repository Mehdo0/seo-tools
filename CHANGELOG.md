# Changelog

## [Unreleased]

### Fixed

- **The application could not start.** `api/payments.py` imported `USERS_DB` from
  `api.auth`, a symbol the SQLite migration had already removed: importing `main` raised
  `ImportError`, the deployed API could not boot, and 50 of the 81 tests errored out before
  reaching an assertion.
- **Counts were measured on a trimmed document.** `analyze_html` removed
  `script/style/nav/footer/header` *before* counting headings, links and images, so every
  navigation link, every header/footer heading and every footer image was missing from the
  report, and page weight was measured after the trim. Extraction no longer modifies the
  document; boilerplate is skipped only when building the visible text.
- **Internal/external links** were split with a substring test (`base_url in href`), which
  counted `notexample.com` as internal. Hostnames are compared now.
- **Reading ease was labelled Flesch-Kincaid**, which is a different formula. Both values
  are returned; the historical key keeps its old meaning.
- **Images were never returned by the scraper**: `_safe_attrs` passed an async generator to
  `set()`, which raises `TypeError`, and the exception was swallowed — the field came back
  empty on every scrape.
- **Premium state was stored nowhere.** It lived in a module-level dict that no longer
  existed, so Stripe webhooks wrote into the void and `/status` always answered `false`.
  Subscription state is now persisted (migration-safe columns) with the Stripe customer id.
- **Audit history never contained anything for a real account.** Every public analysis was
  written under the literal account "anonymous" and read back with the caller's email. The
  endpoint now identifies the caller optionally and stores the audit under their address.
- **Price history was invented**: the response carried a single point built from the
  current price and nothing was persisted. Points are now stored and the series, lowest and
  highest are returned.
- **The extension report broke whenever the API answered**: the response was merged with
  `{...local, ...api}` although the two engines expose different shapes, so `headings.h1`
  became an object read as an array and the link counts disappeared.
- **`.env` was silently ignored** (nested `class Config` is not how pydantic-settings v2
  reads configuration).
- Deprecated `GET /api/seo/score` answered 404 instead of the documented 400 hint.
- `GET /api/payments/config` required a token while returning a publishable key; the
  subscription flow could not start for a visitor who was not signed in.

### Security

- **SSRF in `POST /api/seo/batch-analyze`**: it fetched arbitrary URLs with httpx and no
  check at all — cloud metadata, localhost and RFC1918 ranges were reachable.
- **The scraping validator was weaker than it read**: `gethostbyname` returned one IPv4
  answer (so a public A plus a private AAAA passed), the private ranges were CIDR *strings*
  compared by equality ("10.0.0.0/8" can never match), any port was accepted, and the
  check-then-re-resolve window stayed open because the browser resolved names again.
- `services/url_guard.py` is now the single gate: every resolved IPv4/IPv6 address must be
  public, explicit port allowlist, no credentials in the URL, internal suffixes refused,
  redirects followed manually with each hop re-validated, body size capped, and a
  request-level handler inside the browser so a DNS answer cannot change between the check
  and the fetch. 38 tests cover it.
- A request body is refused (413) before being read instead of after being buffered.
- The scraper no longer advertises a three-year-old Chrome user agent.

### Added

- `services/audit.py`: rule engine producing findings (severity, category, evidence, fix,
  points lost) and a weighted score over seven categories, plus `GET /api/seo/rules`
  documenting the ruleset.
- New extracted signals: robots directives, `hreflang`, `lang`, charset, canonical
  absoluteness/self-reference/host, OG extras (`og:url`, `og:site_name`, `og:image:alt`),
  `twitter:site`, heading structure, content statistics, image quality, link quality,
  structured-data validation (per-type required properties), rendering signals.
- Persisted price history (`price_history` table, numeric value parsed from the display
  string) with lowest/highest/current.
- Audit tab in the extension rendering categories, findings, fixes and rule ids.
- Indexes on `audit_history` and `price_history`.

### Performance

- Analysis runs in a worker thread: a 5 MB page used to block the event loop for the whole
  parse.
- Competitor scraping is parallel behind a semaphore (ten URLs used to cost ten sequential
  page loads) and waits for the DOM plus the target selector instead of `networkidle` plus a
  fixed two-second sleep.
- Rate limits are configuration-driven (`RATE_LIMIT_REQUESTS`/`_WINDOW` were dead code: the
  limiter was hard-coded to 60/minute, so the test harness was throttled despite setting the
  variable).
- Keyword extraction is bounded (it built five n-grams per word over the whole document).
