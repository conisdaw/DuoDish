async def get_balance(db, user_id: int) -> int:
    cursor = await db.execute("SELECT balance FROM love_coins WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    return row["balance"] if row else 0


async def _add_transaction(db, user_id: int, amount: int, tx_type: str,
                           reference_id=None, description=None):
    """写入流水并更新余额（不提交，由调用方统一提交）"""
    await db.execute(
        "INSERT OR IGNORE INTO love_coins (user_id, balance) VALUES (?, 0)", (user_id,)
    )
    await db.execute(
        "UPDATE love_coins SET balance = balance + ? WHERE user_id = ?", (amount, user_id)
    )
    await db.execute(
        "INSERT INTO love_coin_transactions (user_id, amount, type, reference_id, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, tx_type, reference_id, description),
    )


async def deposit(db, user_id: int, amount: int, tx_type: str,
                  reference_id=None, description=None):
    await _add_transaction(db, user_id, amount, tx_type, reference_id, description)
    await db.commit()


async def get_transactions(db, user_id: int, page=1, size=20):
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM love_coin_transactions WHERE user_id = ?", (user_id,)
    )
    total = (await cursor.fetchone())["cnt"]
    offset = (page - 1) * size
    cursor = await db.execute(
        "SELECT * FROM love_coin_transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, size, offset),
    )
    return {"items": list(await cursor.fetchall()), "total": total, "page": page, "size": size}


async def list_redeem_items(db):
    cursor = await db.execute(
        "SELECT * FROM redeem_items WHERE is_active = 1 ORDER BY star_level, cost"
    )
    return list(await cursor.fetchall())


async def redeem_item(db, user_id: int, item_id: int):
    cursor = await db.execute(
        "SELECT * FROM redeem_items WHERE id = ? AND is_active = 1", (item_id,)
    )
    item = await cursor.fetchone()
    if not item:
        raise ValueError("物品不存在或已下架")

    if item["cost"] > 0:
        balance = await get_balance(db, user_id)
        if balance < item["cost"]:
            raise ValueError(f"爱情币不足，需要{item['cost']}，当前余额{balance}")
        await _add_transaction(
            db, user_id, -item["cost"], "redeem", description=f"兑换: {item['name']}"
        )

    cursor = await db.execute(
        "INSERT INTO redemptions (user_id, item_id, cost) VALUES (?, ?, ?)",
        (user_id, item_id, item["cost"]),
    )
    await db.commit()
    return cursor.lastrowid


async def synthesize(db, user_id: int, redemption_ids: list[int]):
    if len(redemption_ids) < 3:
        raise ValueError("合成至少需要3个同类型物品")

    placeholders = ",".join("?" * len(redemption_ids))
    cursor = await db.execute(
        f"""SELECT r.id as redemption_id, r.item_id, ri.star_level, ri.name as item_name
            FROM redemptions r JOIN redeem_items ri ON r.item_id = ri.id
            WHERE r.id IN ({placeholders}) AND r.user_id = ? AND r.status = 'redeemed'""",
        redemption_ids + [user_id],
    )
    items = list(await cursor.fetchall())

    if len(items) != len(redemption_ids):
        raise ValueError("部分物品不存在、不属于你或已被使用")

    item_ids = set(row["item_id"] for row in items)
    if len(item_ids) != 1:
        raise ValueError("只能合成相同类型的物品")
    source_item_id = item_ids.pop()

    star_level = items[0]["star_level"]
    if star_level < 1 or star_level >= 4:
        raise ValueError("该物品不支持合成")

    cursor = await db.execute(
        "SELECT * FROM redeem_items WHERE synthesize_from = ?", (source_item_id,)
    )
    next_item = await cursor.fetchone()
    if not next_item:
        raise ValueError("无法找到合成目标")

    needed = next_item.get("synthesize_count") or 3
    if len(redemption_ids) < needed:
        raise ValueError(f"合成需要{needed}个同类型物品，当前只有{len(redemption_ids)}个")

    used_ids = redemption_ids[:needed]
    cursor = await db.execute(
        "INSERT INTO redemptions (user_id, item_id, cost, status) VALUES (?, ?, 0, 'redeemed')",
        (user_id, next_item["id"]),
    )
    new_id = cursor.lastrowid

    for rid in used_ids:
        await db.execute(
            "UPDATE redemptions SET status = 'consumed_for_synthesis', synthesized_into = ? WHERE id = ?",
            (new_id, rid),
        )
    await db.commit()
    return new_id


async def get_inventory(db, user_id: int):
    cursor = await db.execute(
        """SELECT r.id as redemption_id, ri.name as item_name, ri.description,
                  ri.star_level, ri.icon, r.status, r.redeemed_at
           FROM redemptions r JOIN redeem_items ri ON r.item_id = ri.id
           WHERE r.user_id = ? AND r.status = 'redeemed'
           ORDER BY ri.star_level DESC, r.redeemed_at DESC""",
        (user_id,),
    )
    return list(await cursor.fetchall())
