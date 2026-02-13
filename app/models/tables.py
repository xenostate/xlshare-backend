import psycopg2
from app.db import get_connection


def list_tables(template_id: int) -> list[dict]:
    query = """
    SELECT id, template_id, name, is_archived, created_at, period_start
    FROM tables
    WHERE template_id = %s
    ORDER BY period_start DESC;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (template_id,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]
    finally:
        conn.close()

def get_table(table_id: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, template_id, name, is_archived, created_at, period_start FROM tables WHERE id = %s;",
                (table_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Table not found: {table_id}")

            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()


def create_month_table(template_id: int, name: str, period_start: str) -> dict:
    query = """
    INSERT INTO tables (template_id, name, period_start)
    VALUES (%s, %s, %s)
    RETURNING id, template_id, name, is_archived, created_at, period_start;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (template_id, name, period_start))
            row = cur.fetchone()
            conn.commit()
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_table_by_template_and_period(template_id: int, period_start: str) -> dict | None:
    query = """
    SELECT id, template_id, name, is_archived, created_at, period_start
    FROM tables
    WHERE template_id = %s AND period_start = %s
    LIMIT 1;
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (template_id, period_start))
            row = cur.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()
