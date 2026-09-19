"""API behaviour that the previous test suite could not see: history, rules, body cap, SSRF."""

import json


from config import settings
from rate_limit import DEFAULT_LIMIT

MINIMAL_HTML = """<!doctype html><html lang="en"><head><title>%s</title>
<meta name="description" content="%s"></head><body><h1>%s</h1><p>%s</p></body></html>"""


def page(title="A page title long enough to pass the length rule", words=350):
    body = " ".join(["content"] * words)
    return MINIMAL_HTML % (title, "d" * 130, title, body)


def history_rows(email=None):
    import database
    with database._conn() as connection:
        if email:
            rows = connection.execute("SELECT * FROM audit_history WHERE email = ?", (email,)).fetchall()
        else:
            rows = connection.execute("SELECT * FROM audit_history").fetchall()
        return [dict(row) for row in rows]


class TestAnalyzeResponse:
    def test_exposes_audit_and_legacy_score(self, client):
        resp = client.post("/api/seo/analyze", json={"html": page(), "url": "https://example.com/a"})
        assert resp.status_code == 200
        data = resp.json()
        assert 0 <= data["score"] <= 100
        audit = data["audit"]
        assert audit["grade"] in list("ABCDEF")
        assert sum(entry["max"] for entry in audit["categories"].values()) == 100
        assert audit["score"] == sum(entry["score"] for entry in audit["categories"].values())
        assert isinstance(audit["issues"], list)
        for issue in audit["issues"]:
            assert set(issue) >= {"rule", "category", "severity", "impact", "message", "fix"}

    def test_anonymous_analysis_does_not_touch_history(self, client):
        before = len(history_rows())
        client.post("/api/seo/analyze", json={"html": page(), "url": "https://example.com/anon"})
        assert len(history_rows()) == before

    def test_authenticated_analysis_is_stored_for_the_account(self, client, auth_headers):
        me = client.get("/api/auth/me", headers=auth_headers).json()
        email = me["email"]
        assert history_rows(email) == []
        client.post("/api/seo/analyze", json={"html": page(), "url": "https://example.com/tracked"},
                    headers=auth_headers)
        rows = history_rows(email)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://example.com/tracked"
        stored = json.loads(rows[0]["analysis"])
        assert set(stored) == {"url", "score", "audit"}
        assert stored["audit"]["counts"] is not None

    def test_history_endpoint_returns_the_stored_audit(self, client, auth_headers):
        client.post("/api/seo/analyze", json={"html": page(), "url": "https://example.com/hist"},
                    headers=auth_headers)
        resp = client.get("/api/seo/history", headers=auth_headers)
        assert resp.status_code == 200
        entries = resp.json()
        assert entries and entries[0]["url"] == "https://example.com/hist"


class TestRulesEndpoint:
    def test_lists_categories_and_weights(self, client):
        resp = client.get("/api/seo/rules")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ruleset"]
        assert sum(data["categories"].values()) == 100
        assert data["rules"]
        assert {"rule", "category", "severity", "check"} <= set(data["rules"][0])


class TestBodyCap:
    def test_oversized_declared_body_is_refused_before_reading(self, client):
        resp = client.post("/api/seo/analyze", content=b"x" * 32,
                           headers={"content-length": str(settings.max_request_bytes + 1)})
        assert resp.status_code == 413


class TestRateLimitWiring:
    def test_limiter_follows_configuration(self):
        """Le limiteur était figé à 60/minute : la configuration, elle, n'était jamais lue.
        Le harnais pose RATE_LIMIT_REQUESTS très haut — cette valeur doit réellement compter."""
        unit = "minute" if settings.rate_limit_window == 60 else "second"
        assert DEFAULT_LIMIT == f"{settings.rate_limit_requests}/{unit}"
        assert settings.rate_limit_requests == 999999


class TestBatchSsrf:
    def test_private_targets_are_refused(self, client):
        resp = client.post("/api/seo/batch-analyze", json={
            "urls": ["http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/", "file:///etc/passwd"],
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 3
        for entry in results:
            assert entry["status"] == "error"
            assert "Refused" in entry["error"]
