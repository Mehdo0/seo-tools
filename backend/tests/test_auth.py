import pytest
import time
import jwt
from datetime import datetime, timedelta


class TestRegister:
    def test_register_valid_user(self, client):
        email = f"newuser_{time.time()}@test.com"
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
            "name": "New User",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
        assert data["user"]["name"] == "New User"

    def test_register_duplicate_email(self, client):
        email = f"dup_{time.time()}@test.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
        })
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": "password456",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "short@test.com",
            "password": "123",
        })
        assert resp.status_code == 400
        assert "password" in resp.json()["detail"].lower()

    def test_register_missing_email(self, client):
        resp = client.post("/api/auth/register", json={
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_register_missing_password(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "nopass@test.com",
        })
        assert resp.status_code == 422

    def test_register_empty_name_defaults(self, client):
        email = f"noname_{time.time()}@test.com"
        resp = client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["name"] == ""


class TestLogin:
    def test_login_valid_credentials(self, client):
        email = f"login_{time.time()}@test.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": "securepass123",
            "name": "Login User",
        })
        resp = client.post("/api/auth/login", json={
            "email": email,
            "password": "securepass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email

    def test_login_wrong_password(self, client):
        email = f"wrongpass_{time.time()}@test.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": "correctpassword",
        })
        resp = client.post("/api/auth/login", json={
            "email": email,
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "noone@test.com",
            "password": "password123",
        })
        assert resp.status_code == 401

    def test_login_missing_email(self, client):
        resp = client.post("/api/auth/login", json={
            "password": "password123",
        })
        assert resp.status_code == 422

    def test_login_missing_password(self, client):
        resp = client.post("/api/auth/login", json={
            "email": "someone@test.com",
        })
        assert resp.status_code == 422


class TestMeEndpoint:
    def test_me_with_valid_token(self, client):
        email = f"me_{time.time()}@test.com"
        reg = client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
            "name": "Me User",
        })
        token = reg.json()["access_token"]
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == email
        assert data["name"] == "Me User"

    def test_me_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert resp.status_code == 401

    def test_me_with_malformed_header(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "NotBearer token"})
        assert resp.status_code == 401

    def test_me_with_expired_token(self, client):
        email = f"expired_{time.time()}@test.com"
        reg = client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
        })
        from config import settings
        expire = datetime.utcnow() - timedelta(hours=1)
        payload = {"sub": email, "exp": expire}
        expired_token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_me_with_wrong_secret_token(self, client):
        email = f"wrongsecret_{time.time()}@test.com"
        client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
        })
        expire = datetime.utcnow() + timedelta(hours=1)
        payload = {"sub": email, "exp": expire}
        bad_token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert resp.status_code == 401


class TestTokenStructure:
    def test_token_contains_correct_claims(self, client):
        email = f"claims_{time.time()}@test.com"
        reg = client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
        })
        token = reg.json()["access_token"]
        from config import settings
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == email
        assert "exp" in payload
        expire_time = datetime.utcfromtimestamp(payload["exp"])
        assert expire_time > datetime.utcnow()


class TestHealthEndpoint:
    def test_health_check(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "service" in data
