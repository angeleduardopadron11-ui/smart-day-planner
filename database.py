"""SQLite database setup and CRUD operations using aiosqlite."""

import aiosqlite
import json
import os
from pathlib import Path
from typing import Optional

# In serverless environments (like Vercel), the project root is read-only.
# We store the SQLite database in /tmp or in a path specified by DB_PATH.
if os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/planner.db")
else:
    DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent / "planner.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    data TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS schedule_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'personal',
    description TEXT DEFAULT '',
    is_fixed INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_schedule_date ON schedule_blocks(schedule_date);

INSERT OR IGNORE INTO preferences (id, data) VALUES (1, '{}');
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Initialize the database schema."""
    db = await get_db()
    try:
        await db.executescript(SCHEMA)
        await db.commit()
    finally:
        await db.close()


# ── Preferences ──────────────────────────────────────────────

async def get_preferences() -> dict:
    """Retrieve user preferences."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT data FROM preferences WHERE id = 1")
        row = await cursor.fetchone()
        if row:
            return json.loads(row[0])
        return {}
    finally:
        await db.close()


async def save_preferences(prefs: dict) -> dict:
    """Save user preferences."""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE preferences 
               SET data = ?, updated_at = datetime('now','localtime') 
               WHERE id = 1""",
            (json.dumps(prefs),)
        )
        await db.commit()
        return prefs
    finally:
        await db.close()


# ── Schedule Blocks ──────────────────────────────────────────

async def get_schedule(schedule_date: str) -> list[dict]:
    """Get all blocks for a specific date, ordered by start_time."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, schedule_date, start_time, end_time, title, 
                      category, description, is_fixed, sort_order
               FROM schedule_blocks 
               WHERE schedule_date = ? 
               ORDER BY start_time, sort_order""",
            (schedule_date,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def save_schedule(schedule_date: str, blocks: list[dict]) -> list[dict]:
    """Replace all blocks for a date with new ones (atomic operation)."""
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM schedule_blocks WHERE schedule_date = ?",
            (schedule_date,)
        )
        for i, block in enumerate(blocks):
            await db.execute(
                """INSERT INTO schedule_blocks 
                   (schedule_date, start_time, end_time, title, category, 
                    description, is_fixed, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    schedule_date,
                    block["start_time"],
                    block["end_time"],
                    block["title"],
                    block["category"],
                    block.get("description", ""),
                    block.get("is_fixed", 0),
                    i,
                )
            )
        await db.commit()
        return await get_schedule(schedule_date)
    finally:
        await db.close()


async def update_block(block_id: int, updates: dict) -> Optional[dict]:
    """Update a specific block by ID."""
    db = await get_db()
    try:
        # Build dynamic SET clause from non-None values
        fields = {k: v for k, v in updates.items() if v is not None}
        if not fields:
            return None

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [block_id]

        await db.execute(
            f"""UPDATE schedule_blocks 
                SET {set_clause}, updated_at = datetime('now','localtime')
                WHERE id = ?""",
            values,
        )
        await db.commit()

        cursor = await db.execute(
            """SELECT id, schedule_date, start_time, end_time, title, 
                      category, description, is_fixed, sort_order
               FROM schedule_blocks WHERE id = ?""",
            (block_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def delete_block(block_id: int) -> bool:
    """Delete a block by ID."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM schedule_blocks WHERE id = ?", (block_id,)
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def add_block(block: dict) -> dict:
    """Add a single block."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO schedule_blocks 
               (schedule_date, start_time, end_time, title, category, 
                description, is_fixed, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                block["schedule_date"],
                block["start_time"],
                block["end_time"],
                block["title"],
                block["category"],
                block.get("description", ""),
                block.get("is_fixed", 0),
                block.get("sort_order", 0),
            ),
        )
        await db.commit()
        new_id = cursor.lastrowid

        cursor = await db.execute(
            """SELECT id, schedule_date, start_time, end_time, title, 
                      category, description, is_fixed, sort_order
               FROM schedule_blocks WHERE id = ?""",
            (new_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else block
    finally:
        await db.close()


async def get_dates_with_schedules() -> list[str]:
    """Get all dates that have saved schedules."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT DISTINCT schedule_date 
               FROM schedule_blocks 
               ORDER BY schedule_date DESC 
               LIMIT 30"""
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]
    finally:
        await db.close()
