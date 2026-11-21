from __future__ import annotations

import sqlite3
from config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    # Pre-multi-city databases have no `city` column; they are only a cache
    # of OpenStreetMap data, so drop and rebuild them.
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(places)")]
    if cols and "city" not in cols:
        conn.execute("DROP TABLE places")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cities (
            name         TEXT PRIMARY KEY,   -- normalised key, e.g. 'kraków'
            display_name TEXT NOT NULL,
            lat          REAL NOT NULL,
            lon          REAL NOT NULL,
            fetched_at   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS places (
            id          TEXT NOT NULL,
            city        TEXT NOT NULL,
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
            tags        TEXT,
            PRIMARY KEY (city, id)
        );
    """)
    conn.commit()
    conn.close()


def city_key(name: str) -> str:
    return name.strip().lower()


# ── Cities ──────────────────────────────────────────────────────────────────

def save_city(key: str, display_name: str, lat: float, lon: float, fetched_at: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO cities (name, display_name, lat, lon, fetched_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            display_name=excluded.display_name, lat=excluded.lat,
            lon=excluded.lon, fetched_at=excluded.fetched_at
    """, (key, display_name, lat, lon, fetched_at))
    conn.commit()
    conn.close()


def get_city(key: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM cities WHERE name=?", (key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_cities() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.*, COUNT(p.id) AS n_places
        FROM cities c LEFT JOIN places p ON p.city = c.name
        GROUP BY c.name ORDER BY c.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def replace_city_places(key: str, places: list[dict]):
    """Atomically swap a city's places for a freshly fetched set."""
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM places WHERE city=?", (key,))
        conn.executemany("""
            INSERT OR REPLACE INTO places
                (id, city, name, category, subcategory, lat, lon, address,
                 opening_hours, avg_cost_pln, duration_min, description, tags)
            VALUES
                (:id, :city, :name, :category, :subcategory, :lat, :lon, :address,
                 :opening_hours, :avg_cost_pln, :duration_min, :description, :tags)
        """, [{**p, "city": key} for p in places])
    conn.close()


def delete_city(key: str):
    conn = get_conn()
    with conn:
        conn.execute("DELETE FROM places WHERE city=?", (key,))
        conn.execute("DELETE FROM cities WHERE name=?", (key,))
    conn.close()


# ── Places ──────────────────────────────────────────────────────────────────

def get_all_places(city: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM places WHERE city=? ORDER BY category, name", (city_key(city),)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_place_by_id(city: str, place_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM places WHERE city=? AND id=?", (city_key(city), place_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def count_places(city: str | None = None) -> int:
    conn = get_conn()
    if city is None:
        n = conn.execute("SELECT COUNT(*) FROM places").fetchone()[0]
    else:
        n = conn.execute("SELECT COUNT(*) FROM places WHERE city=?", (city_key(city),)).fetchone()[0]
    conn.close()
    return n
