import json
from app.db import get_connection

def get_template(template_id: int) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, description, schema_json FROM table_templates WHERE id = %s;",
                (template_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Template not found: {template_id}")

            cols = [d[0] for d in cur.description]
            res = dict(zip(cols, row))

            # psycopg2 often returns jsonb as Python dict already,
            # but in some configs it may return a string. Normalize:
            if isinstance(res["schema_json"], str):
                res["schema_json"] = json.loads(res["schema_json"])

            return res
    finally:
        conn.close()
