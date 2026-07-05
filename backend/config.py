import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "SEO Tools API"
    debug: bool = False
    secret_key: str = os.getenv("SECRET_KEY", "")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.secret_key:
            import secrets
            import sys
            generated = secrets.token_hex(32)
            print(
                f"WARNING: SECRET_KEY not set. Generated a temporary key: {generated}\n"
                f"This will cause all tokens to be invalidated on restart.\n"
                f"Set the SECRET_KEY environment variable for production use.",
                file=sys.stderr,
            )
            object.__setattr__(self, "secret_key", generated)
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
