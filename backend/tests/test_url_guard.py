"""URL guard: every case an SSRF attempt would try, and the fetch hardening."""

import asyncio
import socket

import httpx
import pytest

from services.url_guard import (
    CheckedUrl,
    UnsafeUrlError,
    check_redirect,
    check_url,
    fetch_checked,
)

PUBLIC = "93.184.216.34"


@pytest.fixture(autouse=True)
def deterministic_dns(monkeypatch):
    """Résolution fixée : aucun test ne dépend du réseau. Les adresses littérales sont
    traitées comme le fait la libc, pour que le contrôle d'adresse soit réellement exercé
    et pas seulement celui de la résolution."""
    import ipaddress

    def literal(host):
        try:
            return ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            pass
        if host.isdigit() and len(host) <= 10:
            try:
                return ipaddress.ip_address(int(host))
            except ValueError:
                return None
        return None

    def fake_getaddrinfo(host, port, *args, **kwargs):
        address = literal(host)
        if address is not None:
            family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
            entry = (str(address), port or 80, 0, 0) if address.version == 6 else (str(address), port or 80)
            return [(family, socket.SOCK_STREAM, 6, "", entry)]
        if host in ("example.com", "www.example.com", "sub.example.com"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC, port or 443))]
        if host == "internal-ip.example.com":
            # un nom public qui pointe vers une adresse privée
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.7", port or 443))]
        if host == "mixed.example.com":
            # un A public et un AAAA privé : il suffit du second pour passer
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC, port or 443)),
                (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", port or 443, 0, 0)),
            ]
        raise socket.gaierror("nom inconnu")

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


class TestRefusedUrls:
    @pytest.mark.parametrize("url", [
        "http://localhost/admin",
        "http://LOCALHOST/admin",
        "http://localhost.localdomain/",
        "http://127.0.0.1/",
        "http://127.1/",
        "http://2130706433/",
        "http://[::1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://10.0.0.1/",
        "http://192.168.1.10/router",
        "http://172.16.3.4/",
        "http://service.internal/",
        "http://printer.local/",
        "file:///etc/passwd",
        "gopher://example.com/",
        "ftp://example.com/",
        "javascript:alert(1)",
        "http://user:pass@example.com/",
        "https://example.com:22/",
        "https://example.com:6379/",
        "http://internal-ip.example.com/",
        "http://mixed.example.com/",
        "http://unknown-host-xyz.invalid/",
        "",
    ])
    def test_refuses(self, url):
        with pytest.raises(UnsafeUrlError):
            check_url(url)

    def test_refuses_overlong(self):
        with pytest.raises(UnsafeUrlError):
            check_url("https://example.com/" + "a" * 2100)

    def test_message_names_the_reason(self):
        with pytest.raises(UnsafeUrlError) as error:
            check_url("http://169.254.169.254/")
        assert "non-public" in str(error.value) or "blocked" in str(error.value)

    def test_literal_private_ip_is_caught_by_the_address_check(self):
        """127.0.0.1 et sa forme décimale doivent être refusés par le contrôle d'adresse,
        pas seulement parce que le nom ne se résout pas."""
        for url in ("http://127.0.0.1/", "http://2130706433/", "http://[::1]/"):
            with pytest.raises(UnsafeUrlError) as error:
                check_url(url)
            assert "non-public" in str(error.value), (url, str(error.value))


class TestAcceptedUrls:
    def test_https_default_port(self):
        checked = check_url("https://example.com/page")
        assert isinstance(checked, CheckedUrl)
        assert checked.host == "example.com"
        assert checked.port == 443
        assert checked.addresses == (PUBLIC,)

    def test_custom_allowed_port(self):
        assert check_url("http://example.com:8080/").port == 8080

    def test_trailing_dot_host(self):
        assert check_url("https://example.com./").host == "example.com"

    def test_resolution_can_be_skipped(self):
        assert check_url("https://example.com/", resolve=False).addresses == ()


class TestRedirects:
    def test_redirect_to_private_host_is_refused(self):
        with pytest.raises(UnsafeUrlError):
            check_redirect("https://example.com/", "http://127.0.0.1/")

    def test_relative_redirect_is_resolved(self):
        assert check_redirect("https://example.com/a", "/b").url == "https://example.com/b"


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)


class TestFetchChecked:
    def test_follows_public_redirect(self):
        def handler(request):
            if request.url.path == "/start":
                return httpx.Response(302, headers={"location": "/final"})
            return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>ok</html>")

        final, body, content_type, status = asyncio.run(
            fetch_checked("https://example.com/start", client=_client(handler))
        )
        assert status == 200
        assert "ok" in body
        assert content_type == "text/html"
        assert final.endswith("/final")

    def test_refuses_redirect_to_private_host(self):
        def handler(request):
            return httpx.Response(302, headers={"location": "http://10.0.0.5/admin"})

        with pytest.raises(UnsafeUrlError):
            asyncio.run(fetch_checked("https://example.com/start", client=_client(handler)))

    def test_caps_body_size(self):
        def handler(request):
            return httpx.Response(200, headers={"content-type": "text/html"}, content=b"x" * 4096)

        _, body, _, _ = asyncio.run(
            fetch_checked("https://example.com/big", client=_client(handler), max_bytes=1024)
        )
        assert len(body) <= 1024

    def test_gives_up_after_too_many_redirects(self):
        def handler(request):
            return httpx.Response(302, headers={"location": "/loop"})

        with pytest.raises(UnsafeUrlError):
            asyncio.run(fetch_checked("https://example.com/loop", client=_client(handler)))
