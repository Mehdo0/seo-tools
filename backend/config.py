import os, secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    # pydantic-settings v2 : la classe `Config` imbriquée était ignorée, donc le fichier
    # .env n'était jamais lu — seules les variables d'environnement du processus comptaient.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    # CORS ne connaît pas les jokers de type "chrome-extension://*" : une origine d'extension
    # doit passer par allow_origin_regex, sinon le navigateur rejette la réponse.
    cors_origins: list = ["http://localhost:3000", "http://localhost:5173"]
    cors_origin_regex: str = r"chrome-extension://[a-p]{32}|http://localhost:\d+"
    rate_limit_requests: int = 60
    rate_limit_window: int = 60
    rate_limit_enabled: bool = True
    playwright_headless: bool = True
    # Bornes publiques : une analyse est du calcul pur, on ne laisse pas un client en lancer
    # indéfiniment ni envoyer un document arbitrairement gros.
    analyze_rate_limit: str = "40/minute"
    batch_rate_limit: str = "10/minute"
    scrape_rate_limit: str = "20/minute"
    max_request_bytes: int = 6 * 1024 * 1024
    max_history_analysis_chars: int = 20_000


settings = Settings()
