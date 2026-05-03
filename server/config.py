import os

JWT_SECRET = "dev_only_super_secret_signing_key_change_me"
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "teladoc-fake-issuer"
JWT_EXPIRES_MINUTES = 60

MAX_EVENT_AMOUNT = 1_000_000_000
MAX_IDEMPOTENCY_KEY_LENGTH = 100
MAX_REASON_LENGTH = 200
MIN_REASON_LENGTH = 10

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@db:5432/teladoc",
)
