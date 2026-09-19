import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from rate_limit import limiter
from api import auth, seo, payments, scraping

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from services.scraper_engine import scraper
    await scraper.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Une origine d'extension (chrome-extension://<id>) ne peut pas être comparée à un
    # joker : le middleware fait une égalité stricte, donc "chrome-extension://*" ne
    # correspondait à rien et le navigateur rejetait la réponse.
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def cap_request_body(request: Request, call_next):
    """Refuse un corps trop gros avant de le lire en mémoire.

    La validation de taille sur le HTML s'appliquait après que le corps entier ait été
    chargé : un client pouvait envoyer plusieurs gigaoctets et saturer la mémoire du
    processus avant la moindre vérification.
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > settings.max_request_bytes:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    return await call_next(request)

app.include_router(auth.router)
app.include_router(seo.router)
app.include_router(payments.router)
app.include_router(scraping.router)


@app.get("/upgrade", response_class=HTMLResponse)
@limiter.exempt
async def upgrade_page():
    upgrade_html = STATIC_DIR / "upgrade.html"
    if upgrade_html.exists():
        return upgrade_html.read_text()
    return HTMLResponse("<h1>Upgrade page not found</h1>", status_code=404)


@app.get("/api/health")
@limiter.exempt
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
