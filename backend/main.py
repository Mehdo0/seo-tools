from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from api import auth, seo, payments, scraping


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_requests}/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(seo.router)
app.include_router(payments.router)
app.include_router(scraping.router)


@app.get("/api/health")
@limiter.exempt
async def health():
    return {"status": "ok", "service": settings.app_name}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
