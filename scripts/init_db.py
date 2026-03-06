"""使用 init.sql 创建空的 SQLite 数据库"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INIT_SQL = os.path.join(PROJECT_ROOT, "migrations", "init.sql")
DB_PATH = os.getenv("DB_PATH", os.path.join(PROJECT_ROOT, "duodish.db"))


def main():
    if not os.path.exists(INIT_SQL):
        print(f"[ERR] 未找到 {INIT_SQL}")
        return 1

    with open(INIT_SQL, encoding="utf-8") as f:
        sql = f.read()

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(sql)
    conn.commit()
    conn.close()

    print(f"[OK] 数据库已创建: {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
