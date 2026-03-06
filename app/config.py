import os

SECRET_KEY = os.getenv("SECRET_KEY", "duodish-secret-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7
DB_PATH = os.getenv("DB_PATH", "duodish.db")
UPLOAD_DIR = "uploads"

LOVE_COIN_PER_ORDER = 10
LOVE_COIN_FOR_PARTNER_DISH = 5

# 认证加密：有效时间窗口（秒），超时拒绝防重放
AUTH_PAYLOAD_TTL_SECONDS = 300

# 钉钉通知消息模板，占位符：{from_nickname} 发送者昵称，{message} 消息内容
DINGTALK_NOTIFY_TEMPLATE = os.getenv(
    "DINGTALK_NOTIFY_TEMPLATE",
    "【DuoDish 通知】{from_nickname} 发来消息：\n\n{message}",
)
