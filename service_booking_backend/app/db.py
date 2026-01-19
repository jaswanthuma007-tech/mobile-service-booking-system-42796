import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# This app uses a plain sqlite3 connection (no ORM) to keep dependencies minimal.
# The database path is configured via SQLITE_DB environment variable.
#
# NOTE: The database container provides SQLITE_DB in its .env; ask orchestrator/user to ensure it is set.


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db_path() -> str:
    """Get SQLite database path from env; default to local dev file."""
    return os.getenv("SQLITE_DB", "service_booking.sqlite3")


def get_connection() -> sqlite3.Connection:
    """Create a sqlite3 connection with row factory enabled."""
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enforce foreign keys in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Create required tables if they do not exist."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brands (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS models (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              brand_id INTEGER NOT NULL,
              name TEXT NOT NULL,
              UNIQUE(brand_id, name),
              FOREIGN KEY(brand_id) REFERENCES brands(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS problems (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              customer_name TEXT NOT NULL,
              phone TEXT NOT NULL,
              email TEXT NOT NULL,
              brand_id INTEGER NOT NULL,
              model_id INTEGER NOT NULL,
              problem_id INTEGER NOT NULL,
              notes TEXT,
              status TEXT NOT NULL DEFAULT 'new',
              created_at TEXT NOT NULL,
              FOREIGN KEY(brand_id) REFERENCES brands(id),
              FOREIGN KEY(model_id) REFERENCES models(id),
              FOREIGN KEY(problem_id) REFERENCES problems(id)
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _table_is_empty(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(f"SELECT COUNT(1) AS cnt FROM {table};")
    row = cur.fetchone()
    return int(row["cnt"]) == 0


def seed_reference_data_if_empty() -> None:
    """Seed brands/models/problems with initial values if empty."""
    conn = get_connection()
    try:
        if _table_is_empty(conn, "brands"):
            for name in ["Apple", "Samsung", "Google", "OnePlus", "Xiaomi"]:
                conn.execute("INSERT INTO brands(name) VALUES (?);", (name,))
        if _table_is_empty(conn, "models"):
            # Map brand name -> list of models
            brand_models = {
                "Apple": ["iPhone 12", "iPhone 13", "iPhone 14", "iPhone 15"],
                "Samsung": ["Galaxy S21", "Galaxy S22", "Galaxy S23", "Galaxy A54"],
                "Google": ["Pixel 6", "Pixel 7", "Pixel 8"],
                "OnePlus": ["OnePlus 10", "OnePlus 11", "OnePlus 12"],
                "Xiaomi": ["Redmi Note 12", "Redmi Note 13", "Mi 11"],
            }
            brand_rows = conn.execute("SELECT id, name FROM brands;").fetchall()
            brand_id_by_name = {r["name"]: r["id"] for r in brand_rows}
            for brand_name, models in brand_models.items():
                brand_id = brand_id_by_name.get(brand_name)
                if not brand_id:
                    continue
                for model_name in models:
                    conn.execute(
                        "INSERT OR IGNORE INTO models(brand_id, name) VALUES (?, ?);",
                        (brand_id, model_name),
                    )
        if _table_is_empty(conn, "problems"):
            for name in [
                "Screen replacement",
                "Battery replacement",
                "Charging port issue",
                "Camera issue",
                "Water damage",
                "Software troubleshooting",
            ]:
                conn.execute("INSERT INTO problems(name) VALUES (?);", (name,))
        conn.commit()
    finally:
        conn.close()


def rows_to_dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Convert sqlite3.Row list to plain dict list."""
    return [dict(r) for r in rows]


def create_booking(data: Dict[str, Any]) -> int:
    """Insert booking and return booking id."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO bookings(
              customer_name, phone, email, brand_id, model_id, problem_id, notes, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                data["customer_name"],
                data["phone"],
                data["email"],
                int(data["brand_id"]),
                int(data["model_id"]),
                int(data["problem_id"]),
                data.get("notes"),
                data.get("status", "new"),
                _utc_now_iso(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def get_booking(booking_id: int) -> Optional[Dict[str, Any]]:
    """Fetch booking with joined brand/model/problem names."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
              b.id,
              b.customer_name,
              b.phone,
              b.email,
              b.brand_id,
              br.name AS brand_name,
              b.model_id,
              mo.name AS model_name,
              b.problem_id,
              pr.name AS problem_name,
              b.notes,
              b.status,
              b.created_at
            FROM bookings b
            JOIN brands br ON br.id = b.brand_id
            JOIN models mo ON mo.id = b.model_id
            JOIN problems pr ON pr.id = b.problem_id
            WHERE b.id = ?;
            """,
            (int(booking_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_brands() -> List[Dict[str, Any]]:
    """List all brands."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, name FROM brands ORDER BY name;").fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


def list_models(brand_id: int) -> List[Dict[str, Any]]:
    """List models by brand."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, brand_id, name FROM models WHERE brand_id = ? ORDER BY name;",
            (int(brand_id),),
        ).fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


def list_problems() -> List[Dict[str, Any]]:
    """List all problems."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, name FROM problems ORDER BY name;").fetchall()
        return rows_to_dicts(rows)
    finally:
        conn.close()


def list_admin_bookings(
    status: Optional[str] = None,
    brand_id: Optional[int] = None,
    model_id: Optional[int] = None,
    problem_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """List bookings for admin with optional filters; returns (rows, total_count)."""
    where: List[str] = []
    params: List[Any] = []

    if status:
        where.append("b.status = ?")
        params.append(status)
    if brand_id is not None:
        where.append("b.brand_id = ?")
        params.append(int(brand_id))
    if model_id is not None:
        where.append("b.model_id = ?")
        params.append(int(model_id))
    if problem_id is not None:
        where.append("b.problem_id = ?")
        params.append(int(problem_id))
    if search:
        where.append(
            "(LOWER(b.customer_name) LIKE ? OR LOWER(b.email) LIKE ? OR LOWER(b.phone) LIKE ?)"
        )
        s = f"%{search.lower()}%"
        params.extend([s, s, s])

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    conn = get_connection()
    try:
        count_row = conn.execute(
            f"SELECT COUNT(1) AS cnt FROM bookings b {where_sql};", params
        ).fetchone()
        total = int(count_row["cnt"])

        rows = conn.execute(
            f"""
            SELECT
              b.id,
              b.customer_name,
              b.phone,
              b.email,
              b.status,
              b.created_at,
              br.name AS brand_name,
              mo.name AS model_name,
              pr.name AS problem_name
            FROM bookings b
            JOIN brands br ON br.id = b.brand_id
            JOIN models mo ON mo.id = b.model_id
            JOIN problems pr ON pr.id = b.problem_id
            {where_sql}
            ORDER BY b.created_at DESC
            LIMIT ? OFFSET ?;
            """,
            params + [int(limit), int(offset)],
        ).fetchall()
        return rows_to_dicts(rows), total
    finally:
        conn.close()


def update_booking_status(booking_id: int, status: str) -> bool:
    """Update booking status; return True if booking existed."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE bookings SET status = ? WHERE id = ?;", (status, int(booking_id))
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
