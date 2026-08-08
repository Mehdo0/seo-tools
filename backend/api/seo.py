import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

import httpx
from services.seo_analyzer import analyze_html, compute_seo_score, estimate_keyword_difficulty, format_csv_report
from database import save_audit, get_history
from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/seo", tags=["seo"])

MAX_HTML_SIZE = 5 * 1024 * 1024


class AnalyzeRequest(BaseModel):
    url: str = None
    html: str

    @field_validator("html")
    @classmethod
    def validate_html_size(cls, v):
        if len(v.encode("utf-8", errors="replace")) > MAX_HTML_SIZE:
            raise ValueError("HTML content exceeds maximum size of 5 MB")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if v and len(v) > 2048:
            raise ValueError("URL exceeds maximum length of 2048 characters")
        return v


class BatchRequest(BaseModel):
    urls: list[str]
    format: str = "json"

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v):
        if len(v) > 50:
            raise ValueError("Maximum 50 URLs per batch")
        if len(v) == 0:
            raise ValueError("At least one URL required")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v):
        if v not in ("json", "csv"):
            raise ValueError("Format must be json or csv")
        return v


class KeywordDifficultyRequest(BaseModel):
    keyword: str
    url: str = None


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.html or len(req.html.strip()) < 50:
        raise HTTPException(status_code=400, detail="HTML content too short or empty")
    try:
        analysis = analyze_html(req.html, req.url)
        score = compute_seo_score(analysis)
        analysis["score"] = score
        try:
            save_audit("anonymous", req.url or "unknown", score, str(analysis), datetime.utcnow().isoformat())
        except Exception:
            pass
        return analysis
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("SEO analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during analysis")


@router.post("/batch-analyze")
async def batch_analyze(req: BatchRequest):
    results = []
    sem = asyncio.Semaphore(3)

    async def analyze_one(url):
        async with sem:
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(url)
                    html = resp.text
                analysis = analyze_html(html, url)
                analysis["score"] = compute_seo_score(analysis)
                analysis["status"] = "ok"
                return analysis
            except Exception as e:
                return {"url": url, "status": "error", "error": str(e)}

    tasks = [analyze_one(url) for url in req.urls]
    results = await asyncio.gather(*tasks)
    if req.format == "csv":
        return {"csv": format_csv_report(results)}
    return {"total": len(req.urls), "results": results}


@router.post("/keyword-difficulty")
async def keyword_difficulty(req: KeywordDifficultyRequest):
    score = estimate_keyword_difficulty(req.keyword, req.url)
    return {"keyword": req.keyword, "difficulty": score}


@router.get("/history")
async def history(user: dict = Depends(get_current_user)):
    return get_history(user["email"])
