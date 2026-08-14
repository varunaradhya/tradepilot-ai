import os


JWT_ALGORITHM = "HS256"

JWT_SECRET_KEY = os.getenv(
    "TRADEPILOT_JWT_SECRET",
    "development-only-secret-change-before-production",
)

JWT_EXPIRE_MINUTES = int(
    os.getenv(
        "TRADEPILOT_JWT_EXPIRE_MINUTES",
        "60",
    )
)

TRADEPILOT_AI_PROVIDER = os.getenv(
    "TRADEPILOT_AI_PROVIDER",
    "mock",
).strip().lower()
