"""The single place where an outbound URL is judged safe.

Why this module exists: three code paths fetched user-supplied URLs and only one of them
checked anything.

- `/api/seo/batch-analyze` fetched arbitrary URLs through httpx with no validation at all —
  a straight SSRF into the internal network (cloud metadata, localhost, RFC1918 ranges).
- The scraping validator resolved a single IPv4 answer with `gethostbyname`, compared the
  hostname against a set that contained CIDR *strings* ("10.0.0.0/8") which equality can
  never match, let any port through, and left the check-then-re-resolve race open: the
  browser resolved the name again at request time, so a DNS record could point at a
  public IP during validation and at 127.0.0.1 during the fetch.

Rules enforced here: http/https only, no credentials in the URL, hostname that is not a
known metadata name or an internal suffix, port from an explicit allowlist, and *every*
resolved address (IPv4 and IPv6) must be public. Validation is re-run on each redirect
hop, and the scraper re-runs it inside the browser on every request, which is what closes
the TOCTOU window.
"""

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

ALLOWED_SCHEMES = ("http", "https")
DEFAULT_PORTS = {"http": 80, "https": 443}
ALLOWED_PORTS = frozenset({80, 443, 3000, 4000, 5000, 8000, 8080, 8443, 9000})
BLOCKED_HOSTNAMES = frozenset({
    "localhost", "localhost.localdomain", "ip6-localhost", "metadata", "instance-data",
    "metadata.google.internal", "metadata.goog",
})
BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost", ".home.arpa", ".in-addr.arpa")
METADATA_ADDRESSES = frozenset({"169.254.169.254", "169.254.170.2", "100.100.100.200"})
MAX_URL_LENGTH = 2048
MAX_REDIRECTS = 5
MAX_BODY_BYTES = 5 * 1024 * 1024


class UnsafeUrlError(ValueError):
    """The URL must not be fetched."""


@dataclass(frozen=True)
class CheckedUrl:
    url: str
    host: str
    port: int
    addresses: tuple


def _public_address(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
        return False
    if ip.is_reserved or ip.is_unspecified:
        return False
    # IPv4-mapped IPv6 (::ffff:127.0.0.1) hides a private address inside a public-looking one.
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return _public_address(str(ip.ipv4_mapped))
    if isinstance(ip, ipaddress.IPv6Address) and ip.is_site_local:
        return False
    return True


def check_url(url, *, allowed_ports=None, resolve=True) -> CheckedUrl:
    """Validate a URL and resolve it. Raises UnsafeUrlError with the reason."""
    if not url or not isinstance(url, str):
        raise UnsafeUrlError("URL is required")
    if len(url) > MAX_URL_LENGTH:
        raise UnsafeUrlError("URL exceeds maximum length")
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise UnsafeUrlError("URL cannot be parsed") from exc
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"Only http/https URLs are allowed, got: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise UnsafeUrlError("Credentials in the URL are not allowed")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if not hostname:
        raise UnsafeUrlError("URL must include a valid hostname")
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(BLOCKED_HOST_SUFFIXES):
        raise UnsafeUrlError("URL hostname is blocked for security reasons")
    try:
        port = parsed.port or DEFAULT_PORTS[scheme]
    except ValueError as exc:
        raise UnsafeUrlError("URL has an invalid port") from exc
    allowlist = frozenset(allowed_ports) if allowed_ports else ALLOWED_PORTS
    if port not in allowlist:
        raise UnsafeUrlError(f"Port {port} is not allowed")
    if not resolve:
        return CheckedUrl(url=url, host=hostname, port=port, addresses=())

    try:
        answers = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeUrlError("Could not resolve URL hostname") from exc
    addresses = tuple(sorted({str(answer[4][0]) for answer in answers}))
    if not addresses:
        raise UnsafeUrlError("Could not resolve URL hostname")
    for address in addresses:
        if address in METADATA_ADDRESSES or not _public_address(address):
            # One private answer is enough to refuse: a host publishing both a public A and a
            # private AAAA record would otherwise be reachable at will.
            raise UnsafeUrlError(f"Hostname resolves to a non-public address ({address})")
    return CheckedUrl(url=url, host=hostname, port=port, addresses=addresses)


def check_redirect(from_url, location) -> CheckedUrl:
    """Follow one redirect hop, re-validating the target."""
    from urllib.parse import urljoin
    target = urljoin(from_url, location or "")
    if not target:
        raise UnsafeUrlError("Redirect without a target")
    return check_url(target)


async def fetch_checked(url, *, client=None, timeout=20.0, max_bytes=MAX_BODY_BYTES, headers=None):
    """GET a URL with every hop validated and a hard cap on the body size.

    Redirects are followed manually: `follow_redirects=True` would hand the decision to the
    HTTP client, which is exactly how an SSRF gets around a single entry check. Returns
    (final_url, text, content_type, status).
    """
    import httpx

    checked = check_url(url)
    owned = client is None
    if owned:
        client = httpx.AsyncClient(timeout=timeout, headers=headers or {
            "User-Agent": "SEOToolsBot/1.0 (+https://github.com/Mehdo0/seo-tools)"
        })
    try:
        current = checked.url
        for _ in range(MAX_REDIRECTS + 1):
            async with client.stream("GET", current) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    if not location:
                        break
                    current = check_redirect(current, location).url
                    continue
                content_type = response.headers.get("content-type", "")
                chunks = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > max_bytes:
                        chunks.append(chunk[: max(0, max_bytes - (total - len(chunk)))])
                        break
                    chunks.append(chunk)
                body = b"".join(chunks)
                encoding = response.encoding or "utf-8"
                return current, body.decode(encoding, errors="replace"), content_type, response.status_code
        raise UnsafeUrlError("Too many redirects")
    finally:
        if owned:
            await client.aclose()
