from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.auth import hash_password, verify_password, create_token
from app.auth_crypto import get_public_key_pem, decrypt_auth_payload
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, ApiResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _resolve_login_payload(req: LoginRequest) -> tuple[str, str]:
    """解析登录数据（仅支持加密）"""
    try:
        data = decrypt_auth_payload(req.encryptedData)
        return data["username"], data["password"]
    except ValueError as e:
        raise HTTPException(400, str(e))


def _resolve_register_payload(req: RegisterRequest) -> tuple[str, str, str | None]:
    """解析注册数据（仅支持加密）"""
    try:
        data = decrypt_auth_payload(req.encryptedData)
        return data["username"], data["password"], data.get("nickname")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/public-key", summary="获取 RSA 公钥（供前端加密）")
async def get_public_key():
    return {"publicKey": get_public_key_pem()}


@router.post("/register", summary="用户注册", response_model=ApiResponse)
async def register(req: RegisterRequest, db=Depends(get_db)):
    username, password, nickname = _resolve_register_payload(req)

    cursor = await db.execute("SELECT COUNT(*) as cnt FROM users")
    if (await cursor.fetchone())["cnt"] >= 2:
        raise HTTPException(403, "已有两名用户，不允许继续注册")

    cursor = await db.execute("SELECT id FROM users WHERE username = ?", (username,))
    if await cursor.fetchone():
        raise HTTPException(400, "用户名已存在")

    pw_hash = hash_password(password)
    cursor = await db.execute(
        "INSERT INTO users (username, password_hash, nickname) VALUES (?, ?, ?)",
        (username, pw_hash, nickname),
    )
    user_id = cursor.lastrowid
    await db.execute("INSERT INTO love_coins (user_id, balance) VALUES (?, 0)", (user_id,))
    await db.commit()

    token = create_token(user_id)
    return ApiResponse(data=TokenResponse(token=token, user_id=user_id).model_dump())


@router.post("/login", summary="用户登录", response_model=ApiResponse)
async def login(req: LoginRequest, db=Depends(get_db)):
    username, password = _resolve_login_payload(req)

    cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = await cursor.fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(401, "用户名或密码错误")

    token = create_token(user["id"])
    return ApiResponse(data=TokenResponse(token=token, user_id=user["id"]).model_dump())
