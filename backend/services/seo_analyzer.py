"""On-page SEO extraction.

Design rule: extraction never modifies the document. The previous version decomposed
`script`, `style`, `nav`, `footer` and `header` *before* counting headings, links and
images, so every navigation link (the most valuable internal links on a page) and every
heading inside a header or footer was silently missing from the report, and the page
weight was measured on an already-trimmed tree. Boilerplate is now skipped only when
building the visible text.
"""

import json
import re
from collections import Counter
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# Boilerplate: excluded from the *text* used for readability and keywords, never from the
# structural counts.
BOILERPLATE_TAGS = frozenset(
    {"script", "style", "noscript", "template", "svg", "nav", "footer", "header", "aside", "form", "iframe"}
)

MAX_TEXT_CHARS = 120_000
MAX_KEYWORD_CHARS = 60_000

STOP_WORDS = {
    "the", "is", "in", "at", "of", "a", "an", "and", "or", "but", "not",
    "to", "for", "on", "with", "by", "as", "it", "its", "be", "are",
    "was", "were", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "can",
    "shall", "this", "that", "these", "those", "i", "me", "my", "we",
    "our", "you", "your", "he", "she", "him", "her", "they", "them",
    "their", "what", "which", "who", "whom", "when", "where", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "only", "own", "same", "so", "than",
    "too", "very", "just", "because", "about", "into", "through",
    "during", "before", "after", "above", "below", "between", "from",
    "up", "down", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "while", "if", "also", "now",
}

# Properties Google expects on the structured data types that actually earn rich results.
# Missing ones are reported so the report can say what to add, not just "schema present".
SCHEMA_REQUIRED_PROPERTIES = {
    "Article": ("headline", "image", "datePublished", "author"),
    "NewsArticle": ("headline", "image", "datePublished", "author"),
    "BlogPosting": ("headline", "image", "datePublished", "author"),
    "Product": ("name", "image", "offers"),
    "BreadcrumbList": ("itemListElement",),
    "Organization": ("name", "url"),
    "LocalBusiness": ("name", "address"),
    "WebSite": ("name", "url"),
    "WebPage": ("name",),
    "FAQPage": ("mainEntity",),
    "Event": ("name", "startDate", "location"),
    "Recipe": ("name", "image", "recipeIngredient", "recipeInstructions"),
    "VideoObject": ("name", "description", "thumbnailUrl", "uploadDate"),
}


def host_of(value, base_url=None):
    """Hostname of a URL, resolving relative paths against the page URL."""
    if not value:
        return ""
    absolute = urljoin(base_url, value) if base_url else value
    try:
        return (urlparse(absolute).hostname or "").lower()
    except ValueError:
        return ""


def is_absolute(value):
    return bool(value) and bool(urlparse(value).scheme)


def _iter_visible_text(root):
    """Text nodes outside boilerplate tags, without a second BeautifulSoup parse."""
    chunks = []
    stack = [item for item in root.children]
    while stack:
        node = stack.pop()
        name = getattr(node, "name", None)
        if name in BOILERPLATE_TAGS:
            continue
        if name is None:
            text = str(node).strip()
            if text:
                chunks.append(text)
            continue
        stack.extend(list(node.children))
    return " ".join(chunks)


def extract_meta_tags(soup, base_url=None):
    meta = {
        "title": None,
        "title_length": 0,
        "title_words": 0,
        "description": None,
        "description_length": 0,
        "og_title": None,
        "og_description": None,
        "og_image": None,
        "og_image_alt": None,
        "og_type": None,
        "og_url": None,
        "og_site_name": None,
        "twitter_card": None,
        "twitter_title": None,
        "twitter_description": None,
        "twitter_image": None,
        "twitter_site": None,
        "canonical": None,
        "canonical_absolute": False,
        "canonical_self": False,
        "canonical_host": "",
        "robots": None,
        "robots_directives": [],
        "keywords_meta": None,
        "lang": None,
        "charset": None,
        "has_favicon": False,
        "meta_refresh": None,
        "hreflang": [],
    }
    if soup.title is not None:
        title = soup.title.get_text(strip=True)
        meta["title"] = title or None
        meta["title_length"] = len(title)
        meta["title_words"] = len(title.split())
    html_tag = soup.find("html")
    if html_tag is not None:
        meta["lang"] = html_tag.get("lang")
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").strip().lower()
        content = (tag.get("content") or "").strip()
        if name == "description":
            meta["description"] = content
            meta["description_length"] = len(content)
        elif name == "og:title":
            meta["og_title"] = content
        elif name == "og:description":
            meta["og_description"] = content
        elif name == "og:image":
            meta["og_image"] = content
        elif name in ("og:image:alt", "twitter:image:alt"):
            meta["og_image_alt"] = content
        elif name == "og:type":
            meta["og_type"] = content
        elif name == "og:url":
            meta["og_url"] = content
        elif name == "og:site_name":
            meta["og_site_name"] = content
        elif name == "twitter:card":
            meta["twitter_card"] = content
        elif name == "twitter:title":
            meta["twitter_title"] = content
        elif name == "twitter:description":
            meta["twitter_description"] = content
        elif name == "twitter:image":
            meta["twitter_image"] = content
        elif name in ("twitter:site", "twitter:creator"):
            meta["twitter_site"] = content
        elif name == "robots":
            meta["robots"] = content
            meta["robots_directives"] = parse_robots_directives(content)
        elif name == "keywords":
            meta["keywords_meta"] = content
        elif name == "http-equiv" and content.lower().startswith("refresh"):
            meta["meta_refresh"] = content
    if soup.find("meta", attrs={"charset": True}) is not None:
        meta["charset"] = soup.find("meta", attrs={"charset": True}).get("charset")
    refresh_tag = soup.find("meta", attrs={"http-equiv": re.compile("^refresh$", re.I)})
    if refresh_tag is not None:
        meta["meta_refresh"] = refresh_tag.get("content", "")
    canonical_tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    if canonical_tag and canonical_tag.get("href"):
        href = canonical_tag["href"].strip()
        meta["canonical"] = href
        meta["canonical_absolute"] = is_absolute(href)
        meta["canonical_host"] = host_of(href, base_url)
        if base_url:
            meta["canonical_self"] = urljoin(base_url, href).rstrip("/") == str(base_url).rstrip("/")
    if soup.find("link", rel=lambda value: value and "icon" in value) is not None:
        meta["has_favicon"] = True
    for link in soup.find_all("link", rel=lambda value: value and "alternate" in value):
        if link.get("hreflang"):
            meta["hreflang"].append(
                {"lang": link["hreflang"], "href": link.get("href", ""), "host": host_of(link.get("href", ""), base_url)}
            )
    return meta


def parse_robots_directives(value):
    return [part.strip().lower() for part in (value or "").split(",") if part.strip()]


def extract_headings(soup):
    headings = {}
    total = 0
    empty = 0
    levels_seen = []
    for level in range(1, 7):
        tags = soup.find_all(f"h{level}")
        texts = [t.get_text(" ", strip=True) for t in tags]
        blank = sum(1 for text in texts if not text)
        empty += blank
        total += len(tags)
        if tags:
            levels_seen.append(level)
        headings[f"h{level}"] = {
            "count": len(tags),
            "content": [text[:120] for text in texts],
            "empty": blank,
        }
    skipped = []
    for previous, current in zip(levels_seen, levels_seen[1:]):
        if current - previous > 1:
            skipped.append({"from": previous, "to": current})
    headings["total"] = total
    headings["empty"] = empty
    headings["skipped_levels"] = skipped
    headings["levels_used"] = levels_seen
    return headings


def extract_keywords(text, top_n=20):
    """Bag of words over at most MAX_KEYWORD_CHARS.

    The previous implementation generated 5 n-grams per word for the whole page: a
    200k-character article produced a million generator calls and a multi-second CPU spike
    on a public endpoint. The cap keeps quality on normal pages and bounds the worst case.
    """
    words_all = re.findall(r"\b[a-zA-Z][a-zA-Z'-]{2,}\b", (text or "")[:MAX_KEYWORD_CHARS].lower())
    words = [w for w in words_all if w not in STOP_WORDS]
    words = words[:40_000]
    word_freq = Counter(words).most_common(top_n)
    bigrams = Counter()
    trigrams = Counter()
    for index in range(len(words) - 1):
        first, second = words[index], words[index + 1]
        bigrams[f"{first} {second}"] += 1
        if index < len(words) - 2:
            trigrams[f"{first} {second} {words[index + 2]}"] += 1
    return {
        "top_words": [{"word": w, "count": c} for w, c in word_freq],
        "top_2grams": [{"phrase": p, "count": c} for p, c in bigrams.most_common(top_n)],
        "top_3grams": [{"phrase": p, "count": c} for p, c in trigrams.most_common(top_n)],
        "word_count": len(words_all),
    }


def content_stats(text):
    """Word, sentence and paragraph statistics on the visible text."""
    clean = " ".join((text or "").split())
    if not clean:
        return {"word_count": 0, "text_chars": 0, "sentence_count": 0, "avg_sentence_length": 0.0,
                "long_sentences": 0, "paragraph_count": 0}
    words = re.findall(r"[^\W\d_]+", clean, flags=re.UNICODE)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    sentence_count = max(len(sentences), 1)
    avg = len(words) / sentence_count
    long_sentences = sum(1 for s in sentences if len(s.split()) > 25)
    return {
        "word_count": len(words),
        "text_chars": len(clean),
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg, 1),
        "long_sentences": long_sentences,
        "paragraph_count": clean.count("\n") + 1,
    }


def count_syllables(word):
    word = word.lower()
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    count = len(re.findall(r"[aeiouy]{1,2}", word))
    return max(count, 1)


def readability_score(text):
    """Flesch reading ease and the Flesch-Kincaid grade level.

    The previous version labelled reading ease as "flesch_kincaid": the two formulas are
    different, so the reported number was not the grade level it claimed to be. Both are
    now returned explicitly; `flesch_kincaid` is kept for existing clients.
    """
    clean = " ".join((text or "").split())
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", clean) if s.strip()]
    words = re.findall(r"[^\W\d_]+", clean, flags=re.UNICODE)
    word_count = len(words)
    if word_count == 0 or not sentences:
        return {"flesch_kincaid": 0, "reading_ease": 0, "flesch_kincaid_grade": 0,
                "word_count": 0, "sentence_count": 0, "syllable_count": 0, "level": "unknown",
                "avg_sentence_length": 0.0}
    syllables = sum(count_syllables(w) for w in words)
    asl = word_count / len(sentences)
    asw = syllables / word_count
    grade = round(0.39 * asl + 11.8 * asw - 15.59, 1)
    ease = max(0.0, min(100.0, 206.835 - 1.015 * asl - 84.6 * asw))
    return {
        "reading_ease": round(ease, 1),
        # compatibilité : la clé historique portait la lecture facile
        "flesch_kincaid": round(ease, 1),
        "flesch_kincaid_grade": grade,
        "word_count": word_count,
        "sentence_count": len(sentences),
        "syllable_count": syllables,
        "avg_sentence_length": round(asl, 1),
        "level": (
            "very easy" if ease >= 90 else
            "easy" if ease >= 80 else
            "fairly easy" if ease >= 70 else
            "standard" if ease >= 60 else
            "fairly difficult" if ease >= 50 else
            "difficult" if ease >= 30 else
            "very difficult"
        ),
    }


def extract_links(soup, base_url=None):
    """Internal/external split by hostname, plus the quality signals a link audit needs."""
    page_host = host_of(base_url) if base_url else ""
    internal = external = nofollow = empty_anchor = 0
    hash_only = javascript = mailto = 0
    unique_internal = set()
    external_hosts = Counter()
    internal_examples = []
    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue
        low = href.lower()
        if low.startswith("mailto:"):
            mailto += 1
            continue
        if low.startswith("javascript:"):
            javascript += 1
            continue
        if href.startswith("#"):
            hash_only += 1
            continue
        if "nofollow" in (anchor.get("rel") or ""):
            nofollow += 1
        text = anchor.get_text(" ", strip=True)
        if not text and not anchor.find("img"):
            empty_anchor += 1
        target_host = host_of(href, base_url)
        if target_host and page_host and target_host != page_host:
            external += 1
            external_hosts[target_host] += 1
        elif href.startswith("http") and not page_host:
            external += 1
            external_hosts[target_host] += 1
        else:
            internal += 1
            unique_internal.add(urljoin(base_url, href) if base_url else href)
            if len(internal_examples) < 10:
                internal_examples.append({"href": href, "text": text[:80]})
    return {
        "internal": internal,
        "external": external,
        "total": internal + external,
        "nofollow": nofollow,
        "empty_anchor": empty_anchor,
        "hash_only": hash_only,
        "javascript": javascript,
        "mailto": mailto,
        "unique_internal": len(unique_internal),
        "external_hosts": [{"host": h, "count": c} for h, c in external_hosts.most_common(10)],
        "internal_examples": internal_examples,
    }


def extract_images(soup, base_url=None):
    images = soup.find_all("img")
    total = len(images)
    without_alt = empty_alt = no_dimensions = lazy = srcset = data_uri = 0
    legacy = 0
    examples_missing_alt = []
    for img in images:
        if not img.has_attr("alt"):
            without_alt += 1
            if len(examples_missing_alt) < 10:
                examples_missing_alt.append(img.get("src", "")[:120])
        elif not (img.get("alt") or "").strip():
            empty_alt += 1
        if not (img.get("width") and img.get("height")):
            no_dimensions += 1
        if (img.get("loading") or "").lower() == "lazy":
            lazy += 1
        if img.get("srcset"):
            srcset += 1
        src = (img.get("src") or "").strip()
        if src.startswith("data:"):
            data_uri += 1
            continue
        extension = src.split("?")[0].rsplit(".", 1)[-1].lower() if "." in src.split("?")[0] else ""
        if extension and extension not in ("webp", "avif"):
            legacy += 1
    return {
        "total": total,
        "without_alt": without_alt + empty_alt,
        "empty_alt": empty_alt,
        "missing_alt": without_alt,
        "without_dimensions": no_dimensions,
        "with_dimensions": total - no_dimensions,
        "lazy": lazy,
        "with_srcset": srcset,
        "data_uri": data_uri,
        "legacy_format": legacy,
        "examples_missing_alt": examples_missing_alt,
    }


def detect_schema(soup):
    """JSON-LD blocks, validated: context, known types, and the properties Google needs."""
    types = []
    contexts = set()
    invalid = 0
    missing_properties = []
    blocks = 0

    def visit(node):
        nonlocal invalid
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if not isinstance(node, dict):
            return
        if "@graph" in node:
            visit(node["@graph"])
            return
        schema_type = node.get("@type")
        context = node.get("@context")
        if context:
            contexts.add(str(context))
        if not schema_type:
            return
        for single in schema_type if isinstance(schema_type, list) else [schema_type]:
            types.append(single)
            required = SCHEMA_REQUIRED_PROPERTIES.get(single)
            if required:
                absent = [prop for prop in required if prop not in node]
                if absent:
                    missing_properties.append({"type": single, "missing": absent})

    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        blocks += 1
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            invalid += 1
            continue
        visit(data)

    return {
        "has_structured_data": bool(types),
        "types": types,
        "contexts": sorted(contexts),
        "blocks": blocks,
        "invalid_blocks": invalid,
        "missing_properties": missing_properties,
        "uses_schema_org": any("schema.org" in c for c in contexts),
    }


def check_mobile_viewport(soup):
    viewport = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    content = (viewport.get("content") or "") if viewport else ""
    lowered = content.lower().replace(" ", "")
    return {
        "has_viewport": viewport is not None,
        "content": content,
        "width_device": "width=device-width" in lowered,
        "user_scalable_disabled": "user-scalable=no" in lowered or "maximum-scale=1" in lowered,
        "has_initial_scale": "initial-scale" in lowered,
    }


def estimate_core_web_vitals(soup, text, html="", base_url=None):
    """Heuristic rendering signals — NOT field data.

    Kept under its original name for existing clients, but the field names say plainly
    what they are: estimates read from the markup. Real Core Web Vitals come from the
    Chrome UX Report, which needs a separate data source.
    """
    document = html or str(soup)
    dom_size = len(document)
    dom_nodes = len(soup.find_all(True))
    images = soup.find_all("img")
    image_count = len(images)
    images_no_dims = sum(1 for img in images if not (img.get("width") and img.get("height")))
    scripts = soup.find_all("script")
    stylesheets = soup.find_all("link", rel=lambda value: value and "stylesheet" in value)
    iframes = soup.find_all("iframe")
    embeds = soup.find_all("embed")
    head = soup.head
    head_scripts = head.find_all("script") if head else []
    render_blocking_scripts = [
        s for s in head_scripts if not s.get("src") or not (s.get("defer") or s.get("async") or s.get("type") == "module")
    ]
    inline_script_bytes = sum(len(s.get_text() or "") for s in scripts)
    inline_style_bytes = sum(len(s.get_text() or "") for s in soup.find_all("style"))
    page_host = host_of(base_url) if base_url else ""
    third_party = Counter()
    for node in soup.find_all(["script", "link", "img"], src=True):
        host = host_of(node.get("src")) or ""
        if host and page_host and host != page_host:
            third_party[host] += 1
    for node in soup.find_all("link", href=True):
        host = host_of(node.get("href")) or ""
        if host and page_host and host != page_host:
            third_party[host] += 1
    text_length = len(text or "")

    lcp = "good"
    if text_length > 50000 or dom_size > 1000000 or image_count > 20:
        lcp = "needs improvement"
    if text_length > 200000 or dom_size > 5000000 or image_count > 100:
        lcp = "poor"
    fcp = "good"
    if dom_size > 500000 or len(scripts) > 10 or len(stylesheets) > 5:
        fcp = "needs improvement"
    if dom_size > 2000000 or len(scripts) > 30:
        fcp = "poor"
    cls = "good"
    if images_no_dims > 0 or iframes or embeds:
        cls = "needs improvement"
    if images_no_dims > 5 or len(iframes) > 3:
        cls = "poor"
    return {
        "lcp": lcp,
        "fcp": fcp,
        "cls": cls,
        "dom_size_bytes": dom_size,
        "dom_nodes": dom_nodes,
        "image_count": image_count,
        "images_without_dimensions": images_no_dims,
        "scripts_count": len(scripts),
        "stylesheets_count": len(stylesheets),
        "render_blocking_scripts": len(render_blocking_scripts),
        "render_blocking_styles": len(stylesheets),
        "defer_scripts": sum(1 for s in scripts if s.get("defer")),
        "async_scripts": sum(1 for s in scripts if s.get("async")),
        "inline_script_bytes": inline_script_bytes,
        "inline_style_bytes": inline_style_bytes,
        "lazy_images": sum(1 for img in images if (img.get("loading") or "").lower() == "lazy"),
        "preconnect": len(soup.find_all("link", rel=lambda v: v and "preconnect" in v)),
        "preload": len(soup.find_all("link", rel=lambda v: v and "preload" in v)),
        "third_party_hosts": [{"host": h, "count": c} for h, c in third_party.most_common(10)],
        "text_length_chars": text_length,
        "estimate": True,
    }


COMMERCIAL_MODIFIERS = frozenset(
    {"buy", "price", "pricing", "cost", "cheap", "cheapest", "best", "top", "review", "reviews",
     "discount", "deal", "deals", "sale", "near", "vs", "versus", "alternative", "alternatives",
     "comparison", "compare", "trial", "free", "download", "software", "tool", "tools", "service",
     "services", "agency", "consultant", "company", "hire"}
)


def estimate_keyword_difficulty(keyword, url=None):
    """Intrinsic keyword difficulty estimate (no SERP is queried).

    The previous version fetched `google.com/search` with urllib and parsed the result
    count. That is against Google's terms, breaks silently the moment the markup changes,
    and turns a public endpoint into an uncontrolled outbound caller. Real difficulty needs
    a keyword data provider; what is returned here is a transparent estimate built from the
    keyword itself, with `confidence` stating how little it is worth. The UI must never
    present it as measured competition.
    """
    text = (keyword or "").strip()
    words = [w for w in re.split(r"\s+", text) if w]
    lowered = text.lower()
    length_words = len(words)
    length_chars = len(text)
    stop_words = [w for w in words if w.lower() in STOP_WORDS]
    modifiers = sorted({m for m in COMMERCIAL_MODIFIERS if re.search(rf"\b{m}\b", lowered)})

    # Long-tail queries are easier: more words narrow the intent. Commercial modifiers widen
    # the audience and raise the competition. Length caps the score for very short queries.
    word_component = max(0, 45 - (length_words - 1) * 12)
    character_component = min(15, length_chars // 3)
    modifier_component = 30 if modifiers else 15
    intent_bonus = 10 if re.match(r"^(how|what|why|when|where|who|which)\b", lowered) else 0
    density_score = min(40, character_component + intent_bonus)
    competition_score = min(60, modifier_component + word_component)
    difficulty = int(max(0, min(100, density_score + competition_score)))
    if difficulty <= 25:
        band = "easy"
    elif difficulty <= 50:
        band = "moderate"
    elif difficulty <= 75:
        band = "hard"
    else:
        band = "very hard"
    return {
        "score": difficulty,
        "band": band,
        "density_score": density_score,
        "competition_score": competition_score,
        "confidence": "low",
        "basis": {
            "words": length_words,
            "characters": length_chars,
            "stop_words": stop_words,
            "commercial_modifiers": modifiers,
            "queried_serp": False,
            "note": "Estimate from the keyword alone. Connect a keyword data provider for measured competition.",
        },
    }


def format_csv_report(results):
    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["url", "status", "score", "critical_issues", "warnings", "title", "title_length",
                     "description_length", "h1_count", "word_count", "images_total", "images_without_alt",
                     "has_viewport", "has_schema", "flesch_kincaid_grade", "internal_links", "external_links",
                     "lcp", "fcp", "cls"])
    for r in results:
        if r.get("status") != "ok":
            writer.writerow([r.get("url", ""), "error", ""] + [""] * 18)
            continue
        meta = r.get("meta_tags", {})
        headings = r.get("headings", {})
        images = r.get("images", {})
        mobile = r.get("mobile_viewport", {})
        schema = r.get("structured_data", {})
        readability = r.get("readability", {})
        links = r.get("links", {})
        cwv = r.get("core_web_vitals", {})
        audit = r.get("audit", {})
        writer.writerow([
            r.get("url", ""), "ok", r.get("score", ""),
            audit.get("counts", {}).get("critical", 0), audit.get("counts", {}).get("warning", 0),
            meta.get("title", ""), meta.get("title_length", 0), meta.get("description_length", 0),
            headings.get("h1", {}).get("count", 0),
            r.get("content_stats", {}).get("word_count", 0),
            images.get("total", 0), images.get("without_alt", 0),
            mobile.get("has_viewport", False),
            schema.get("has_structured_data", False),
            readability.get("flesch_kincaid_grade", 0),
            links.get("internal", 0), links.get("external", 0),
            cwv.get("lcp", ""), cwv.get("fcp", ""), cwv.get("cls", ""),
        ])
    return output.getvalue()


def compute_seo_score(analysis):
    """Legacy additive score, kept for clients that read `score`.

    New reports use `audit.score`, a weighted score built from the same signals but with a
    category breakdown and an explanation per point. Both are returned.
    """
    score = 0
    meta = analysis.get("meta_tags", {})
    title_length = meta.get("title_length", 0)
    if meta.get("title") and 30 <= title_length <= 65:
        score += 10
    elif meta.get("title"):
        score += 5
    description_length = meta.get("description_length", 0)
    if meta.get("description") and 120 <= description_length <= 160:
        score += 10
    elif meta.get("description"):
        score += 5
    if meta.get("og_title"):
        score += 5
    if meta.get("og_description"):
        score += 5
    if meta.get("og_image"):
        score += 5
    if meta.get("twitter_card"):
        score += 3
    if meta.get("canonical"):
        score += 5
    headings = analysis.get("headings", {})
    h1_count = headings.get("h1", {}).get("count", 0)
    if h1_count == 1:
        score += 10
    elif h1_count > 1:
        score += 5
    images = analysis.get("images", {})
    if images.get("total", 0) > 0:
        ratio = (images["total"] - images["without_alt"]) / images["total"]
        score += max(0, int(ratio * 10))
    if analysis.get("mobile_viewport", {}).get("has_viewport"):
        score += 10
    if analysis.get("structured_data", {}).get("has_structured_data"):
        score += 10
    readability = analysis.get("readability", {})
    fk = readability.get("flesch_kincaid", 0)
    if 60 <= fk <= 70:
        score += 8
    elif 50 <= fk < 60 or 70 < fk:
        score += 4
    links = analysis.get("links", {})
    if links.get("internal", 0) > 0:
        score += min(5, links["internal"])
    cwv = analysis.get("core_web_vitals", {})
    if cwv.get("lcp") == "good":
        score += 3
    if cwv.get("cls") == "good":
        score += 2
    if analysis.get("keywords", {}).get("top_words"):
        score += 3
    return min(100, score)


def analyze_html(html, url=None):
    """Extract every on-page signal. Pure function: the document is never modified."""
    soup = BeautifulSoup(html or "", "html.parser")
    base = url or None
    if base and not is_absolute(base):
        base = None
    text = _iter_visible_text(soup.body or soup)[:MAX_TEXT_CHARS]
    analysis = {
        "url": url,
        "meta_tags": extract_meta_tags(soup, base),
        "headings": extract_headings(soup),
        "keywords": extract_keywords(text),
        "content_stats": content_stats(text),
        "readability": readability_score(text),
        "images": extract_images(soup, base),
        "links": extract_links(soup, base),
        "structured_data": detect_schema(soup),
        "mobile_viewport": check_mobile_viewport(soup),
        "core_web_vitals": estimate_core_web_vitals(soup, text, html, base),
        "html_bytes": len(html or ""),
    }
    return analysis
