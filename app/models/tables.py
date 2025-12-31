from app.db import get_connection

def get_table(table_id: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, template_id, name, is_archived, created_at FROM tables WHERE id = %s;",
                (table_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Table not found: {table_id}")

            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))
    finally:
        conn.close()
