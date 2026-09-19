import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, field_validator

from config import settings
from rate_limit import limiter
from services.seo_analyzer import analyze_html, compute_seo_score, estimate_keyword_difficulty, format_csv_report
from services.audit import audit, rules_catalog, CATEGORY_WEIGHTS, RULESET_VERSION
from services.url_guard import UnsafeUrlError, fetch_checked
from database import save_audit, get_history
from api.auth import get_current_user, optional_user

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


def history_payload(analysis: dict) -> str:
    """Version courte stockée dans l'historique : le rapport complet pèse des centaines de
    kilo-octets et n'est jamais relu."""
    compact = {
        "url": analysis.get("url"),
        "score": analysis.get("score"),
        "audit": {
            "score": analysis.get("audit", {}).get("score"),
            "grade": analysis.get("audit", {}).get("grade"),
            "counts": analysis.get("audit", {}).get("counts"),
            "summary": analysis.get("audit", {}).get("summary"),
        },
    }
    text = json.dumps(compact)
    return text[: settings.max_history_analysis_chars]


@router.post("/analyze")
@limiter.limit(settings.analyze_rate_limit)
async def analyze(req: AnalyzeRequest, request: Request, user: dict | None = Depends(optional_user)):
    if not req.html or len(req.html.strip()) < 50:
        raise HTTPException(status_code=400, detail="HTML content too short or empty")
    try:
        # L'analyse est purement calculatoire (jusqu'à 5 Mo de HTML) : dans le thread de
        # l'événement, elle bloquait toutes les autres requêtes pendant sa durée.
        analysis = await asyncio.to_thread(analyze_html, req.html, req.url)
        analysis["audit"] = audit(analysis)
        analysis["score"] = compute_seo_score(analysis)
        if user:
            # Historique écrit au nom du compte connecté, pas sous « anonymous ».
            try:
                save_audit(user["email"], req.url or "unknown", analysis["audit"]["score"],
                           history_payload(analysis), datetime.utcnow().isoformat())
            except Exception as exc:
                logger.warning("History not stored for %s: %s", user.get("email"), exc)
        return analysis
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("SEO analysis failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during analysis")


@router.get("/rules")
async def rules():
    """The documented rule set: which categories are scored, how they are weighted, and what
    each rule checks. A report that deducts points must be able to explain them."""
    return {
        "ruleset": RULESET_VERSION,
        "categories": CATEGORY_WEIGHTS,
        "rules": rules_catalog(),
    }


@router.post("/batch-analyze")
@limiter.limit(settings.batch_rate_limit)
async def batch_analyze(req: BatchRequest, request: Request):
    """Analyse several URLs.

    Every hop is validated by `url_guard.fetch_checked`: this endpoint used to fetch any URL
    with httpx and no check whatsoever, which made it a direct SSRF path into the internal
    network (cloud metadata, localhost, RFC1918). The analysis itself runs in a worker
    thread so the event loop keeps serving other requests while a page is parsed.
    """
    sem = asyncio.Semaphore(4)

    async def analyze_one(url):
        async with sem:
            try:
                final_url, html, content_type, status = await fetch_checked(url, timeout=20.0)
                if status >= 400:
                    return {"url": url, "status": "error", "error": f"HTTP {status}"}
                if "html" not in content_type and "xml" not in content_type:
                    return {"url": url, "status": "error", "error": f"Not an HTML document ({content_type})"}
                analysis = await asyncio.to_thread(analyze_html, html, final_url)
                analysis["audit"] = audit(analysis)
                analysis["score"] = compute_seo_score(analysis)
                analysis["status"] = "ok"
                return analysis
            except UnsafeUrlError as exc:
                return {"url": url, "status": "error", "error": f"Refused: {exc}"}
            except Exception as exc:  # réseau, DNS, timeouts
                return {"url": url, "status": "error", "error": str(exc)}

    results = await asyncio.gather(*[analyze_one(url) for url in req.urls])
    if req.format == "csv":
        return {"csv": format_csv_report(results)}
    return {"total": len(req.urls), "results": results}


@router.post("/keyword-difficulty")
@limiter.limit(settings.analyze_rate_limit)
async def keyword_difficulty(req: KeywordDifficultyRequest, request: Request):
    score = estimate_keyword_difficulty(req.keyword, req.url)
    return {"keyword": req.keyword, "difficulty": score}


@router.get("/score")
async def score_deprecated(url: str = ""):
    """Ancien point d'entrée conservé pour ne pas casser les clients : l'analyse se fait
    désormais en POST, avec le HTML de la page (le serveur n'a plus à refetcher l'URL)."""
    raise HTTPException(
        status_code=400,
        detail="Deprecated: POST the page HTML to /api/seo/analyze instead",
    )


@router.get("/history")
async def history(user: dict = Depends(get_current_user)):
    return get_history(user["email"])
