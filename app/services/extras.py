import base64
import hmac
import json
import random
import time
import urllib.parse
from datetime import date
from typing import Tuple

import httpx

from app.config import DINGTALK_NOTIFY_TEMPLATE


MOOD_TAG_MAP = {
    "冷": ["火锅", "汤", "热饮", "砂锅"],
    "暖": ["分享", "套餐", "家常"],
    "躁": ["冷饮", "凉菜", "清淡", "沙拉"],
    "甜": ["甜品", "蛋糕", "奶茶", "冰淇淋"],
}


async def get_recommendations(db, restaurant=None, exclude=None, mood=None,
                              user_id=None, count=3):
    conditions, params = [], []
    if restaurant:
        conditions.append("o.restaurant = ?")
        params.append(restaurant)
    if exclude:
        placeholders = ",".join("?" * len(exclude))
        conditions.append(f"od.id NOT IN ({placeholders})")
        params.extend(exclude)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cursor = await db.execute(
        f"""SELECT DISTINCT od.dish_name, od.price, o.restaurant,
                   COUNT(*) as order_count
            FROM order_dishes od
            JOIN orders o ON od.order_id = o.id
            {where}
            GROUP BY od.dish_name
            ORDER BY RANDOM()
            LIMIT ?""",
        params + [count * 5],
    )
    candidates = [dict(row) for row in await cursor.fetchall()]

    if user_id:
        cursor = await db.execute(
            "SELECT likes FROM user_preferences WHERE user_id = ?", (user_id,)
        )
        pref = await cursor.fetchone()
        if pref and pref.get("likes"):
            likes = json.loads(pref["likes"])
            for c in candidates:
                c["_score"] = sum(1 for lk in likes if lk in c["dish_name"])
            candidates.sort(key=lambda x: x["_score"], reverse=True)

    if mood and mood in MOOD_TAG_MAP:
        tags = MOOD_TAG_MAP[mood]
        for c in candidates:
            c["_mood"] = sum(1 for t in tags if t in c["dish_name"])
        candidates.sort(key=lambda x: x.get("_mood", 0), reverse=True)

    for c in candidates:
        c.pop("_score", None)
        c.pop("_mood", None)

    result = candidates[:count]
    if not result:
        result = [{"dish_name": "暂无推荐，快去创建第一笔点餐记录吧！", "price": None, "restaurant": None}]
    return result


async def get_surprise_status(db):
    today = date.today()
    cursor = await db.execute("SELECT * FROM anniversaries ORDER BY date")
    rows = await cursor.fetchall()

    for row in rows:
        ann = dict(row)
        try:
            ann_date = date.fromisoformat(ann["date"])
        except (ValueError, TypeError):
            continue
        next_date = ann_date.replace(year=today.year) if ann_date.year != today.year else ann_date
        try:
            if next_date < today:
                next_date = next_date.replace(year=today.year + 1)
        except ValueError:
            continue
        days_until = (next_date - today).days
        remind_days = ann.get("remind_days") or 3

        if 0 <= days_until <= remind_days:
            ann["days_until"] = days_until
            messages = [
                f"🎉 {ann['name']}就要到了！还有{days_until}天",
                f"💕 别忘了，{ann['name']}临近了哦~",
                f"✨ 惊喜模式已激活：{ann['name']}倒计时{days_until}天",
            ]
            return {"active": True, "anniversary": ann, "message": random.choice(messages)}

    return {"active": False, "anniversary": None, "message": None}


async def get_mood_statistics(db, start_date=None, end_date=None):
    conditions, params = [], []
    if start_date:
        conditions.append("order_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("order_date <= ?")
        params.append(end_date)

    conds1 = conditions + ["mood_user1 IS NOT NULL"]
    where1 = f"WHERE {' AND '.join(conds1)}"
    cursor = await db.execute(
        f"SELECT mood_user1 as mood, COUNT(*) as count FROM orders {where1} GROUP BY mood_user1",
        params,
    )
    user1_stats = list(await cursor.fetchall())

    conds2 = conditions + ["mood_user2 IS NOT NULL"]
    where2 = f"WHERE {' AND '.join(conds2)}"
    cursor = await db.execute(
        f"SELECT mood_user2 as mood, COUNT(*) as count FROM orders {where2} GROUP BY mood_user2",
        params,
    )
    user2_stats = list(await cursor.fetchall())

    return {"user1": user1_stats, "user2": user2_stats}


async def get_dashboard(db):
    from app.services.anniversary import list_anniversaries
    from app.services.order import list_orders

    upcoming = await list_anniversaries(db, upcoming_only=True, days=30)

    cursor = await db.execute("SELECT user_id, balance FROM love_coins")
    balances = list(await cursor.fetchall())

    orders_data = await list_orders(db, page=1, size=5)

    cursor = await db.execute(
        """SELECT a.name, a.badge_icon, ua.unlocked_at, ua.user_id
           FROM user_achievements ua
           JOIN achievements a ON ua.achievement_id = a.id
           WHERE ua.unlocked_at IS NOT NULL
           ORDER BY ua.unlocked_at DESC LIMIT 5"""
    )
    achievements = list(await cursor.fetchall())

    cursor = await db.execute("SELECT COUNT(*) as cnt FROM orders")
    total_orders = (await cursor.fetchone())["cnt"]
    cursor = await db.execute("SELECT COUNT(DISTINCT restaurant) as cnt FROM orders")
    total_restaurants = (await cursor.fetchone())["cnt"]

    return {
        "upcoming_anniversaries": upcoming,
        "love_coin_balances": balances,
        "recent_orders": orders_data["items"],
        "latest_achievements": achievements,
        "total_orders": total_orders,
        "total_restaurants": total_restaurants,
    }


def _dingtalk_sign(secret: str) -> Tuple[str, str]:
    """钉钉 webhook 加签：返回 (timestamp, sign)"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode("utf-8")
    string_to_sign = f"{timestamp}\n{secret}"
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod="sha256").digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


async def send_notification(db, from_user_id: int, message: str) -> dict:
    """
    向另一名用户发送钉钉通知。
    从被通知方的 user 记录读取 dingtalk（加签密钥）、webhookUrl，使用加签推送。
    """
    from app.services import user as user_svc

    partner_id = await user_svc.get_partner_id(db, from_user_id)
    if not partner_id:
        raise ValueError("未找到对方用户")

    partner = await user_svc.get_user(db, partner_id)
    if not partner:
        raise ValueError("对方用户不存在")

    webhook_url = (partner.get("webhookUrl") or "").strip()
    dingtalk = (partner.get("dingtalk") or "").strip()  # dingtalk 即加签密钥

    if not webhook_url:
        raise ValueError("对方未配置 webhookUrl，无法发送通知")

    if not dingtalk:
        raise ValueError("对方未配置 dingtalk（加签密钥），无法发送通知")

    from_user = await user_svc.get_user(db, from_user_id)
    from_nickname = (from_user.get("nickname") or from_user.get("username") or "用户") if from_user else "用户"

    content = DINGTALK_NOTIFY_TEMPLATE.format(from_nickname=from_nickname, message=message)

    timestamp, sign = _dingtalk_sign(dingtalk)
    sep = "&" if "?" in webhook_url else "?"
    signed_url = f"{webhook_url}{sep}timestamp={timestamp}&sign={sign}"

    payload = {
        "msgtype": "text",
        "text": {"content": content},
        "at": {"isAtAll": False},
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(signed_url, json=payload)
    result = resp.json()

    if resp.status_code != 200 or result.get("errcode", -1) != 0:
        errmsg = result.get("errmsg", resp.text)
        raise ValueError(f"钉钉推送失败: {errmsg}")

    return {"success": True, "errcode": 0}
