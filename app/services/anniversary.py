from datetime import date, timedelta


def _safe_replace_year(d: date, year: int) -> date:
    try:
        return d.replace(year=year)
    except ValueError:
        return d.replace(year=year, day=28)


def _next_occurrence(ann_date: date, is_recurring: int) -> date:
    today = date.today()
    if is_recurring == 0:
        return ann_date
    if is_recurring == 1:  # 每年
        this_year = _safe_replace_year(ann_date, today.year)
        return this_year if this_year >= today else _safe_replace_year(ann_date, today.year + 1)
    if is_recurring == 3:  # 每月
        this_month = date(today.year, today.month, min(ann_date.day, 28))
        if this_month >= today:
            return this_month
        month = today.month + 1
        year = today.year
        if month > 12:
            month, year = 1, year + 1
        return date(year, month, min(ann_date.day, 28))
    if is_recurring == 2:  # 每周
        days_ahead = (ann_date.weekday() - today.weekday()) % 7
        return today if days_ahead == 0 else today + timedelta(days=days_ahead)
    return ann_date


def _enrich(row: dict) -> dict:
    ann = dict(row)
    try:
        ann_date = date.fromisoformat(ann["date"])
        next_occ = _next_occurrence(ann_date, ann.get("is_recurring", 0))
        ann["days_until"] = (next_occ - date.today()).days
    except (ValueError, TypeError):
        ann["days_until"] = None
    return ann


async def list_anniversaries(db, upcoming_only=False, days=7):
    cursor = await db.execute("SELECT * FROM anniversaries ORDER BY date")
    rows = await cursor.fetchall()
    result = [_enrich(r) for r in rows]
    if upcoming_only:
        result = [a for a in result if a.get("days_until") is not None and 0 <= a["days_until"] <= days]
    return result


async def get_anniversary(db, ann_id: int):
    cursor = await db.execute("SELECT * FROM anniversaries WHERE id = ?", (ann_id,))
    row = await cursor.fetchone()
    return _enrich(row) if row else None


async def create_anniversary(db, name, date_str, description=None, is_recurring=0, remind_days=3):
    cursor = await db.execute(
        "INSERT INTO anniversaries (name, date, description, is_recurring, remind_days) VALUES (?, ?, ?, ?, ?)",
        (name, date_str, description, is_recurring, remind_days),
    )
    await db.commit()
    return cursor.lastrowid


async def update_anniversary(db, ann_id: int, **kwargs):
    fields, values = [], []
    for key, value in kwargs.items():
        if value is not None:
            fields.append(f"{key} = ?")
            values.append(value)
    if not fields:
        return
    values.append(ann_id)
    await db.execute(f"UPDATE anniversaries SET {', '.join(fields)} WHERE id = ?", values)
    await db.commit()


async def delete_anniversary(db, ann_id: int):
    await db.execute("DELETE FROM anniversaries WHERE id = ?", (ann_id,))
    await db.commit()
