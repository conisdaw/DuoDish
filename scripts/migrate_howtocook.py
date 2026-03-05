"""将 HowToCook 菜谱迁移到 DuoDish 私家厨房

扫描 temp/HowToCook/dishes 下所有 .md 菜谱，导入 private_kitchen_dishes。
菜谱以 md 链接形式引用，食材从「必备原料和工具」解析。
"""

import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, _dict_factory
from app.config import DB_PATH
import aiosqlite

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOWTOCOOK_DISHES = os.path.join(PROJECT_ROOT, "temp", "HowToCook", "dishes")
CREATED_BY = 1  # alice


def path_to_url(fp: str) -> str:
    """将本地路径转为 /temp/HowToCook/dishes/... 形式的 URL"""
    rel = os.path.relpath(fp, PROJECT_ROOT)
    return "/" + rel.replace("\\", "/")


def parse_dish(md_path: str) -> tuple[str, list[tuple[str, str, str]]] | None:
    """解析 .md 菜谱，返回 (dish_name, [(ingredient_name, amount, unit), ...])"""
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 菜名：从 # 标题提取，如 "# 西红柿炒鸡蛋的做法" -> 西红柿炒鸡蛋
    m = re.search(r"^#\s*(.+?)(?:的做法)?\s*$", content, re.MULTILINE)
    name = m.group(1).strip() if m else os.path.splitext(os.path.basename(md_path))[0]

    # 必备原料和工具
    ingredients = []
    sec = re.search(r"##\s*必备原料和工具\s*\n(.*?)(?=##|$)", content, re.DOTALL)
    if sec:
        block = sec.group(1)
        for line in block.splitlines():
            line = line.strip()
            if not line or not (line.startswith("- ") or line.startswith("* ")):
                continue
            raw = line[2:].strip()
            # 去除括号内容：内脂豆腐（推荐清美） -> 内脂豆腐
            raw = re.sub(r"[（(].*?[）)]", "", raw).strip()
            # 跳过纯工具（可选：水果刀、炒锅等，这里简单保留所有）
            if not raw or raw in ("可选", "推荐"):
                continue
            # 默认用量
            ingredients.append((raw, "适量", ""))

    return (name, ingredients)


def collect_dish_files() -> list[str]:
    """收集 dishes 下所有菜谱 .md，排除 template"""
    out = []
    for root, _dirs, files in os.walk(HOWTOCOOK_DISHES):
        if "template" in root:
            continue
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(root, f))
    return sorted(out)


async def migrate():
    if not os.path.exists(HOWTOCOOK_DISHES):
        print("请先运行: python scripts/setup_howtocook.py")
        return 1

    await init_db()
    files = collect_dish_files()
    print(f"发现 {len(files)} 个菜谱文件")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = _dict_factory
        await db.execute("PRAGMA foreign_keys = OFF")

        # 清空私家厨房相关表
        for t in ["kitchen_selections", "dish_ingredients", "private_kitchen_dishes"]:
            await db.execute(f"DELETE FROM {t}")
        await db.execute("DELETE FROM sqlite_sequence WHERE name IN ('private_kitchen_dishes','dish_ingredients','kitchen_selections')")
        await db.commit()
        await db.execute("PRAGMA foreign_keys = ON")

        inserted = 0
        skipped = 0
        for md_path in files:
            parsed = parse_dish(md_path)
            if not parsed:
                skipped += 1
                continue
            name, ings = parsed
            recipe_url = path_to_url(md_path)
            recipe = f"完整菜谱：[{name}]({recipe_url})"

            cursor = await db.execute(
                "INSERT INTO private_kitchen_dishes (name, recipe, recipe_url, images, created_by) VALUES (?, ?, ?, ?, ?)",
                (name, recipe, recipe_url, json.dumps([], ensure_ascii=False), CREATED_BY),
            )
            dish_id = cursor.lastrowid
            for i, (n, amt, unit) in enumerate(ings):
                await db.execute(
                    "INSERT INTO dish_ingredients (dish_id, name, amount, unit, sort_order) VALUES (?, ?, ?, ?, ?)",
                    (dish_id, n, amt, unit, i),
                )
            inserted += 1

        # 添加 2 个测试点菜（dish 1 由 user1 选，dish 2 由 user2 选）
        if inserted >= 2:
            await db.execute(
                "INSERT OR IGNORE INTO kitchen_selections (dish_id, selected_by) VALUES (1, 1), (2, 2)"
            )
        await db.commit()
        print(f"[OK] 已迁移 {inserted} 道菜谱到私家厨房")
        if skipped:
            print(f"  跳过 {skipped} 个")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(migrate()))
