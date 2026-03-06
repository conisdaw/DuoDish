"""RSA 加密/解密，用于登录/注册接口传输数据保护"""

import base64
import json
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from app.config import AUTH_PAYLOAD_TTL_SECONDS

# 应用启动时生成密钥对（4096 位提升抗破解强度）
_private_key = None
_public_key_pem = None


def _ensure_keys():
    global _private_key, _public_key_pem
    if _private_key is None:
        _private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend(),
        )
        _public_key_pem = _private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
    return _private_key, _public_key_pem


def get_public_key_pem() -> str:
    """获取 RSA 公钥（PEM 格式），供前端加密使用"""
    _, pem = _ensure_keys()
    return pem


def decrypt_auth_payload(encrypted_base64: str) -> dict:
    """
    解密前端加密的认证数据。
    要求 payload 含 _t（Unix 时间戳），超时拒绝以防重放攻击。
    encrypted_base64: Base64 编码的密文
    返回: {"username": str, "password": str, "nickname": str | None}
    """
    private_key, _ = _ensure_keys()
    try:
        cipher_bytes = base64.b64decode(encrypted_base64)
        plain_bytes = private_key.decrypt(
            cipher_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        data = json.loads(plain_bytes.decode("utf-8"))
        if not isinstance(data, dict) or "username" not in data or "password" not in data:
            raise ValueError("解密结果缺少 username 或 password")

        ts = data.get("_t")
        if ts is None:
            raise ValueError("缺少时间戳 _t，请使用最新版前端加密")
        try:
            ts = int(ts)
        except (TypeError, ValueError):
            raise ValueError("时间戳 _t 格式无效")
        now = int(time.time())
        if abs(now - ts) > AUTH_PAYLOAD_TTL_SECONDS:
            raise ValueError("请求已过期，请重新登录")

        return {k: v for k, v in data.items() if not k.startswith("_")}
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"解密失败: {e}") from e
