import sqlite3
import json
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS places (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            subcategory TEXT,
            lat         REAL NOT NULL,
            lon         REAL NOT NULL,
            address     TEXT,
            opening_hours TEXT,
            avg_cost_pln  REAL,
            duration_min  INTEGER,
            description TEXT,
            tags        TEXT
        );
    """)
    conn.commit()
    conn.close()


def upsert_place(place: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO places
            (id, name, category, subcategory, lat, lon, address,
             opening_hours, avg_cost_pln, duration_min, description, tags)
        VALUES
            (:id, :name, :category, :subcategory, :lat, :lon, :address,
             :opening_hours, :avg_cost_pln, :duration_min, :description, :tags)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            opening_hours=excluded.opening_hours,
            avg_cost_pln=excluded.avg_cost_pln,
            tags=excluded.tags
    """, place)
    conn.commit()
    conn.close()


def get_all_places() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM places ORDER BY category, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_places_by_category(categories: list[str]) -> list[dict]:
    placeholders = ",".join("?" * len(categories))
    conn = get_conn()
    rows = conn.execute(
        f"SELECT * FROM places WHERE category IN ({placeholders}) ORDER BY name",
        categories,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_place_by_id(place_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM places WHERE id=?", (place_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def place_exists(place_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM places WHERE id=?", (place_id,)).fetchone()
    conn.close()
    return row is not None


def count_places() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    conn.close()
    return n
