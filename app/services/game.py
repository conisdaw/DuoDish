import random


async def init_game(db, order_id: int, hidden_dish_id=None):
    cursor = await db.execute(
        "SELECT * FROM price_guess_games WHERE order_id = ?", (order_id,)
    )
    if await cursor.fetchone():
        raise ValueError("该订单已有盲猜游戏")

    if not hidden_dish_id:
        cursor = await db.execute(
            "SELECT id FROM order_dishes WHERE order_id = ? AND price IS NOT NULL",
            (order_id,),
        )
        dishes = list(await cursor.fetchall())
        if not dishes:
            raise ValueError("该订单没有带价格的菜品")
        hidden_dish_id = random.choice(dishes)["id"]

    await db.execute(
        "INSERT INTO price_guess_games (order_id, hidden_dish_id) VALUES (?, ?)",
        (order_id, hidden_dish_id),
    )
    await db.commit()


async def reset_game(db, order_id: int):
    cursor = await db.execute(
        "SELECT * FROM price_guess_games WHERE order_id = ?", (order_id,)
    )
    if not await cursor.fetchone():
        raise ValueError("该订单没有盲猜游戏")
    await db.execute("DELETE FROM price_guess_games WHERE order_id = ?", (order_id,))
    await db.commit()


async def get_game_status(db, order_id: int):
    cursor = await db.execute(
        """SELECT g.*, d.dish_name, d.order_id as d_order_id
           FROM price_guess_games g
           JOIN order_dishes d ON g.hidden_dish_id = d.id
           WHERE g.order_id = ?""",
        (order_id,),
    )
    game = await cursor.fetchone()
    if not game:
        return None
    return {
        "order_id": order_id,
        "hidden_dish": {
            "id": game["hidden_dish_id"],
            "order_id": game["d_order_id"],
            "dish_name": game["dish_name"],
            "price": None,
        },
        "user1_guessed": game["guess_user1"] is not None,
        "user2_guessed": game["guess_user2"] is not None,
        "completed": game["completed_at"] is not None,
    }


async def submit_guess(db, order_id: int, user_id: int, guess: float):
    if user_id not in (1, 2):
        raise ValueError("无效的用户ID，仅支持用户1和用户2")

    cursor = await db.execute(
        "SELECT * FROM price_guess_games WHERE order_id = ?", (order_id,)
    )
    game = await cursor.fetchone()
    if not game:
        raise ValueError("该订单没有盲猜游戏")
    if game["completed_at"]:
        raise ValueError("游戏已结束")

    field = f"guess_user{user_id}"
    if game[field] is not None:
        raise ValueError("你已经猜过了")

    await db.execute(
        f"UPDATE price_guess_games SET {field} = ? WHERE order_id = ?",
        (guess, order_id),
    )
    await db.commit()


async def get_result(db, order_id: int):
    cursor = await db.execute(
        """SELECT g.*, d.price as actual_price
           FROM price_guess_games g
           JOIN order_dishes d ON g.hidden_dish_id = d.id
           WHERE g.order_id = ?""",
        (order_id,),
    )
    game = await cursor.fetchone()
    if not game:
        raise ValueError("该订单没有盲猜游戏")
    if game["guess_user1"] is None or game["guess_user2"] is None:
        raise ValueError("两人还未全部猜完")

    actual = game["actual_price"]
    g1, g2 = game["guess_user1"], game["guess_user2"]
    diff1, diff2 = abs(g1 - actual), abs(g2 - actual)

    if diff1 < diff2:
        result, reward = "user1_win", "用户1猜得更准！获得菜品决定权"
    elif diff2 < diff1:
        result, reward = "user2_win", "用户2猜得更准！获得菜品决定权"
    else:
        result, reward = "both_wrong", "看来你们离柴米油盐还差一点默契哦~随机赠送一道小菜"

    await db.execute(
        "UPDATE price_guess_games SET result = ?, reward = ?, completed_at = CURRENT_TIMESTAMP "
        "WHERE order_id = ?",
        (result, reward, order_id),
    )
    await db.commit()

    return {
        "actual_price": actual,
        "guess_user1": g1,
        "guess_user2": g2,
        "result": result,
        "reward": reward,
    }
