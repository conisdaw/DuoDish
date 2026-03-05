"""私家厨房服务：菜品、点菜、备菜"""

import json
import sqlite3


async def list_dishes(db, page=1, size=20, keyword=None):
    offset = (page - 1) * size
    params = [size, offset]
    where = ""
    if keyword:
        where = " WHERE d.name LIKE ?"
        params = [f"%{keyword}%", size, offset]

    cursor = await db.execute(
        f"SELECT COUNT(*) as cnt FROM private_kitchen_dishes d{where}",
        params[:-2] if where else [],
    )
    total = (await cursor.fetchone())["cnt"]

    cursor = await db.execute(
        f"""SELECT d.*, u.nickname as creator_nickname
            FROM private_kitchen_dishes d
            LEFT JOIN users u ON d.created_by = u.id
            {where}
            ORDER BY d.updated_at DESC, d.created_at DESC
            LIMIT ? OFFSET ?""",
        params,
    )
    rows = await cursor.fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["images"] = json.loads(item["images"]) if item.get("images") else []
        items.append(await _enrich_dish(db, item, row["id"]))
    return {"items": items, "total": total, "page": page, "size": size}


async def _enrich_dish(db, row, dish_id=None):
    did = dish_id or row.get("id")
    if not did:
        return row
    cursor = await db.execute(
        "SELECT id, name, amount, unit FROM dish_ingredients WHERE dish_id = ? ORDER BY sort_order, id",
        (did,),
    )
    row["ingredients"] = [dict(r) for r in await cursor.fetchall()]
    if "images" not in row or row.get("images") is None:
        cursor = await db.execute("SELECT images FROM private_kitchen_dishes WHERE id = ?", (did,))
        r = await cursor.fetchone()
        row["images"] = json.loads(r["images"]) if r and r.get("images") else []
    return row


async def get_dish(db, dish_id):
    cursor = await db.execute(
        """SELECT d.*, u.nickname as creator_nickname
           FROM private_kitchen_dishes d
           LEFT JOIN users u ON d.created_by = u.id
           WHERE d.id = ?""",
        (dish_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    item = dict(row)
    item["images"] = json.loads(item["images"]) if item.get("images") else []
    return await _enrich_dish(db, item, dish_id)


async def create_dish(db, user_id, name, recipe=None, recipe_url=None, images=None, ingredients=None):
    images_json = json.dumps(images or [], ensure_ascii=False)
    cursor = await db.execute(
        "INSERT INTO private_kitchen_dishes (name, recipe, recipe_url, images, created_by) VALUES (?, ?, ?, ?, ?)",
        (name, recipe, recipe_url, images_json, user_id),
    )
    dish_id = cursor.lastrowid

    for i, ing in enumerate(ingredients or []):
        await db.execute(
            "INSERT INTO dish_ingredients (dish_id, name, amount, unit, sort_order) VALUES (?, ?, ?, ?, ?)",
            (dish_id, ing["name"], ing.get("amount") or "", ing.get("unit") or "", i),
        )
    await db.commit()
    return dish_id


async def update_dish(db, dish_id, name=None, recipe=None, recipe_url=None, images=None, ingredients=None):
    sets, params = [], []
    if name is not None:
        sets.append("name = ?")
        params.append(name)
    if recipe is not None:
        sets.append("recipe = ?")
        params.append(recipe)
    if recipe_url is not None:
        sets.append("recipe_url = ?")
        params.append(recipe_url)
    if images is not None:
        sets.append("images = ?")
        params.append(json.dumps(images, ensure_ascii=False))
    if sets:
        params.append(dish_id)
        await db.execute(f"UPDATE private_kitchen_dishes SET {', '.join(sets)} WHERE id = ?", params)

    if ingredients is not None:
        await db.execute("DELETE FROM dish_ingredients WHERE dish_id = ?", (dish_id,))
        for i, ing in enumerate(ingredients):
            await db.execute(
                "INSERT INTO dish_ingredients (dish_id, name, amount, unit, sort_order) VALUES (?, ?, ?, ?, ?)",
                (dish_id, ing["name"], ing.get("amount") or "", ing.get("unit") or "", i),
            )
    await db.commit()


async def delete_dish(db, dish_id):
    await db.execute("DELETE FROM kitchen_selections WHERE dish_id = ?", (dish_id,))
    await db.execute("DELETE FROM dish_ingredients WHERE dish_id = ?", (dish_id,))
    await db.execute("DELETE FROM private_kitchen_dishes WHERE id = ?", (dish_id,))
    await db.commit()


async def add_selection(db, user_id, dish_id):
    cursor = await db.execute("SELECT id FROM private_kitchen_dishes WHERE id = ?", (dish_id,))
    if not await cursor.fetchone():
        return None, "菜品不存在"
    try:
        cursor = await db.execute(
            "INSERT INTO kitchen_selections (dish_id, selected_by) VALUES (?, ?)",
            (dish_id, user_id),
        )
        await db.commit()
        return cursor.lastrowid, None
    except sqlite3.IntegrityError:
        await db.rollback()
        return None, "该菜品已在制作计划中"


async def list_selections(db):
    """制作接口：当前计划中的所有菜品（含食材、菜谱、图片）"""
    cursor = await db.execute(
        """SELECT s.id as selection_id, s.dish_id, s.selected_by, s.created_at,
                  d.name, d.recipe, d.recipe_url, d.images, d.created_by
           FROM kitchen_selections s
           JOIN private_kitchen_dishes d ON s.dish_id = d.id
           ORDER BY s.created_at"""
    )
    rows = await cursor.fetchall()
    items = []
    for row in rows:
        item = {
            "id": row["selection_id"],
            "dish_id": row["dish_id"],
            "selected_by": row["selected_by"],
            "created_at": row["created_at"],
            "name": row["name"],
            "recipe": row["recipe"],
            "recipe_url": row.get("recipe_url"),
            "images": json.loads(row["images"]) if row.get("images") else [],
        }
        item = await _enrich_dish(db, item, row["dish_id"])
        items.append(item)
    return items


async def remove_selection(db, selection_id):
    cursor = await db.execute("DELETE FROM kitchen_selections WHERE id = ?", (selection_id,))
    await db.commit()
    return cursor.rowcount > 0


async def get_aggregated_ingredients(db):
    """备菜接口：当前计划所有菜品所需食材汇总"""
    cursor = await db.execute(
        """SELECT di.id, di.dish_id, di.name, di.amount, di.unit, d.name as dish_name
           FROM dish_ingredients di
           JOIN kitchen_selections ks ON di.dish_id = ks.dish_id
           JOIN private_kitchen_dishes d ON di.dish_id = d.id
           ORDER BY di.name, di.unit"""
    )
    rows = await cursor.fetchall()

    by_key = {}
    for r in rows:
        name = r["name"]
        unit = r["unit"] or ""
        key = (name, unit)
        amount_str = (r["amount"] or "").strip()
        try:
            val = float(amount_str)
        except (ValueError, TypeError):
            val = None

        if key not in by_key:
            by_key[key] = {"name": name, "unit": unit, "total_numeric": 0.0, "sources": [], "has_non_numeric": False}

        entry = by_key[key]
        entry["sources"].append({"dish_name": r["dish_name"], "amount": amount_str or "—"})
        if val is not None:
            entry["total_numeric"] += val
        else:
            entry["has_non_numeric"] = True

    result = []
    for (name, unit), v in by_key.items():
        item = {"name": name, "unit": unit or None, "sources": v["sources"]}
        if not v["has_non_numeric"] and v["total_numeric"] > 0:
            total = round(v["total_numeric"], 2)
            item["total_numeric"] = total
            amt = str(int(total)) if total == int(total) else str(total)
            item["amount"] = amt + (unit or "")
        elif v["sources"]:
            item["amount"] = "、".join(s["amount"] for s in v["sources"] if s["amount"] != "—") or "—"
        else:
            item["amount"] = "—"
        result.append(item)
    return result
