

class TestPaymentsStatus:
    def test_status_authenticated_free_user(self, client, auth_headers):
        resp = client.get("/api/payments/status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["premium"] is False

    def test_status_unauthenticated(self, client):
        resp = client.get("/api/payments/status")
        assert resp.status_code == 401


class TestPaymentsConfig:
    def test_config_returns_publishable_key(self, client):
        resp = client.get("/api/payments/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "publishable_key" in data
        assert "price_id" in data


class TestPaymentsCheckout:
    def test_create_checkout_authenticated(self, client, auth_headers, mock_stripe, monkeypatch):
        monkeypatch.setattr("api.payments.settings.stripe_secret_key", "sk_test_dummy")
        resp = client.post("/api/payments/create-checkout", json={
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "url" in data
        assert "session_id" in data

    def test_create_checkout_unauthenticated(self, client):
        resp = client.post("/api/payments/create-checkout", json={
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        })
        assert resp.status_code == 401
