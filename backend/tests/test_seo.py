import pytest
from fastapi.testclient import TestClient


class TestSEOAnalyzeEndpoint:
    def test_analyze_with_valid_html(self, client):
        html = """
        <html>
        <head><title>Test Page Title</title>
        <meta name="description" content="This is a test description for SEO analysis.">
        </head>
        <body><h1>Main Heading</h1><p>Some paragraph text here for analysis.</p></body>
        </html>
        """
        resp = client.post("/api/seo/analyze", json={"html": html})
        assert resp.status_code == 200
        data = resp.json()
        assert "meta_tags" in data
        assert "headings" in data
        assert "keywords" in data
        assert "readability" in data
        assert "images" in data
        assert "links" in data
        assert "structured_data" in data
        assert "mobile_viewport" in data
        assert "score" in data

    def test_analyze_with_url_param(self, client):
        html = """
        <html>
        <head><title>Test Page</title>
        <meta name="description" content="A test page for SEO analysis with URL.">
        </head>
        <body><h1>Hello</h1><p>Content goes here for testing purposes.</p></body>
        </html>
        """
        resp = client.post("/api/seo/analyze", json={
            "html": html,
            "url": "https://example.com/test"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com/test"

    def test_empty_html_rejected(self, client):
        resp = client.post("/api/seo/analyze", json={"html": ""})
        assert resp.status_code == 400
        assert "too short" in resp.json()["detail"].lower()

    def test_short_html_rejected(self, client):
        resp = client.post("/api/seo/analyze", json={"html": "short"})
        assert resp.status_code == 400
        assert "too short" in resp.json()["detail"].lower()

    def test_missing_html_field(self, client):
        resp = client.post("/api/seo/analyze", json={})
        assert resp.status_code == 422


class TestSEOAnalyzerService:
    def test_extract_meta_tags_title(self):
        from services.seo_analyzer import extract_meta_tags
        from bs4 import BeautifulSoup
        html = "<html><head><title>My Awesome Page</title></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_meta_tags(soup)
        assert meta["title"] == "My Awesome Page"
        assert meta["title_length"] == 15

    def test_extract_meta_tags_description(self):
        from services.seo_analyzer import extract_meta_tags
        from bs4 import BeautifulSoup
        html = '<html><head><meta name="description" content="Page desc"></head><body></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_meta_tags(soup)
        assert meta["description"] == "Page desc"
        assert meta["description_length"] == 9

    def test_extract_meta_tags_og(self):
        from services.seo_analyzer import extract_meta_tags
        from bs4 import BeautifulSoup
        html = """<html><head>
        <meta property="og:title" content="OG Title">
        <meta property="og:description" content="OG Desc">
        <meta property="og:image" content="https://img.com/pic.jpg">
        <meta property="og:type" content="website">
        </head><body></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_meta_tags(soup)
        assert meta["og_title"] == "OG Title"
        assert meta["og_description"] == "OG Desc"
        assert meta["og_image"] == "https://img.com/pic.jpg"
        assert meta["og_type"] == "website"

    def test_extract_meta_tags_twitter(self):
        from services.seo_analyzer import extract_meta_tags
        from bs4 import BeautifulSoup
        html = """<html><head>
        <meta name="twitter:card" content="summary">
        <meta name="twitter:title" content="Tweet Title">
        <meta name="twitter:description" content="Tweet Desc">
        <meta name="twitter:image" content="https://img.com/tweet.jpg">
        </head><body></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_meta_tags(soup)
        assert meta["twitter_card"] == "summary"
        assert meta["twitter_title"] == "Tweet Title"
        assert meta["twitter_description"] == "Tweet Desc"
        assert meta["twitter_image"] == "https://img.com/tweet.jpg"

    def test_extract_meta_tags_canonical(self):
        from services.seo_analyzer import extract_meta_tags
        from bs4 import BeautifulSoup
        html = '<html><head><link rel="canonical" href="https://example.com/page"></head><body></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_meta_tags(soup)
        assert meta["canonical"] == "https://example.com/page"

    def test_extract_meta_tags_robots(self):
        from services.seo_analyzer import extract_meta_tags
        from bs4 import BeautifulSoup
        html = '<html><head><meta name="robots" content="noindex, nofollow"></head><body></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_meta_tags(soup)
        assert meta["robots"] == "noindex, nofollow"

    def test_extract_meta_tags_no_title(self):
        from services.seo_analyzer import extract_meta_tags
        from bs4 import BeautifulSoup
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        meta = extract_meta_tags(soup)
        assert meta["title"] is None
        assert meta["title_length"] == 0

    def test_extract_headings_all_levels(self):
        from services.seo_analyzer import extract_headings
        from bs4 import BeautifulSoup
        html = """<html><body>
        <h1>H1</h1><h1>H1b</h1>
        <h2>H2a</h2><h2>H2b</h2><h2>H2c</h2>
        <h3>H3</h3>
        <h4>H4</h4>
        <h5>H5</h5>
        <h6>H6a</h6><h6>H6b</h6>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        headings = extract_headings(soup)
        assert headings["h1"]["count"] == 2
        assert headings["h2"]["count"] == 3
        assert headings["h3"]["count"] == 1
        assert headings["h4"]["count"] == 1
        assert headings["h5"]["count"] == 1
        assert headings["h6"]["count"] == 2

    def test_extract_headings_empty(self):
        from services.seo_analyzer import extract_headings
        from bs4 import BeautifulSoup
        html = "<html><body><p>No headings here</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        headings = extract_headings(soup)
        for level in range(1, 7):
            assert headings[f"h{level}"]["count"] == 0

    def test_extract_keywords(self):
        from services.seo_analyzer import extract_keywords
        text = "search engine optimization is important for search rankings. engine optimization helps ranking."
        result = extract_keywords(text)
        assert "top_words" in result
        assert "top_2grams" in result
        assert "top_3grams" in result
        assert len(result["top_words"]) > 0

    def test_extract_keywords_stop_words_filtered(self):
        from services.seo_analyzer import extract_keywords
        text = "the and or but not is at in of a an"
        result = extract_keywords(text)
        assert result["top_words"] == []

    def test_extract_keywords_empty_text(self):
        from services.seo_analyzer import extract_keywords
        result = extract_keywords("")
        assert result["top_words"] == []

    def test_extract_links_internal(self):
        from services.seo_analyzer import extract_links
        from bs4 import BeautifulSoup
        html = """<html><body>
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        <a href="https://example.com/page3">Page 3</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        links = extract_links(soup, base_url="https://example.com")
        assert links["internal"] == 3
        assert links["external"] == 0
        assert links["total"] == 3

    def test_extract_links_external(self):
        from services.seo_analyzer import extract_links
        from bs4 import BeautifulSoup
        html = """<html><body>
        <a href="https://other.com">Other</a>
        <a href="https://another.com">Another</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        links = extract_links(soup, base_url="https://example.com")
        assert links["external"] == 2
        assert links["internal"] == 0

    def test_extract_links_skip_special(self):
        from services.seo_analyzer import extract_links
        from bs4 import BeautifulSoup
        html = """<html><body>
        <a href="#section">Anchor</a>
        <a href="javascript:void(0)">JS</a>
        <a href="mailto:test@test.com">Email</a>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        links = extract_links(soup)
        assert links["total"] == 0

    def test_extract_images_with_alt(self):
        from services.seo_analyzer import extract_images
        from bs4 import BeautifulSoup
        html = """<html><body>
        <img src="a.jpg" alt="Image A">
        <img src="b.jpg" alt="Image B">
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images(soup)
        assert images["total"] == 2
        assert images["without_alt"] == 0

    def test_extract_images_without_alt(self):
        from services.seo_analyzer import extract_images
        from bs4 import BeautifulSoup
        html = """<html><body>
        <img src="a.jpg">
        <img src="b.jpg" alt="">
        <img src="c.jpg" alt="Has alt">
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images(soup)
        assert images["total"] == 3
        assert images["without_alt"] == 2

    def test_extract_images_empty(self):
        from services.seo_analyzer import extract_images
        from bs4 import BeautifulSoup
        html = "<html><body><p>No images</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images(soup)
        assert images["total"] == 0

    def test_detect_schema_with_jsonld(self):
        from services.seo_analyzer import detect_schema
        from bs4 import BeautifulSoup
        html = """<html><head>
        <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "Article", "headline": "Test"}
        </script>
        </head><body></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        schema = detect_schema(soup)
        assert schema["has_structured_data"] is True
        assert "Article" in schema["types"]

    def test_detect_schema_none(self):
        from services.seo_analyzer import detect_schema
        from bs4 import BeautifulSoup
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        schema = detect_schema(soup)
        assert schema["has_structured_data"] is False
        assert schema["types"] == []

    def test_check_mobile_viewport_present(self):
        from services.seo_analyzer import check_mobile_viewport
        from bs4 import BeautifulSoup
        html = '<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        vp = check_mobile_viewport(soup)
        assert vp["has_viewport"] is True
        assert "width=device-width" in vp["content"]

    def test_check_mobile_viewport_missing(self):
        from services.seo_analyzer import check_mobile_viewport
        from bs4 import BeautifulSoup
        html = "<html><head></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        vp = check_mobile_viewport(soup)
        assert vp["has_viewport"] is False

    def test_readability_score_normal_text(self):
        from services.seo_analyzer import readability_score
        text = (
            "Search engine optimization is a critical component of digital marketing. "
            "It helps websites rank higher in search results. "
            "Good SEO practices include keyword research and content optimization. "
            "Technical SEO ensures search engines can crawl your site effectively. "
            "Link building remains an important factor for ranking algorithms."
        )
        result = readability_score(text)
        assert "flesch_kincaid" in result
        assert result["word_count"] > 0
        assert result["sentence_count"] > 0
        assert "level" in result

    def test_readability_score_empty(self):
        from services.seo_analyzer import readability_score
        result = readability_score("")
        assert result["flesch_kincaid"] == 0
        assert result["word_count"] == 0

    def test_readability_score_single_word(self):
        from services.seo_analyzer import readability_score
        result = readability_score("Hello.")
        assert result["word_count"] == 1

    def test_count_syllables(self):
        from services.seo_analyzer import count_syllables
        assert count_syllables("hello") == 2
        assert count_syllables("world") == 1
        assert count_syllables("beautiful") >= 2
        assert count_syllables("a") == 1
        assert count_syllables("the") == 1


class TestComputeSEOScore:
    def test_perfect_score(self):
        from services.seo_analyzer import compute_seo_score
        analysis = {
            "meta_tags": {
                "title": "A Perfect Title Tag for SEO",
                "title_length": 50,
                "description": "This description tag is exactly the right length for optimal SEO display in search results pages and provides good value to readers.",
                "description_length": 140,
                "og_title": "OG Title",
                "og_description": "OG Desc",
                "og_image": "https://img.com/pic.jpg",
                "twitter_card": "summary",
                "canonical": "https://example.com",
            },
            "headings": {"h1": {"count": 1, "content": ["Perfect H1"]}},
            "images": {"total": 5, "without_alt": 0},
            "mobile_viewport": {"has_viewport": True},
            "structured_data": {"has_structured_data": True},
            "readability": {"flesch_kincaid": 65},
            "links": {"internal": 10, "external": 3, "total": 13},
            "keywords": {"top_words": [{"word": "test", "count": 5}]},
        }
        score = compute_seo_score(analysis)
        assert score == 99

    def test_empty_analysis(self):
        from services.seo_analyzer import compute_seo_score
        score = compute_seo_score({})
        assert score == 0

    def test_only_title(self):
        from services.seo_analyzer import compute_seo_score
        analysis = {
            "meta_tags": {"title": "Good Title", "title_length": 10},
        }
        score = compute_seo_score(analysis)
        assert score == 5

    def test_multiple_h1_penalty(self):
        from services.seo_analyzer import compute_seo_score
        analysis = {
            "meta_tags": {"title": "Test", "title_length": 4},
            "headings": {"h1": {"count": 3}},
        }
        score = compute_seo_score(analysis)
        assert score == 10

    def test_images_with_missing_alt(self):
        from services.seo_analyzer import compute_seo_score
        analysis = {
            "images": {"total": 4, "without_alt": 2},
        }
        score = compute_seo_score(analysis)
        assert score == 5


class TestRealWorldHTML:
    def test_full_real_world_html(self, client, real_html):
        resp = client.post("/api/seo/analyze", json={
            "html": real_html,
            "url": "https://example.com/seo-guide-2024"
        })
        assert resp.status_code == 200
        data = resp.json()

        meta = data["meta_tags"]
        assert meta["title"] == "The Ultimate Guide to SEO Optimization in 2024"
        assert 30 <= meta["title_length"] <= 65
        assert meta["description"] is not None
        assert meta["og_title"] == "Ultimate SEO Guide 2024"
        assert meta["og_image"] is not None
        assert meta["twitter_card"] == "summary_large_image"
        assert meta["canonical"] == "https://example.com/seo-guide-2024"
        assert meta["robots"] == "index, follow"

        headings = data["headings"]
        assert headings["h1"]["count"] == 1
        assert headings["h2"]["count"] >= 2
        assert headings["h3"]["count"] >= 2

        images = data["images"]
        assert images["total"] == 3
        assert images["without_alt"] == 1

        links = data["links"]
        assert links["internal"] >= 2
        assert links["external"] >= 2

        schema = data["structured_data"]
        assert schema["has_structured_data"] is True

        mobile = data["mobile_viewport"]
        assert mobile["has_viewport"] is True

        assert "keywords" in data
        assert "readability" in data
        assert 0 <= data["score"] <= 100

    def test_malformed_html_recovery(self, client):
        html = "<html><head><title>Broken</title><body><h1>Missing closing tags<p>content</body>"
        resp = client.post("/api/seo/analyze", json={"html": html})
        assert resp.status_code == 200
        data = resp.json()
        assert data["meta_tags"]["title"] == "Broken"
        assert data["headings"]["h1"]["count"] == 1

    def test_large_html(self, client):
        body = "<p>" + "Content paragraph for testing purposes. " * 200 + "</p>"
        html = f"<html><head><title>Large Page</title><meta name='description' content='A large test page with substantial content for analysis.'></head><body>{body}</body></html>"
        resp = client.post("/api/seo/analyze", json={"html": html})
        assert resp.status_code == 200
        data = resp.json()
        assert data["readability"]["word_count"] > 100

    def test_html_with_only_body(self, client):
        html = "<body><h1>Minimal Page</h1><p>Some content here for analysis testing purposes for SEO checker.</p></body>"
        resp = client.post("/api/seo/analyze", json={"html": html})
        assert resp.status_code == 200
        data = resp.json()
        assert data["headings"]["h1"]["count"] == 1
        assert data["meta_tags"]["title"] is None

    def test_score_endpoint_redirects(self, client):
        resp = client.get("/api/seo/score?url=https://example.com")
        assert resp.status_code == 400
        assert "POST" in resp.json()["detail"]
