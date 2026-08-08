import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator

from services.seo_analyzer import analyze_html, compute_seo_score
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


@router.get("/score")
async def score(url: str):
    raise HTTPException(
        status_code=400,
        detail="Use POST /api/seo/analyze with HTML content to get a full analysis and score.",
    )


@router.get("/history")
async def history(user: dict = Depends(get_current_user)):
    return get_history(user["email"])
