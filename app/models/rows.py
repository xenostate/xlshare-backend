import json
from app.db import get_connection

def upsert_row(table_id: int, row_date: str, data: dict, user_id: int) -> dict:
    query = """
    INSERT INTO table_rows (
      table_id,
      row_date,
      data,
      created_by
    )
    VALUES (%s, %s, %s::jsonb, %s)
    ON CONFLICT (table_id, row_date)
    DO UPDATE SET
      data = EXCLUDED.data,
      updated_by = EXCLUDED.created_by,
      updated_at = now(),
      version = table_rows.version + 1
    RETURNING *;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (table_id, row_date, json.dumps(data), user_id))
            row = cur.fetchone()
            colnames = [desc[0] for desc in cur.description]
            conn.commit()
            return dict(zip(colnames, row))
    finally:
        conn.close()


def get_rows(table_id: int, date_from: str, date_to: str) -> list[dict]:
    query = """
    SELECT *
    FROM table_rows
    WHERE table_id = %s AND row_date BETWEEN %s AND %s
    ORDER BY row_date;
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (table_id, date_from, date_to))
            rows = cur.fetchall()
            colnames = [desc[0] for desc in cur.description]
            return [dict(zip(colnames, row)) for row in rows]
    finally:
        conn.close()
