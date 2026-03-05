"""填充测试数据到 duodish.db"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, _dict_factory
from app.auth import hash_password
from app.config import DB_PATH

import aiosqlite

PASSWORD_HASH = hash_password("123456")


async def seed():
    await init_db()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _dict_factory
        await db.execute("PRAGMA foreign_keys = OFF")

        tables_to_clear = [
            # private_kitchen 由 scripts/migrate_howtocook.py 迁移，不在此处清理
            "user_achievements", "love_coin_transactions", "redemptions",
            "price_guess_games", "taste_diary", "dish_tags",
            "order_dishes", "orders", "anniversaries",
            "user_preferences", "love_coins", "users",
        ]
        for t in tables_to_clear:
            await db.execute(f"DELETE FROM {t}")
        await db.execute("DELETE FROM sqlite_sequence")
        await db.commit()

        await db.execute("PRAGMA foreign_keys = ON")

        # ═══════════ 1. 用户 ═══════════
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, password_hash, nickname, avatar) VALUES (?, ?, ?, ?, ?)",
            (1, "alice", PASSWORD_HASH, "小爱", "/uploads/alice.jpg"),
        )
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, password_hash, nickname, avatar) VALUES (?, ?, ?, ?, ?)",
            (2, "bob", PASSWORD_HASH, "阿宝", "/uploads/bob.jpg"),
        )

        # ═══════════ 2. 爱情币初始余额 ═══════════
        await db.execute("INSERT OR IGNORE INTO love_coins (user_id, balance) VALUES (1, 2000)")
        await db.execute("INSERT OR IGNORE INTO love_coins (user_id, balance) VALUES (2, 1500)")

        # ═══════════ 3. 用户偏好 ═══════════
        await db.execute(
            "INSERT OR IGNORE INTO user_preferences (user_id, dislikes, likes) VALUES (?, ?, ?)",
            (1, json.dumps(["香菜", "葱", "芥末"], ensure_ascii=False),
             json.dumps(["辣", "麻", "川菜", "火锅"], ensure_ascii=False)),
        )
        await db.execute(
            "INSERT OR IGNORE INTO user_preferences (user_id, dislikes, likes) VALUES (?, ?, ?)",
            (2, json.dumps(["辣", "花椒", "内脏"], ensure_ascii=False),
             json.dumps(["甜品", "日料", "清淡", "海鲜"], ensure_ascii=False)),
        )

        # ═══════════ 4. 纪念日 ═══════════
        anniversaries = [
            ("在一起纪念日", "2025-03-04", "我们在一起的第一天 ❤️", 1, 7),
            ("小爱生日", "2025-08-15", "记得准备礼物！", 1, 7),
            ("阿宝生日", "2025-12-20", "他最想要新款耳机", 1, 5),
            ("每周约会日", "2026-03-08", "每周六的固定约会", 2, 1),
            ("100天纪念", "2025-06-12", "在一起100天", 0, 3),
            ("第一次旅行纪念", "2025-10-01", "一起去了杭州", 1, 5),
        ]
        for name, date, desc, recurring, remind in anniversaries:
            await db.execute(
                "INSERT INTO anniversaries (name, date, description, is_recurring, remind_days) VALUES (?, ?, ?, ?, ?)",
                (name, date, desc, recurring, remind),
            )

        # ═══════════ 5. 点餐记录 + 菜品 ═══════════
        orders_data = [
            {
                "restaurant": "海底捞", "address": "北京市朝阳区望京SOHO",
                "date": "2026-02-14T18:30:00", "mood1": "甜", "mood2": "甜",
                "notes": "情人节快乐！今天的番茄锅底超好喝",
                "dishes": [
                    ("麻辣牛肉", 68.0, 1, None), ("虾滑", 38.0, 2, None),
                    ("番茄锅底", 0.0, None, None), ("酸梅汤", 12.0, None, "少糖"),
                    ("冰粉", 8.0, 2, None),
                ],
            },
            {
                "restaurant": "一幸寿司", "address": "北京市海淀区中关村大街",
                "date": "2026-02-20T12:00:00", "mood1": "暖", "mood2": "暖",
                "notes": "阿宝推荐的这家日料太赞了",
                "dishes": [
                    ("三文鱼刺身", 88.0, 2, None), ("鳗鱼饭", 58.0, 1, None),
                    ("味增汤", 15.0, None, None), ("抹茶蛋糕", 28.0, 2, None),
                ],
            },
            {
                "restaurant": "海底捞", "address": "北京市朝阳区望京SOHO",
                "date": "2026-02-28T19:00:00", "mood1": "躁", "mood2": "冷",
                "notes": "今天都有点累，火锅治愈一切",
                "dishes": [
                    ("毛肚", 42.0, 1, None), ("肥牛卷", 52.0, 2, None),
                    ("土豆片", 16.0, None, None), ("椰子鸡汤", 32.0, None, None),
                ],
            },
            {
                "restaurant": "外婆家", "address": "北京市西城区西单大悦城",
                "date": "2026-03-01T11:30:00", "mood1": "暖", "mood2": "甜",
                "notes": "周末brunch，外婆家的茶香鸡真香",
                "dishes": [
                    ("茶香鸡", 48.0, 1, None), ("西湖醋鱼", 58.0, 2, None),
                    ("龙井虾仁", 68.0, None, None), ("东坡肉", 38.0, 1, None),
                ],
            },
            {
                "restaurant": "鼎泰丰", "address": "北京市朝阳区国贸商城",
                "date": "2026-03-03T12:00:00", "mood1": "甜", "mood2": "暖",
                "notes": "小笼包永远的神",
                "dishes": [
                    ("蟹粉小笼包", 88.0, None, None), ("红烧狮子头", 48.0, 1, None),
                    ("虾仁蛋炒饭", 38.0, 2, None), ("酸辣汤", 22.0, None, None),
                ],
            },
            {
                "restaurant": "一幸寿司", "address": "北京市海淀区中关村大街",
                "date": "2026-03-04T18:00:00", "mood1": "暖", "mood2": "甜",
                "notes": "在一起一周年纪念日！",
                "dishes": [
                    ("特选寿司拼盘", 168.0, None, None), ("和牛刺身", 128.0, 1, None),
                    ("天妇罗", 58.0, 2, None), ("清酒", 48.0, None, None),
                ],
            },
            {
                "restaurant": "麦当劳", "address": "北京市海淀区五道口",
                "date": "2026-03-05T20:00:00", "mood1": "躁", "mood2": "躁",
                "notes": "加班太晚了随便吃点",
                "dishes": [
                    ("巨无霸套餐", 42.0, 1, None), ("麦辣鸡腿堡套餐", 39.0, 2, None),
                    ("麦旋风", 13.0, 2, None),
                ],
            },
        ]

        for o in orders_data:
            cursor = await db.execute(
                "INSERT INTO orders (restaurant, address, order_date, mood_user1, mood_user2, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (o["restaurant"], o["address"], o["date"], o["mood1"], o["mood2"], o["notes"]),
            )
            order_id = cursor.lastrowid
            for dish_name, price, ordered_by, notes in o["dishes"]:
                await db.execute(
                    "INSERT INTO order_dishes (order_id, dish_name, price, ordered_by, notes) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (order_id, dish_name, price, ordered_by, notes),
                )

        # ═══════════ 6. 味觉日记 ═══════════
        diaries = [
            (1, "情人节的海底捞，虾滑超新鲜！番茄锅底喝到见底。两人对着冒着热气的火锅许愿，希望每天都这么甜。", 5),
            (2, "阿宝带我来的日料店，三文鱼入口即化。抹茶蛋糕是惊喜，拍了好多照片。", 5),
            (3, "加班后的治愈火锅，虽然累但吃到好吃的立刻满血复活。椰子鸡汤太暖了。", 4),
            (4, "茶香鸡真的名不虚传！龙井虾仁也很鲜，下次还来。", 4),
            (6, "一周年纪念日！特选寿司拼盘超级豪华，和牛刺身入口即化。清酒微醺的感觉刚刚好。最棒的一次约会 ❤️", 5),
        ]
        for oid, content, rating in diaries:
            await db.execute(
                "INSERT INTO taste_diary (order_id, content, images, rating) VALUES (?, ?, ?, ?)",
                (oid, content, json.dumps([], ensure_ascii=False), rating),
            )

        # ═══════════ 7. 盲猜价格游戏（订单5: 鼎泰丰，未完成） ═══════════
        # 隐藏蟹粉小笼包(88元)的价格
        cursor = await db.execute(
            "SELECT id FROM order_dishes WHERE order_id = 5 AND dish_name = '蟹粉小笼包'"
        )
        dish = await cursor.fetchone()
        if dish:
            await db.execute(
                "INSERT INTO price_guess_games (order_id, hidden_dish_id) VALUES (?, ?)",
                (5, dish["id"]),
            )

        # ═══════════ 8. 爱情币流水 ═══════════
        transactions = [
            (1, 10, "order_deposit", 1, "点餐存入: 海底捞"),
            (1, 10, "order_deposit", 2, "点餐存入: 一幸寿司"),
            (1, 10, "order_deposit", 3, "点餐存入: 海底捞"),
            (1, 10, "order_deposit", 4, "点餐存入: 外婆家"),
            (1, 10, "order_deposit", 5, "点餐存入: 鼎泰丰"),
            (1, 10, "order_deposit", 6, "点餐存入: 一幸寿司"),
            (1, 10, "order_deposit", 7, "点餐存入: 麦当劳"),
            (2, 10, "order_deposit", 1, "点餐存入: 海底捞"),
            (2, 10, "order_deposit", 2, "点餐存入: 一幸寿司"),
            (2, 10, "order_deposit", 4, "点餐存入: 外婆家"),
            (1, -500, "redeem", None, "兑换: 一星不生气券"),
            (1, -500, "redeem", None, "兑换: 一星不生气券"),
            (1, -500, "redeem", None, "兑换: 一星不生气券"),
            (1, -200, "redeem", None, "兑换: 免洗碗特权"),
        ]
        for uid, amount, tx_type, ref_id, desc in transactions:
            await db.execute(
                "INSERT INTO love_coin_transactions (user_id, amount, type, reference_id, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (uid, amount, tx_type, ref_id, desc),
            )

        # ═══════════ 9. 兑换记录（3张一星不生气券 + 1个免洗碗） ═══════════
        await db.execute("INSERT INTO redemptions (user_id, item_id, cost, status) VALUES (1, 3, 500, 'redeemed')")
        await db.execute("INSERT INTO redemptions (user_id, item_id, cost, status) VALUES (1, 3, 500, 'redeemed')")
        await db.execute("INSERT INTO redemptions (user_id, item_id, cost, status) VALUES (1, 3, 500, 'redeemed')")
        await db.execute("INSERT INTO redemptions (user_id, item_id, cost, status) VALUES (1, 1, 200, 'redeemed')")

        # ═══════════ 10. 菜品标签 ═══════════
        tags = [
            ("麻辣牛肉", "辣"), ("麻辣牛肉", "麻"), ("麻辣牛肉", "牛肉"),
            ("虾滑", "海鲜"), ("番茄锅底", "清淡"), ("酸梅汤", "冷饮"),
            ("冰粉", "甜品"), ("三文鱼刺身", "日料"), ("三文鱼刺身", "海鲜"),
            ("鳗鱼饭", "日料"), ("抹茶蛋糕", "甜品"), ("味增汤", "日料"),
            ("毛肚", "内脏"), ("肥牛卷", "牛肉"), ("椰子鸡汤", "汤"),
            ("茶香鸡", "家常"), ("西湖醋鱼", "海鲜"), ("龙井虾仁", "海鲜"),
            ("东坡肉", "家常"), ("蟹粉小笼包", "海鲜"), ("红烧狮子头", "家常"),
            ("虾仁蛋炒饭", "家常"), ("酸辣汤", "汤"), ("酸辣汤", "辣"),
            ("特选寿司拼盘", "日料"), ("特选寿司拼盘", "海鲜"),
            ("和牛刺身", "日料"), ("和牛刺身", "牛肉"),
            ("天妇罗", "日料"), ("巨无霸套餐", "快餐"), ("麦辣鸡腿堡套餐", "快餐"),
            ("麦辣鸡腿堡套餐", "辣"), ("麦旋风", "甜品"), ("麦旋风", "冷饮"),
        ]
        for dish_name, tag in tags:
            await db.execute(
                "INSERT OR IGNORE INTO dish_tags (dish_name, tag) VALUES (?, ?)",
                (dish_name, tag),
            )

        # ═══════════ 11. 私家厨房 ═══════════
        # 由 scripts/migrate_howtocook.py 迁移 HowToCook 全部菜谱，此处不再填充

        # ═══════════ 12. 成就进度 ═══════════
        # user1: 7次点餐 → 初次约饭已解锁, 十次约会进度7
        await db.execute(
            "INSERT OR REPLACE INTO user_achievements (user_id, achievement_id, progress, unlocked_at) VALUES (1, 1, 7, '2026-02-14 18:30:00')"
        )
        await db.execute(
            "INSERT OR REPLACE INTO user_achievements (user_id, achievement_id, progress, unlocked_at) VALUES (1, 2, 7, NULL)"
        )
        # user1: 海底捞去了2次 → 回头客进度2
        await db.execute(
            "INSERT OR REPLACE INTO user_achievements (user_id, achievement_id, progress, unlocked_at) VALUES (1, 5, 2, NULL)"
        )
        # user1: 5篇日记 → 美食评论家进度5
        await db.execute(
            "INSERT OR REPLACE INTO user_achievements (user_id, achievement_id, progress, unlocked_at) VALUES (1, 6, 5, NULL)"
        )
        # user1: 爱情币存入70 → 甜蜜储蓄家进度70
        await db.execute(
            "INSERT OR REPLACE INTO user_achievements (user_id, achievement_id, progress, unlocked_at) VALUES (1, 8, 70, NULL)"
        )

        await db.commit()
        print("[OK] ce shi shu ju tian chong wan cheng!")
        print()
        print(f"  users:   alice / 123456, bob / 123456")
        print(f"  coins:   alice=2000, bob=1500")
        print(f"  anniversaries: {len(anniversaries)}")
        print(f"  orders:  {len(orders_data)}")
        print(f"  diaries: {len(diaries)}")
        print(f"  tags:    {len(tags)}")
        print(f"  game:    order#5 (hidden dish: xie fen xiao long bao, 88)")
        print(f"  inventory: alice has 3x star-1 + 1x mian-xi-wan")
        cursor = await db.execute("SELECT COUNT(*) as c FROM private_kitchen_dishes")
        row = await cursor.fetchone()
        print(f"  private_kitchen: {row['c']} dishes (run migrate_howtocook for full HowToCook)")


if __name__ == "__main__":
    asyncio.run(seed())
