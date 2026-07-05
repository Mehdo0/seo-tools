from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from api.auth import get_current_user
from services.scraper_engine import scraper

router = APIRouter(prefix="/api/scraping", tags=["scraping"])


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
        result = await scraper.scrape_product(req.url, req.selectors)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.post("/competitors")
async def scrape_competitors(req: CompetitorRequest, user: dict = Depends(get_current_user)):
    if not req.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    if len(req.urls) > 10:
        raise HTTPException(status_code=400, detail="Max 10 URLs per request")
    try:
        result = await scraper.scrape_competitors(req.urls, req.selectors)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.post("/price-history")
async def price_history(req: PriceHistoryRequest, user: dict = Depends(get_current_user)):
    try:
        result = await scraper.price_history(req.url, req.selectors)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@router.post("/export")
async def export_data(req: ExportRequest, user: dict = Depends(get_current_user)):
    try:
        result = await scraper.export_data(req.data, req.format)
        return {"format": req.format, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
