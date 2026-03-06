import json


async def get_user(db, user_id: int):
    cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    return await cursor.fetchone()


async def update_user(db, user_id: int, nickname=None, avatar=None, dingtalk=None, webhookUrl=None):
    fields, values = [], []
    if nickname is not None:
        fields.append("nickname = ?")
        values.append(nickname)
    if avatar is not None:
        fields.append("avatar = ?")
        values.append(avatar)
    if dingtalk is not None:
        fields.append("dingtalk = ?")
        values.append(dingtalk)
    if webhookUrl is not None:
        fields.append("webhookUrl = ?")
        values.append(webhookUrl)
    if not fields:
        return
    values.append(user_id)
    await db.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()


async def get_preferences(db, user_id: int):
    cursor = await db.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row:
        return {
            "user_id": row["user_id"],
            "dislikes": json.loads(row["dislikes"]) if row["dislikes"] else [],
            "likes": json.loads(row["likes"]) if row["likes"] else [],
        }
    return {"user_id": user_id, "dislikes": [], "likes": []}


async def get_partner_id(db, user_id: int):
    cursor = await db.execute("SELECT id FROM users WHERE id != ? LIMIT 1", (user_id,))
    row = await cursor.fetchone()
    return row["id"] if row else None


async def update_preferences(db, user_id: int, dislikes: list, likes: list):
    dislikes_json = json.dumps(dislikes, ensure_ascii=False)
    likes_json = json.dumps(likes, ensure_ascii=False)
    await db.execute(
        """INSERT INTO user_preferences (user_id, dislikes, likes) VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET dislikes = excluded.dislikes, likes = excluded.likes""",
        (user_id, dislikes_json, likes_json),
    )
    await db.commit()
