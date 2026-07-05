from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from services.seo_analyzer import analyze_html, compute_seo_score

router = APIRouter(prefix="/api/seo", tags=["seo"])


class AnalyzeRequest(BaseModel):
    url: str = None
    html: str


class ScoreRequest(BaseModel):
    url: str


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if not req.html or len(req.html.strip()) < 50:
        raise HTTPException(status_code=400, detail="HTML content too short or empty")
    try:
        analysis = analyze_html(req.html, req.url)
        analysis["score"] = compute_seo_score(analysis)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/score")
async def score(url: str):
    raise HTTPException(
        status_code=400,
        detail="Use POST /api/seo/analyze with HTML content to get a full analysis and score.",
    )
