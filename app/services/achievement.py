import json


async def list_achievements(db):
    cursor = await db.execute("SELECT * FROM achievements ORDER BY id")
    return list(await cursor.fetchall())


async def get_user_achievements(db, user_id: int):
    cursor = await db.execute(
        """SELECT a.id, a.name, a.description, a.category, a.criteria, a.badge_icon,
                  ua.progress, ua.unlocked_at
           FROM achievements a
           LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
           ORDER BY a.id""",
        (user_id,),
    )
    result = []
    for row in await cursor.fetchall():
        result.append({
            "achievement": {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "criteria": row["criteria"],
                "badge_icon": row["badge_icon"],
            },
            "progress": row["progress"] or 0,
            "unlocked_at": row["unlocked_at"],
        })
    return result


async def check_achievements(db, user_id: int):
    """根据当前数据自动更新成就进度"""
    cursor = await db.execute("SELECT * FROM achievements")
    achievements = await cursor.fetchall()

    for ach in achievements:
        criteria = json.loads(ach["criteria"]) if ach.get("criteria") else {}
        ctype = criteria.get("type", "")
        target = criteria.get("target", 0)
        progress = 0

        if ctype == "order_count":
            c = await db.execute("SELECT COUNT(*) as cnt FROM orders")
            progress = (await c.fetchone())["cnt"]

        elif ctype == "same_restaurant":
            c = await db.execute(
                "SELECT COUNT(*) as cnt FROM orders GROUP BY restaurant ORDER BY cnt DESC LIMIT 1"
            )
            row = await c.fetchone()
            progress = row["cnt"] if row else 0

        elif ctype == "diary_count":
            c = await db.execute("SELECT COUNT(*) as cnt FROM taste_diary")
            progress = (await c.fetchone())["cnt"]

        elif ctype == "guess_win":
            c = await db.execute(
                "SELECT COUNT(*) as cnt FROM price_guess_games WHERE result = ?",
                (f"user{user_id}_win",),
            )
            progress = (await c.fetchone())["cnt"]

        elif ctype == "total_deposit":
            c = await db.execute(
                "SELECT COALESCE(SUM(amount), 0) as total "
                "FROM love_coin_transactions WHERE user_id = ? AND amount > 0",
                (user_id,),
            )
            progress = (await c.fetchone())["total"]

        elif ctype == "new_dish_streak":
            # 简化实现：统计不重复菜品占比
            c = await db.execute(
                "SELECT COUNT(DISTINCT dish_name) as cnt FROM order_dishes"
            )
            progress = (await c.fetchone())["cnt"]

        unlocked_val = 1 if (target > 0 and progress >= target) else 0
        await db.execute(
            """INSERT INTO user_achievements (user_id, achievement_id, progress, unlocked_at)
               VALUES (?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END)
               ON CONFLICT(user_id, achievement_id) DO UPDATE SET
                   progress = excluded.progress,
                   unlocked_at = CASE
                       WHEN user_achievements.unlocked_at IS NOT NULL THEN user_achievements.unlocked_at
                       WHEN excluded.progress >= ? THEN CURRENT_TIMESTAMP
                       ELSE NULL
                   END""",
            (user_id, ach["id"], progress, unlocked_val, target),
        )
    await db.commit()
