import logging
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Optional

from api.auth import get_current_user
from services.scraper_engine import scraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scraping", tags=["scraping"])

BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",  # private ranges (CIDR prefixes)
}
BLOCKED_SCHEMES = {"file", "ftp", "gopher", "javascript", "data"}


def validate_url(url: str) -> str:
    """Validate URL is safe — block SSRF to internal networks."""
    if not url or not isinstance(url, str):
        raise ValueError("URL is required")
    if len(url) > 2048:
        raise ValueError("URL exceeds maximum length")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Only http/https URLs are allowed, got: {parsed.scheme}")
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL must include a valid hostname")
    # Block localhost and internal IPs
    if hostname in BLOCKED_HOSTS:
        raise ValueError("URL hostname is blocked for security reasons")
    # Check if hostname resolves to a private/internal IP
    try:
        import ipaddress
        import socket
        addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_unspecified:
            raise ValueError("URL resolves to a private/internal IP address")
        if hostname.endswith(".local") or hostname.endswith(".internal"):
            raise ValueError("URL hostname appears to be internal")
    except (socket.gaierror, ValueError):
        raise ValueError("Could not resolve URL hostname")
    return url


class ScrapeRequest(BaseModel):
    url: str
    selectors: Optional[dict] = None


class CompetitorRequest(BaseModel):
    urls: list[str]
    selectors: Optional[dict] = None


class PriceHistoryRequest(BaseModel):
    url: str
    selectors: Optional[dict] = None


class ExportRequest(BaseModel):
    data: list[dict]
    format: str = "json"


@router.post("/product")
async def scrape_product(req: ScrapeRequest, user: dict = Depends(get_current_user)):
    try:
        validated_url = validate_url(req.url)
        result = await scraper.scrape_product(validated_url, req.selectors)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Product scraping failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during scraping")


@router.post("/competitors")
async def scrape_competitors(req: CompetitorRequest, user: dict = Depends(get_current_user)):
    if not req.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    if len(req.urls) > 10:
        raise HTTPException(status_code=400, detail="Max 10 URLs per request")
    try:
        validated_urls = [validate_url(u) for u in req.urls]
        result = await scraper.scrape_competitors(validated_urls, req.selectors)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Competitor scraping failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during scraping")


@router.post("/price-history")
async def price_history(req: PriceHistoryRequest, user: dict = Depends(get_current_user)):
    try:
        validated_url = validate_url(req.url)
        result = await scraper.price_history(validated_url, req.selectors)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Price history scraping failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during scraping")


@router.post("/export")
async def export_data(req: ExportRequest, user: dict = Depends(get_current_user)):
    try:
        result = await scraper.export_data(req.data, req.format)
        return {"format": req.format, "data": result}
    except Exception as e:
        logger.error("Export failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during export")
