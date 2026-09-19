# Roadmap — remaining work

What the audit round did **not** do, ordered, with the sources that justify each item.
Everything listed here was verified against the code, not inferred.

## Correctness and trust of the report

- **Real Core Web Vitals instead of markup estimates.** `core_web_vitals` derives LCP/FCP/CLS
  from tag counts and document size and now says so (`source: "markup-estimate"`). The official
  thresholds are LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 at the 75th percentile, mobile and
  desktop separately: use the CrUX API for field data, falling back to PageSpeed
  Insights/Lighthouse for URLs without CrUX coverage, and label the source in the report.
  <https://web.dev/articles/vitals> · <https://developer.chrome.com/docs/crux/api> ·
  <https://developers.google.com/speed/docs/insights/v5/get-started>
- **INP, not FID.** INP replaced FID as a Core Web Vital on 12 March 2024; the model has no
  field for it. <https://web.dev/blog/inp-cwv-march-12>
- **HTTP-header and robots.txt signals.** The API only sees the HTML it is given, so `X-Robots-Tag`,
  redirect chains, status codes, compression, `Cache-Control` and TTFB are invisible. Add a
  `POST /api/seo/fetch-audit` that fetches the page through `url_guard` and reports them.
  Also read `robots.txt` (RFC 9309) — the commercial documentation claims it is respected.
  <https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag> ·
  <https://www.rfc-editor.org/rfc/rfc9309.html>
- **JavaScript vs raw HTML.** Compare what the server sends with the rendered DOM (content,
  links, canonical, JSON-LD, client-injected meta): the extension sends the rendered DOM, the
  batch path sends the raw response, and nothing measures the gap.
  <https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics>
- **Content duplication and thin content** beyond word count (shingles + MinHash across pages),
  overlap between title, H1 and description, freshness (`datePublished`/`dateModified`) and
  E-E-A-T signals (identifiable author, sources cited).
  <https://developers.google.com/search/docs/fundamentals/creating-helpful-content>
- **Accessibility as an on-page signal**: skipped heading levels (partly covered), contrast,
  form labels, landmarks, invalid ARIA. <https://www.w3.org/TR/WCAG22/>
- **Mobile parity**: render with a mobile emulation profile and compare content with desktop,
  instead of only checking that a viewport tag exists.
  <https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing> ·
  <https://playwright.dev/python/docs/emulation>

## Robustness

- **Payload size.** The popup sends the whole HTML (up to 5 MB, uncompressed) although it has
  already extracted the useful data locally. Send the extracted structure, or gzip via
  `CompressionStream` plus `GZipMiddleware`.
  <https://fastapi.tiangolo.com/advanced/middleware/> · <https://developer.mozilla.org/en-US/docs/Web/API/CompressionStream>
- **One cache, not two.** `seo_cache_*` (popup) and `seo_analysis_*` (service worker) both key
  on the URL alone with a one-hour TTL: a modified page is served stale, and the two can
  disagree. Single namespace, key = URL + content fingerprint, purge with `getBytesInUse`.
  <https://developer.chrome.com/docs/extensions/reference/api/storage>
- **SQLite hardening**: WAL mode, `busy_timeout`, pagination of history, `aiosqlite` or worker
  threads (the calls are synchronous inside async handlers). <https://www.sqlite.org/wal.html>
- **Scraper isolation**: a browser pool with one context per request (a context is an isolated
  session), bounded concurrency, a global timeout per request and back-pressure (429 beyond the
  quota), plus egress filtering in the deployment (deny IMDS and RFC1918 as defence in depth).
  <https://playwright.dev/python/docs/browser-contexts>
- **Rate limit key**: `get_remote_address` returns the proxy address in production, so every
  user shares one bucket unless `X-Forwarded-For` is trusted explicitly.
- **Observability**: structured logs with a request id, per-endpoint metrics (p95, failure
  rate), a `/api/ready` distinct from `/api/health`, and logging of refused SSRF targets.
- **Reproducible build**: lockfile, `requirements-dev` (pytest, ruff, httpx), Docker
  healthcheck, and README/ARCHITECTURE aligned on the dependencies actually used.

## Product

- **Side panel instead of a popup** (`chrome.sidePanel`): the report survives navigation, and
  the DOM work moves out of the service worker. Permissions would then be
  `activeTab + scripting + storage + sidePanel`.
- **Score weighting, one engine.** The extension's local score and the server audit score are
  still two implementations; the server one is the reference, the local one only a fallback
  until the API answers.

## Note on the July audit

`AUDIT.md` (15 July 2026) is a dated snapshot. Already fixed before this round: `USERS_DB` in
RAM, the broken readability condition, the missing `asyncio.Lock`, `scraper.stop()` not called,
plain HTTP for the API, no rate limit on login. Fixed in this round: everything in
`CHANGELOG.md`. Still relevant from it: the TOCTOU hardening is now done in code but the
deployment-level egress filtering is not.
