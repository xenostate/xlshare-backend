import json
from datetime import datetime, timezone
from app.db import get_connection


def _to_dict(row, colnames):
    res = dict(zip(colnames, row))
    # Normalize jsonb if it ever appears (placeholder for future profile data)
    for key, val in res.items():
        if isinstance(val, str) and key.endswith("_json"):
            try:
                res[key] = json.loads(val)
            except Exception:
                pass
    return res


def create_user(email: str, name: str, password_hash: str, is_active: bool = True, is_admin: bool = False) -> dict:
    query = """
    INSERT INTO users (email, name, password_hash, is_active, created_at, is_admin)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING *;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                query,
                (email, name, password_hash, is_active, datetime.now(timezone.utc), is_admin),
            )
            row = cur.fetchone()
            colnames = [desc[0] for desc in cur.description]
            conn.commit()
            return _to_dict(row, colnames)
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    query = "SELECT * FROM users WHERE email = %s LIMIT 1;"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (email,))
            row = cur.fetchone()
            if row is None:
                return None
            colnames = [desc[0] for desc in cur.description]
            return _to_dict(row, colnames)
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    query = "SELECT * FROM users WHERE id = %s LIMIT 1;"
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            row = cur.fetchone()
            if row is None:
                return None
            colnames = [desc[0] for desc in cur.description]
            return _to_dict(row, colnames)
    finally:
        conn.close()
