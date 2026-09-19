"""Audit rules: turn extracted signals into findings, category scores and a verdict.

Design: the extractor (`seo_analyzer`) reports facts, this module judges them. Every
finding carries an `id`, a severity, the category it belongs to, the measured evidence,
what to do about it, and the points it costs. That is what makes a report actionable
instead of a single number: previously the API returned a flat additive score with magic
weights and no explanation of what was wrong or why it cost points.
"""

from typing import Any

CATEGORY_WEIGHTS = {
    "content": 24,
    "indexability": 22,
    "structure": 16,
    "performance": 16,
    "social": 8,
    "mobile": 8,
    "media": 6,
}

SEVERITY_ORDER = {"critical": 0, "warning": 1, "notice": 2}
SEVERITY_LABELS = {"critical": "critical", "warning": "warning", "notice": "notice"}

RULESET_VERSION = "2026-09-1"


def _finding(findings: list, category: str, severity: str, rule: str, impact: int,
             message: str, fix: str, evidence: Any = None) -> None:
    findings.append({
        "rule": f"{category}.{rule}",
        "category": category,
        "severity": SEVERITY_LABELS[severity],
        "impact": impact,
        "message": message,
        "fix": fix,
        "evidence": evidence,
    })


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    if score >= 40:
        return "E"
    return "F"


def _audit_content(findings: list, analysis: dict) -> None:
    meta = analysis.get("meta_tags", {})
    stats = analysis.get("content_stats", {})
    headings = analysis.get("headings", {})
    readability = analysis.get("readability", {})

    title = meta.get("title")
    title_length = meta.get("title_length", 0)
    if not title:
        _finding(findings, "content", "critical", "title.missing", 8,
                 "The page has no <title>.",
                 "Add a unique title of 30-60 characters that states the topic and the brand.")
    elif title_length < 30:
        _finding(findings, "content", "warning", "title.short", 3,
                 f"Title is only {title_length} characters.", "Aim for 30-60 characters.",
                 {"title": title})
    elif title_length > 65:
        _finding(findings, "content", "warning", "title.long", 3,
                 f"Title is {title_length} characters and will be truncated in results.",
                 "Keep the title under 60-65 characters.", {"title": title})
    if title:
        words = [w.lower() for w in title.split()]
        repeated = sorted({w for w in words if words.count(w) > 1 and len(w) > 2})
        if repeated:
            _finding(findings, "content", "notice", "title.repetition", 2,
                     f"Title repeats the same word: {', '.join(repeated)}.",
                     "Use each significant word once; repetition reads as keyword stuffing.")

    description = meta.get("description")
    description_length = meta.get("description_length", 0)
    if not description:
        _finding(findings, "content", "critical", "description.missing", 8,
                 "The page has no meta description.",
                 "Write a 120-160 character description that summarises the page and invites the click.")
    elif description_length < 120:
        _finding(findings, "content", "warning", "description.short", 3,
                 f"Meta description is only {description_length} characters.",
                 "Below ~120 characters the snippet text is wasted.", {"description": description})
    elif description_length > 160:
        _finding(findings, "content", "notice", "description.long", 2,
                 f"Meta description is {description_length} characters and will be cut off.",
                 "Trim it to 120-160 characters, keeping the value proposition first.")

    word_count = stats.get("word_count", 0)
    if word_count < 100:
        _finding(findings, "content", "critical", "content.thin", 8,
                 f"Only {word_count} words of visible text.",
                 "Search engines need substance: expand the page or merge it with a related one.",
                 {"word_count": word_count})
    elif word_count < 300:
        _finding(findings, "content", "warning", "content.short", 5,
                 f"{word_count} words of visible text — thin for most queries.",
                 "Target 300+ words of text a visitor actually needs.", {"word_count": word_count})

    if not headings.get("total"):
        _finding(findings, "content", "warning", "content.no_headings", 3,
                 "The page has no headings at all.",
                 "Structure the content with H2/H3 sections; headings are how both readers and crawlers scan.")

    grade = readability.get("flesch_kincaid_grade", 0)
    if grade and grade > 12:
        _finding(findings, "content", "warning", "content.readability", 3,
                 f"Text reads at US grade {grade} — harder than the recommended 6-10.",
                 "Shorten sentences, prefer common words, split long paragraphs.",
                 {"grade": grade, "avg_sentence_length": readability.get("avg_sentence_length")})
    if stats.get("long_sentences", 0) > 3:
        _finding(findings, "content", "notice", "content.long_sentences", 2,
                 f"{stats['long_sentences']} sentences run past 25 words.",
                 "Keep sentences under ~25 words for readability.")


def _audit_indexability(findings: list, analysis: dict) -> None:
    meta = analysis.get("meta_tags", {})
    directives = meta.get("robots_directives") or []
    has_noindex = "noindex" in directives or "none" in directives

    if has_noindex:
        _finding(findings, "indexability", "critical", "robots.noindex", 10,
                 f"Meta robots says: {meta.get('robots')} — this page is excluded from search.",
                 "Remove noindex once the page is ready to rank.", {"robots": meta.get("robots")})

    canonical = meta.get("canonical")
    if not canonical:
        _finding(findings, "indexability", "warning", "canonical.missing", 5,
                 "No canonical URL declared.",
                 "Add <link rel=\"canonical\"> pointing at the preferred URL to consolidate duplicates.")
    else:
        if not meta.get("canonical_absolute"):
            _finding(findings, "indexability", "warning", "canonical.relative", 2,
                     f"Canonical is relative: {canonical}.",
                     "Use an absolute URL including scheme and host.", {"canonical": canonical})
        if has_noindex:
            _finding(findings, "indexability", "critical", "canonical.noindex_conflict", 6,
                     "The page is both canonical to another URL and marked noindex.",
                     "Pick one strategy: index it, or canonicalise it — not both.",
                     {"canonical": canonical, "robots": meta.get("robots")})
        page_host = meta.get("canonical_host", "")
        if not meta.get("canonical_self") and meta.get("canonical") and analysis.get("url"):
            from .seo_analyzer import host_of
            if host_of(analysis["url"]) and page_host and host_of(analysis["url"]) != page_host:
                _finding(findings, "indexability", "warning", "canonical.cross_domain", 4,
                         f"Canonical points at another domain ({page_host}).",
                         "Cross-domain canonicals hand the ranking to the other site. Keep it on your own host unless that is deliberate.",
                         {"canonical": canonical})

    if not meta.get("lang"):
        _finding(findings, "indexability", "warning", "html.lang_missing", 3,
                 "The <html> element has no lang attribute.",
                 "Declare the page language (e.g. lang=\"fr\") for search and screen readers.")

    if meta.get("meta_refresh"):
        _finding(findings, "indexability", "warning", "meta.refresh", 3,
                 f"The page uses a meta refresh: {meta['meta_refresh']}.",
                 "Replace it with a permanent (301) redirect.")

    hreflang = meta.get("hreflang") or []
    if hreflang:
        relative = [entry for entry in hreflang if not str(entry.get("href", "")).startswith("http")]
        if relative:
            _finding(findings, "indexability", "notice", "hreflang.relative", 2,
                     f"{len(relative)} hreflang entries are relative URLs.",
                     "Use absolute URLs in hreflang annotations.")
        if not any(str(entry.get("lang", "")).lower() in ("x-default",) for entry in hreflang):
            _finding(findings, "indexability", "notice", "hreflang.no_xdefault", 1,
                     "No x-default hreflang entry.",
                     "Add an x-default entry for visitors whose language does not match any variant.")

    if meta.get("keywords_meta"):
        _finding(findings, "indexability", "notice", "meta.keywords", 1,
                 "The obsolete meta keywords tag is present.",
                 "Remove it: it has no ranking effect and exposes your keyword list.")


def _audit_structure(findings: list, analysis: dict) -> None:
    headings = analysis.get("headings", {})
    links = analysis.get("links", {})
    schema = analysis.get("structured_data", {})

    h1_count = headings.get("h1", {}).get("count", 0)
    if h1_count == 0:
        _finding(findings, "structure", "critical", "headings.h1_missing", 6,
                 "No H1 on the page.",
                 "Add one H1 stating the page's main subject.")
    elif h1_count > 1:
        _finding(findings, "structure", "warning", "headings.h1_multiple", 3,
                 f"{h1_count} H1 headings found.",
                 "Keep a single H1 and demote the others to H2.", {"h1_count": h1_count})
    if headings.get("empty"):
        _finding(findings, "structure", "notice", "headings.empty", 2,
                 f"{headings['empty']} headings are empty.",
                 "Remove empty headings or fill them: they add noise to the outline.")
    if headings.get("skipped_levels"):
        skipped = headings["skipped_levels"]
        _finding(findings, "structure", "notice", "headings.skipped_levels", 3,
                 f"Heading levels jump (e.g. H{skipped[0]['from']} then H{skipped[0]['to']}).",
                 "Keep the outline sequential: H1, then H2, then H3.", {"skipped": skipped})

    internal = links.get("internal", 0)
    if internal < 3:
        _finding(findings, "structure", "warning", "links.few_internal", 4,
                 f"Only {internal} internal link(s) on the page.",
                 "Link to related pages: internal links are how crawlers discover and rank the rest of the site.",
                 {"internal": internal})
    if not links.get("external"):
        _finding(findings, "structure", "notice", "links.no_external", 2,
                 "No outbound links.",
                 "Cite at least one authoritative source; outbound links to trusted sites are a positive signal.")
    if links.get("empty_anchor"):
        _finding(findings, "structure", "notice", "links.empty_anchor", 2,
                 f"{links['empty_anchor']} links have no text (and no image).",
                 "Give every link an explicit label: crawlers use anchor text to understand the target.")
    if links.get("hash_only"):
        _finding(findings, "structure", "notice", "links.hash_only", 1,
                 f"{links['hash_only']} links point to '#'.",
                 "Point them at real URLs or make them buttons.")
    if links.get("total", 0) > 100:
        _finding(findings, "structure", "notice", "links.too_many", 2,
                 f"{links['total']} links on a single page.",
                 "Beyond ~100 links, link equity dilutes; move secondary links to a hub page.")

    if not schema.get("has_structured_data"):
        _finding(findings, "structure", "warning", "schema.missing", 5,
                 "No structured data (JSON-LD) found.",
                 "Add schema.org markup for the page type: eligible rich results in search.")
    else:
        if schema.get("invalid_blocks"):
            _finding(findings, "structure", "warning", "schema.invalid", 4,
                     f"{schema['invalid_blocks']} JSON-LD block(s) are not valid JSON.",
                     "Fix the syntax: an invalid block is ignored entirely by search engines.")
        if schema.get("missing_properties"):
            missing = schema["missing_properties"][:4]
            _finding(findings, "structure", "notice", "schema.missing_properties", 3,
                     "Structured data is incomplete: " + "; ".join(
                         f"{entry['type']} lacks {', '.join(entry['missing'])}" for entry in missing),
                     "Add the properties Google lists for that type, otherwise it is ineligible for rich results.",
                     {"missing": missing})
        if not schema.get("uses_schema_org"):
            _finding(findings, "structure", "notice", "schema.context", 1,
                     "Structured data does not declare the schema.org context.",
                     "Set \"@context\": \"https://schema.org\" on the top-level object.")


def _audit_social(findings: list, analysis: dict) -> None:
    meta = analysis.get("meta_tags", {})
    for key, label in (("og_title", "og:title"), ("og_description", "og:description"), ("og_image", "og:image")):
        if not meta.get(key):
            _finding(findings, "social", "warning", f"og.{key}_missing", 2,
                     f"Open Graph {label} is missing.",
                     f"Add the {label} tag: shared links then carry an image and a real title.")
    if meta.get("og_image") and not meta.get("og_image_alt"):
        _finding(findings, "social", "notice", "og.image_alt_missing", 1,
                 "og:image has no og:image:alt.",
                 "Describe the image for screen readers and for cases where it fails to load.")
    if not meta.get("twitter_card"):
        _finding(findings, "social", "notice", "twitter.card_missing", 1,
                 "No twitter:card declared.",
                 "Add twitter:card (summary_large_image for articles) to control the card on X.")
    elif str(meta["twitter_card"]).lower() not in ("summary", "summary_large_image", "app", "player"):
        _finding(findings, "social", "notice", "twitter.card_invalid", 1,
                 f"Unknown twitter:card value: {meta['twitter_card']}.",
                 "Use summary, summary_large_image, app or player.")


def _audit_mobile(findings: list, analysis: dict) -> None:
    mobile = analysis.get("mobile_viewport", {})
    if not mobile.get("has_viewport"):
        _finding(findings, "mobile", "critical", "viewport.missing", 6,
                 "No viewport meta tag: the page renders as a desktop layout on phones.",
                 "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">.")
        return
    if not mobile.get("width_device"):
        _finding(findings, "mobile", "warning", "viewport.width", 3,
                 f"Viewport does not set width=device-width ({mobile.get('content')}).",
                 "Set width=device-width so the layout matches the device instead of the desktop canvas.")
    if mobile.get("user_scalable_disabled"):
        _finding(findings, "mobile", "warning", "viewport.zoom_blocked", 2,
                 "The viewport forbids user zoom (user-scalable=no or maximum-scale=1).",
                 "Let visitors zoom: blocking it fails accessibility checkpoints.")


def _audit_performance(findings: list, analysis: dict) -> None:
    cwv = analysis.get("core_web_vitals", {})
    images = analysis.get("images", {})

    if cwv.get("render_blocking_styles", 0) > 3:
        _finding(findings, "performance", "warning", "perf.blocking_styles", 3,
                 f"{cwv['render_blocking_styles']} stylesheets block rendering.",
                 "Inline the critical CSS and load the rest asynchronously.")
    if cwv.get("render_blocking_scripts", 0) > 2:
        _finding(findings, "performance", "warning", "perf.blocking_scripts", 4,
                 f"{cwv['render_blocking_scripts']} scripts in <head> block rendering.",
                 "Add defer or async, or move them to the end of the body.",
                 {"count": cwv["render_blocking_scripts"]})
    if images.get("without_dimensions"):
        _finding(findings, "performance", "warning", "perf.image_dimensions", 3,
                 f"{images['without_dimensions']} images have no width/height.",
                 "Set the intrinsic dimensions: the browser then reserves space and the layout stops jumping (CLS).")
    if images.get("total", 0) >= 10 and images.get("lazy", 0) == 0:
        _finding(findings, "performance", "notice", "perf.lazy_loading", 2,
                 f"{images['total']} images, none lazy-loaded.",
                 "Add loading=\"lazy\" to images below the fold.")
    if cwv.get("dom_nodes", 0) > 3000:
        _finding(findings, "performance", "warning", "perf.dom_huge", 4,
                 f"{cwv['dom_nodes']} DOM nodes — well past the ~1500 recommended.",
                 "Simplify the markup or virtualise long lists.", {"dom_nodes": cwv["dom_nodes"]})
    elif cwv.get("dom_nodes", 0) > 1500:
        _finding(findings, "performance", "notice", "perf.dom_large", 2,
                 f"{cwv['dom_nodes']} DOM nodes, above the ~1500 recommended.",
                 "Trim wrapper elements and repeated lists.")
    if cwv.get("inline_script_bytes", 0) > 100_000:
        _finding(findings, "performance", "notice", "perf.inline_js", 2,
                 f"{cwv['inline_script_bytes'] // 1024} KB of inline JavaScript.",
                 "Extract it into cacheable files: inline code is re-downloaded on every page.")
    if cwv.get("inline_style_bytes", 0) > 60_000:
        _finding(findings, "performance", "notice", "perf.inline_css", 2,
                 f"{cwv['inline_style_bytes'] // 1024} KB of inline CSS.",
                 "Move it to a stylesheet so browsers can cache it.")
    third_party = cwv.get("third_party_hosts") or []
    if len(third_party) >= 5:
        _finding(findings, "performance", "notice", "perf.third_party", 2,
                 f"Assets come from {len(third_party)} third-party hosts.",
                 "Each host costs a DNS lookup and a connection: self-host or remove.",
                 {"hosts": [entry["host"] for entry in third_party[:5]]})
    elif third_party and not cwv.get("preconnect"):
        _finding(findings, "performance", "notice", "perf.preconnect", 1,
                 "Third-party assets are loaded without preconnect.",
                 "Add <link rel=\"preconnect\"> for the critical third-party origins.")
    if cwv.get("lcp") == "poor":
        _finding(findings, "performance", "warning", "perf.lcp", 3,
                 "Rendering signals suggest a poor Largest Contentful Paint.",
                 "Compress the main image, remove render-blocking resources.")
    elif cwv.get("lcp") == "needs improvement":
        _finding(findings, "performance", "notice", "perf.lcp_improve", 2,
                 "Rendering signals suggest LCP needs improvement.",
                 "Trim the critical path: smaller hero image, fewer blocking resources.")
    if cwv.get("cls") == "poor":
        _finding(findings, "performance", "warning", "perf.cls", 3,
                 "Rendering signals suggest a poor Cumulative Layout Shift.",
                 "Reserve space for images, ads and embeds.")
    if analysis.get("html_bytes", 0) > 500_000:
        _finding(findings, "performance", "warning", "perf.html_size", 3,
                 f"HTML document is {analysis['html_bytes'] // 1024} KB.",
                 "Aim for under ~100 KB of HTML; move data out of the markup.")


def _audit_media(findings: list, analysis: dict) -> None:
    images = analysis.get("images", {})
    total = images.get("total", 0)
    if not total:
        return
    ratio = images.get("without_alt", 0) / total
    if images.get("without_alt"):
        severity = "critical" if ratio > 0.5 else "warning"
        _finding(findings, "media", severity, "images.alt", 6 if severity == "critical" else 4,
                 f"{images['without_alt']} of {total} images have no alt text"
                 f" ({round(ratio * 100)}%).",
                 "Describe each content image; use an empty alt only for decoration.",
                 {"examples": images.get("examples_missing_alt", [])[:3]})
    if images.get("legacy_format"):
        _finding(findings, "media", "notice", "images.format", 2,
                 f"{images['legacy_format']} images are not WebP/AVIF.",
                 "Serve modern formats: typically 25-50% smaller for the same quality.")
    if total >= 5 and images.get("with_srcset", 0) == 0:
        _finding(findings, "media", "notice", "images.srcset", 1,
                 "No responsive images (srcset/sizes).",
                 "Provide several widths so phones do not download desktop-size images.")
    if images.get("data_uri", 0) >= 5:
        _finding(findings, "media", "notice", "images.data_uri", 1,
                 f"{images['data_uri']} images are inlined as data URIs.",
                 "Inline only tiny icons: data URIs block caching and inflate the HTML.")


def audit(analysis: dict) -> dict:
    """Run every rule group and compute the weighted score."""
    findings: list = []
    _audit_content(findings, analysis)
    _audit_indexability(findings, analysis)
    _audit_structure(findings, analysis)
    _audit_social(findings, analysis)
    _audit_mobile(findings, analysis)
    _audit_performance(findings, analysis)
    _audit_media(findings, analysis)

    categories = {}
    for category, weight in CATEGORY_WEIGHTS.items():
        lost = sum(f["impact"] for f in findings if f["category"] == category)
        categories[category] = {
            "score": max(0, weight - lost),
            "max": weight,
            "lost": lost,
            "issues": sum(1 for f in findings if f["category"] == category),
        }
    score = sum(entry["score"] for entry in categories.values())
    counts = {"critical": 0, "warning": 0, "notice": 0}
    for finding in findings:
        counts[finding["severity"]] += 1
    findings.sort(key=lambda f: (SEVERITY_ORDER[f["severity"]], -f["impact"], f["rule"]))

    if counts["critical"]:
        summary = (f"{counts['critical']} critical issue(s) block this page from ranking well, "
                   f"{counts['warning']} warning(s) and {counts['notice']} notice(s).")
    elif counts["warning"]:
        summary = (f"No blocking issue, but {counts['warning']} warning(s) and "
                   f"{counts['notice']} notice(s) hold the score at {score}/100.")
    elif counts["notice"]:
        summary = f"Solid page: {counts['notice']} minor notice(s), score {score}/100."
    else:
        summary = f"No issue found by ruleset {RULESET_VERSION}: score {score}/100."

    return {
        "score": score,
        "grade": _grade(score),
        "max_score": 100,
        "ruleset": RULESET_VERSION,
        "summary": summary,
        "counts": counts,
        "issues_total": len(findings),
        "categories": categories,
        "issues": findings,
    }


def rules_catalog() -> list:
    """Documented rule set, exposed at /api/seo/rules so clients can explain every point."""
    catalog = [
        ("content.title.missing", "content", "critical", "Page has a <title>."),
        ("content.title.length", "content", "warning", "Title is 30-60 characters."),
        ("content.description.missing", "content", "critical", "Meta description exists."),
        ("content.description.length", "content", "warning", "Description is 120-160 characters."),
        ("content.thin", "content", "critical", "At least 300 words of visible text."),
        ("content.readability", "content", "warning", "Reads at US grade 6-10."),
        ("indexability.robots.noindex", "indexability", "critical", "Page is indexable."),
        ("indexability.canonical", "indexability", "warning", "Absolute, self-referencing canonical."),
        ("indexability.html.lang", "indexability", "warning", "Language declared on <html>."),
        ("indexability.hreflang", "indexability", "notice", "hreflang set is absolute and has x-default."),
        ("structure.h1", "structure", "critical", "Exactly one H1."),
        ("structure.headings.order", "structure", "notice", "Heading levels are sequential."),
        ("structure.links.internal", "structure", "warning", "At least 3 internal links."),
        ("structure.links.anchors", "structure", "notice", "Every link has anchor text."),
        ("structure.schema", "structure", "warning", "Valid JSON-LD with the properties Google needs."),
        ("social.og", "social", "warning", "og:title, og:description and og:image present."),
        ("social.twitter", "social", "notice", "Valid twitter:card."),
        ("mobile.viewport", "mobile", "critical", "width=device-width viewport, zoom allowed."),
        ("performance.blocking", "performance", "warning", "No render-blocking head resources."),
        ("performance.cls", "performance", "warning", "Images have intrinsic dimensions."),
        ("performance.dom", "performance", "notice", "DOM under ~1500 nodes."),
        ("performance.weight", "performance", "notice", "Bounded inline code and HTML size."),
        ("media.alt", "media", "warning", "Images carry alt text."),
        ("media.formats", "media", "notice", "WebP/AVIF images with srcset."),
    ]
    return [
        {"rule": rule, "category": category, "severity": severity, "check": check,
         "weight": CATEGORY_WEIGHTS[category]}
        for rule, category, severity, check in catalog
    ]
