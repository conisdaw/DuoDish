import os

SECRET_KEY = os.getenv("SECRET_KEY", "duodish-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7
DB_PATH = os.getenv("DB_PATH", "duodish.db")
UPLOAD_DIR = "uploads"

LOVE_COIN_PER_ORDER = 10
LOVE_COIN_FOR_PARTNER_DISH = 5
