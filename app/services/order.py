import json


async def list_orders(db, page=1, size=20, start_date=None, end_date=None, restaurant=None):
    conditions, params = [], []
    if start_date:
        conditions.append("order_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("order_date <= ?")
        params.append(end_date)
    if restaurant:
        conditions.append("restaurant LIKE ?")
        params.append(f"%{restaurant}%")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    cursor = await db.execute(f"SELECT COUNT(*) as cnt FROM orders {where}", params)
    total = (await cursor.fetchone())["cnt"]

    offset = (page - 1) * size
    cursor = await db.execute(
        f"SELECT * FROM orders {where} ORDER BY order_date DESC LIMIT ? OFFSET ?",
        params + [size, offset],
    )
    orders = list(await cursor.fetchall())

    for order in orders:
        cursor = await db.execute(
            "SELECT * FROM order_dishes WHERE order_id = ?", (order["id"],)
        )
        order["dishes"] = list(await cursor.fetchall())

    return {"items": orders, "total": total, "page": page, "size": size}


async def get_order(db, order_id: int):
    cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = await cursor.fetchone()
    if not order:
        return None
    order = dict(order)
    cursor = await db.execute(
        "SELECT * FROM order_dishes WHERE order_id = ?", (order_id,)
    )
    order["dishes"] = list(await cursor.fetchall())
    return order


async def create_order(db, restaurant, order_date, address=None,
                       mood_user1=None, mood_user2=None, notes=None, dishes=None):
    cursor = await db.execute(
        "INSERT INTO orders (restaurant, address, order_date, mood_user1, mood_user2, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (restaurant, address, order_date, mood_user1, mood_user2, notes),
    )
    order_id = cursor.lastrowid
    for dish in (dishes or []):
        await db.execute(
            "INSERT INTO order_dishes (order_id, dish_name, price, ordered_by, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (order_id, dish["name"], dish.get("price"), dish.get("ordered_by"), dish.get("notes")),
        )
    await db.commit()
    return order_id


async def update_order(db, order_id: int, **kwargs):
    dishes = kwargs.pop("dishes", None)
    moods = kwargs.pop("moods", None)
    fields, values = [], []
    for col in ("restaurant", "address", "notes"):
        if kwargs.get(col) is not None:
            fields.append(f"{col} = ?")
            values.append(kwargs[col])
    if kwargs.get("date") is not None:
        fields.append("order_date = ?")
        values.append(kwargs["date"])
    if moods:
        if moods.get("user1") is not None:
            fields.append("mood_user1 = ?")
            values.append(moods["user1"])
        if moods.get("user2") is not None:
            fields.append("mood_user2 = ?")
            values.append(moods["user2"])
    if fields:
        values.append(order_id)
        await db.execute(f"UPDATE orders SET {', '.join(fields)} WHERE id = ?", values)
    if dishes is not None:
        await db.execute("DELETE FROM order_dishes WHERE order_id = ?", (order_id,))
        for dish in dishes:
            await db.execute(
                "INSERT INTO order_dishes (order_id, dish_name, price, ordered_by, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                (order_id, dish["name"], dish.get("price"), dish.get("ordered_by"), dish.get("notes")),
            )
    await db.commit()


async def delete_order(db, order_id: int):
    await db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    await db.commit()


async def validate_dishes(db, dishes: list):
    conflicts = []
    for dish in dishes:
        user_ids = []
        if dish.get("ordered_for"):
            user_ids = [dish["ordered_for"]]
        else:
            cursor = await db.execute("SELECT id FROM users")
            user_ids = [r["id"] for r in await cursor.fetchall()]

        for uid in user_ids:
            cursor = await db.execute(
                "SELECT * FROM user_preferences WHERE user_id = ?", (uid,)
            )
            pref = await cursor.fetchone()
            if not pref or not pref.get("dislikes"):
                continue
            dislikes = json.loads(pref["dislikes"])

            found = [d for d in dislikes if d in dish["name"]]

            cursor = await db.execute(
                "SELECT tag FROM dish_tags WHERE dish_name = ?", (dish["name"],)
            )
            tags = [r["tag"] for r in await cursor.fetchall()]
            found.extend(d for d in dislikes if d in tags and d not in found)

            if found:
                cursor = await db.execute(
                    "SELECT nickname, username FROM users WHERE id = ?", (uid,)
                )
                user = await cursor.fetchone()
                name = (user["nickname"] or user["username"]) if user else str(uid)
                conflicts.append({
                    "dish_name": dish["name"],
                    "user_id": uid,
                    "nickname": name,
                    "conflicts": found,
                })
    return conflicts
