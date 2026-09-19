import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from api.auth import get_current_user
from services.scraper_engine import scraper
from services.url_guard import check_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scraping", tags=["scraping"])


def validate_url(url: str) -> str:
    """Same guard as every other outbound call.

    The rules used to live here and were weaker than they looked: `gethostbyname` returned a
    single IPv4 answer, the private-range entries were CIDR *strings* ("10.0.0.0/8") that a
    set lookup can never match, any port was accepted, and the resolution happened once —
    the browser resolved the name again when fetching, which is the TOCTOU hole. The shared
    guard checks every resolved address, an explicit port allowlist, credentials and
    internal suffixes, and the scraper re-checks each request inside the browser.
    """
    return check_url(url).url


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
