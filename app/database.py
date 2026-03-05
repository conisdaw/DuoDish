import os
import aiosqlite
from app.config import DB_PATH


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = _dict_factory
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "migrations", "init.sql"
    )
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA foreign_keys = ON")
        with open(schema_path, "r", encoding="utf-8") as f:
            await db.executescript(f.read())
        await db.commit()
        try:
            await db.execute("ALTER TABLE private_kitchen_dishes ADD COLUMN recipe_url TEXT")
            await db.commit()
        except Exception:
            pass
