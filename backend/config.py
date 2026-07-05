import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "SEO Tools API"
    debug: bool = False
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./seo_tools.db")
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_id: str = os.getenv("STRIPE_PRICE_ID", "")
    frontend_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    cors_origins: list = ["http://localhost:3000", "http://localhost:5173"]
    rate_limit_requests: int = 60
    rate_limit_window: int = 60
    playwright_headless: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
