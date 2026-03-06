"""获取登录 Token（供 test_main.http 等手动测试使用）

用法: python scripts/get_auth_tokens.py [base_url]
输出: token1=xxx 和 token2=xxx，复制到 .http 文件或环境变量
"""
import asyncio
import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import httpx


def encrypt_payload(public_key_pem: str, payload: dict) -> str:
    import time
    data = {**payload, "_t": int(time.time()), "_n": os.urandom(8).hex()}
    pub = serialization.load_pem_public_key(public_key_pem.encode())
    plain = json.dumps(data, ensure_ascii=False).encode("utf-8")
    cipher = pub.encrypt(
        plain,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(cipher).decode("ascii")


async def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{base}/api/auth/public-key")
        r.raise_for_status()
        pem = r.json()["publicKey"]

        for username, password, nickname, token_key in [
            ("alice", "123456", "小爱", "token1"),
            ("bob", "123456", "阿宝", "token2"),
        ]:
            enc_reg = encrypt_payload(pem, {"username": username, "password": password, "nickname": nickname})
            reg = await client.post(f"{base}/api/auth/register", json={"encryptedData": enc_reg})
            if reg.status_code != 200:
                enc_log = encrypt_payload(pem, {"username": username, "password": password})
                log = await client.post(f"{base}/api/auth/login", json={"encryptedData": enc_log})
                log.raise_for_status()
                token = log.json()["data"]["token"]
            else:
                token = reg.json()["data"]["token"]
            print(f"{token_key}={token}")


if __name__ == "__main__":
    asyncio.run(main())
