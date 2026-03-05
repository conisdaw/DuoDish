import json


async def list_diaries(db, page=1, size=20):
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM taste_diary")
    total = (await cursor.fetchone())["cnt"]
    offset = (page - 1) * size
    cursor = await db.execute(
        """SELECT d.*, o.restaurant, o.order_date
           FROM taste_diary d JOIN orders o ON d.order_id = o.id
           ORDER BY d.created_at DESC LIMIT ? OFFSET ?""",
        (size, offset),
    )
    items = []
    for row in await cursor.fetchall():
        item = dict(row)
        item["images"] = json.loads(item["images"]) if item.get("images") else []
        items.append(item)
    return {"items": items, "total": total, "page": page, "size": size}


async def get_diary(db, diary_id: int):
    cursor = await db.execute(
        """SELECT d.*, o.restaurant, o.order_date
           FROM taste_diary d JOIN orders o ON d.order_id = o.id
           WHERE d.id = ?""",
        (diary_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    item = dict(row)
    item["images"] = json.loads(item["images"]) if item.get("images") else []
    return item


async def create_diary(db, order_id: int, content=None, rating=None, image_paths=None):
    images_json = json.dumps(image_paths or [], ensure_ascii=False)
    cursor = await db.execute(
        "INSERT INTO taste_diary (order_id, content, images, rating) VALUES (?, ?, ?, ?)",
        (order_id, content, images_json, rating),
    )
    await db.commit()
    return cursor.lastrowid


async def update_diary(db, diary_id: int, content=None, rating=None, images=None):
    sets, params = [], []
    if content is not None:
        sets.append("content = ?")
        params.append(content)
    if rating is not None:
        sets.append("rating = ?")
        params.append(rating)
    if images is not None:
        sets.append("images = ?")
        params.append(json.dumps(images, ensure_ascii=False))
    if not sets:
        return
    params.append(diary_id)
    await db.execute(f"UPDATE taste_diary SET {', '.join(sets)} WHERE id = ?", params)
    await db.commit()


async def get_taste_map(db, restaurant=None):
    conditions, params = [], []
    if restaurant:
        conditions.append("o.restaurant LIKE ?")
        params.append(f"%{restaurant}%")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cursor = await db.execute(
        f"""SELECT o.restaurant, o.address,
                   COUNT(DISTINCT o.id) as visit_count,
                   AVG(d.rating) as avg_rating,
                   MAX(o.order_date) as last_visit
            FROM orders o
            LEFT JOIN taste_diary d ON o.id = d.order_id
            {where}
            GROUP BY o.restaurant
            ORDER BY visit_count DESC""",
        params,
    )
    points = []
    for row in await cursor.fetchall():
        point = dict(row)
        c = await db.execute(
            "SELECT DISTINCT dish_name FROM order_dishes od "
            "JOIN orders o ON od.order_id = o.id WHERE o.restaurant = ?",
            (row["restaurant"],),
        )
        point["dishes"] = [r["dish_name"] for r in await c.fetchall()]
        point["avg_rating"] = round(point["avg_rating"], 1) if point["avg_rating"] else None
        points.append(point)
    return points
