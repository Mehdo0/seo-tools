import re
import math
from collections import Counter
from bs4 import BeautifulSoup

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

def extract_meta_tags(soup):
    meta = {
        "title": None,
        "title_length": 0,
        "description": None,
        "description_length": 0,
        "og_title": None,
        "og_description": None,
        "og_image": None,
        "og_type": None,
        "twitter_card": None,
        "twitter_title": None,
        "twitter_description": None,
        "twitter_image": None,
        "canonical": None,
        "robots": None,
    }
    if soup.title and soup.title.string:
        meta["title"] = soup.title.string.strip()
        meta["title_length"] = len(meta["title"])
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").lower()
        content = tag.get("content", "")
        if name == "description":
            meta["description"] = content
            meta["description_length"] = len(content)
        elif name == "og:title":
            meta["og_title"] = content
        elif name == "og:description":
            meta["og_description"] = content
        elif name == "og:image":
            meta["og_image"] = content
        elif name == "og:type":
            meta["og_type"] = content
        elif name == "twitter:card":
            meta["twitter_card"] = content
        elif name == "twitter:title":
            meta["twitter_title"] = content
        elif name == "twitter:description":
            meta["twitter_description"] = content
        elif name == "twitter:image":
            meta["twitter_image"] = content
        elif name == "robots":
            meta["robots"] = content
    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag:
        meta["canonical"] = canonical_tag.get("href")
    return meta


def extract_headings(soup):
    headings = {}
    for level in range(1, 7):
        tags = soup.find_all(f"h{level}")
        headings[f"h{level}"] = {
            "count": len(tags),
            "content": [t.get_text(strip=True)[:120] for t in tags],
        }
    return headings


def extract_keywords(text, top_n=20):
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    words = [w for w in words if w not in STOP_WORDS]
    word_freq = Counter(words).most_common(top_n)
    phrases_2 = Counter(
        " ".join(words[i : i + 2]) for i in range(len(words) - 1)
        if all(w not in STOP_WORDS for w in words[i : i + 2])
    ).most_common(top_n)
    phrases_3 = Counter(
        " ".join(words[i : i + 3]) for i in range(len(words) - 2)
        if all(w not in STOP_WORDS for w in words[i : i + 3])
    ).most_common(top_n)
    return {
        "top_words": [{"word": w, "count": c} for w, c in word_freq],
        "top_2grams": [{"phrase": p, "count": c} for p, c in phrases_2],
        "top_3grams": [{"phrase": p, "count": c} for p, c in phrases_3],
    }


def extract_links(soup, base_url=None):
    internal, external = 0, 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") or href.startswith("javascript") or href.startswith("mailto"):
            continue
        if base_url and base_url in href:
            internal += 1
        elif href.startswith("/") or (base_url is None and not href.startswith("http")):
            internal += 1
        else:
            external += 1
    return {"internal": internal, "external": external, "total": internal + external}


def extract_images(soup):
    images = soup.find_all("img")
    total = len(images)
    without_alt = sum(1 for img in images if not img.get("alt"))
    return {"total": total, "without_alt": without_alt}


def detect_schema(soup):
    schemas = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            import json
            data = json.loads(script.string)
            if isinstance(data, dict):
                schemas.append(data.get("@type", "Unknown"))
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        schemas.append(item.get("@type", "Unknown"))
        except (json.JSONDecodeError, TypeError):
            pass
    return {"has_structured_data": len(schemas) > 0, "types": schemas}


def check_mobile_viewport(soup):
    viewport = soup.find("meta", attrs={"name": "viewport"})
    return {
        "has_viewport": viewport is not None,
        "content": viewport.get("content", "") if viewport else "",
    }


def readability_score(text):
    sentences = max(len(re.split(r"[.!?]+", text)), 1)
    words = re.findall(r"[a-zA-Z]+", text)
    word_count = len(words)
    if word_count == 0:
        return {"flesch_kincaid": 0, "word_count": 0, "sentence_count": 0}
    syllable_count = sum(count_syllables(w) for w in words)
    fk = 206.835 - 1.015 * (word_count / sentences) - 84.6 * (syllable_count / word_count)
    fk = max(0, min(100, fk))
    return {
        "flesch_kincaid": round(fk, 1),
        "word_count": word_count,
        "sentence_count": sentences,
        "syllable_count": syllable_count,
        "level": (
            "very easy" if fk >= 90 else
            "easy" if fk >= 80 else
            "fairly easy" if fk >= 70 else
            "standard" if fk >= 60 else
            "fairly difficult" if fk >= 50 else
            "difficult" if fk >= 30 else
            "very difficult"
        ),
    }


def count_syllables(word):
    word = word.lower()
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    count = len(re.findall(r"[aeiouy]{1,2}", word))
    return max(count, 1)


def compute_seo_score(analysis):
    score = 0
    meta = analysis.get("meta_tags", {})
    if meta.get("title") and 30 <= meta.get("title_length", 0) <= 65:
        score += 10
    elif meta.get("title"):
        score += 5
    if meta.get("description") and 120 <= meta.get("description_length", 0) <= 160:
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
    if headings.get("h1", {}).get("count", 0) == 1:
        score += 10
    elif headings.get("h1", {}).get("count", 0) > 1:
        score += 5
    images = analysis.get("images", {})
    if images.get("total", 0) > 0:
        ratio = (images["total"] - images["without_alt"]) / images["total"]
        score += max(0, int(ratio * 10))
    mobile = analysis.get("mobile_viewport", {})
    if mobile.get("has_viewport"):
        score += 10
    schema = analysis.get("structured_data", {})
    if schema.get("has_structured_data"):
        score += 10
    readability = analysis.get("readability", {})
    fk = readability.get("flesch_kincaid", 0)
    if 60 <= fk <= 70:
        score += 8
    elif 50 <= fk or 70 <= fk:
        score += 4
    links = analysis.get("links", {})
    if links.get("internal", 0) > 0:
        score += min(5, links["internal"])
    keywords = analysis.get("keywords", {})
    if keywords.get("top_words"):
        score += 3
    return min(100, score)


def analyze_html(html, url=None):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    body = soup.body
    text = body.get_text(separator=" ", strip=True) if body else ""
    return {
        "url": url,
        "meta_tags": extract_meta_tags(soup),
        "headings": extract_headings(soup),
        "keywords": extract_keywords(text),
        "readability": readability_score(text),
        "images": extract_images(soup),
        "links": extract_links(soup, url),
        "structured_data": detect_schema(soup),
        "mobile_viewport": check_mobile_viewport(soup),
    }
