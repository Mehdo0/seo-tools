import os, secrets
from pathlib import Path
from pydantic_settings import BaseSettings

SECRET_KEY_FILE = Path(__file__).parent / "data" / ".secret_key"


def _load_or_create_secret_key() -> str:
    env_key = os.getenv("SECRET_KEY", "")
    if env_key:
        return env_key
    if SECRET_KEY_FILE.exists():
        return SECRET_KEY_FILE.read_text().strip()
    key = secrets.token_hex(32)
    SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_KEY_FILE.write_text(key)
    return key


class Settings(BaseSettings):
    app_name: str = "SEO Tools API"
    debug: bool = False
    secret_key: str = _load_or_create_secret_key()
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./seo_tools.db")
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_publishable_key: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    stripe_webhook_secret: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    stripe_price_id: str = os.getenv("STRIPE_PRICE_ID", "")
    frontend_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    cors_origins: list = ["chrome-extension://*", "http://localhost:3000", "http://localhost:5173", "https://hernestagent.duckdns.org"]
    rate_limit_requests: int = 60
    rate_limit_window: int = 60
    playwright_headless: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
