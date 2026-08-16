import os


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


JWT_ALGORITHM = "HS256"
JWT_SECRET_KEY = os.getenv("TRADEPILOT_JWT_SECRET", "development-only-secret-change-before-production")
JWT_EXPIRE_MINUTES = int(os.getenv("TRADEPILOT_JWT_EXPIRE_MINUTES", "60"))
TRADEPILOT_RESET_DEBUG = os.getenv("TRADEPILOT_RESET_DEBUG", "false").lower() == "true"
TRADEPILOT_AI_PROVIDER = os.getenv("TRADEPILOT_AI_PROVIDER", "mock").strip().lower()
TRADEPILOT_AI_API_KEY = os.getenv("TRADEPILOT_AI_API_KEY", "")
TRADEPILOT_AI_MODEL = os.getenv("TRADEPILOT_AI_MODEL", "")
TRADEPILOT_AI_BASE_URL = os.getenv("TRADEPILOT_AI_BASE_URL", "")
TRADEPILOT_AI_TIMEOUT_SECONDS = float(os.getenv("TRADEPILOT_AI_TIMEOUT_SECONDS", "10"))
TRADEPILOT_AI_MAX_RETRIES = max(0, int(os.getenv("TRADEPILOT_AI_MAX_RETRIES", "1")))
TRADEPILOT_AI_RATE_LIMIT = max(1, int(os.getenv("TRADEPILOT_AI_RATE_LIMIT", "30")))
TRADEPILOT_AI_CACHE_TTL_SECONDS = max(1, int(os.getenv("TRADEPILOT_AI_CACHE_TTL_SECONDS", "300")))
TRADEPILOT_ALERT_COOLDOWN_SECONDS = max(1, int(os.getenv("TRADEPILOT_ALERT_COOLDOWN_SECONDS", "3600")))
TRADEPILOT_AUTO_CREATE_SCHEMA = os.getenv("TRADEPILOT_AUTO_CREATE_SCHEMA", "true").lower() == "true"
TRADEPILOT_CACHE_BACKEND = os.getenv("TRADEPILOT_CACHE_BACKEND", "memory").lower()
TRADEPILOT_CORS_ORIGINS = _csv(os.getenv("TRADEPILOT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))
