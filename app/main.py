from fastapi import FastAPI, Query
from app.db import get_connection
from fastapi import Body
from app.services.row_service import save_row
from app.services.row_service import list_rows
from app.services.table_view_service import get_table_view



app = FastAPI(title="Coal Reports API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/db-test")
def db_test():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT 1;")
    result = cur.fetchone()

    cur.close()
    conn.close()

    return {"db": "ok", "result": result[0]}


@app.put("/debug/tables/{table_id}/rows/{row_date}")
def debug_save_row(table_id: int, row_date: str, payload: dict = Body(...)):
    # temporary user_id until auth exists
    user_id = 1
    return save_row(table_id=table_id, row_date=row_date, incoming_data=payload, user_id=user_id)



@app.get("/debug/tables/{table_id}/rows")
def debug_list_rows(
    table_id: int,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
):
    return list_rows(table_id=table_id, from_date=from_date, to_date=to_date)

@app.get("/tables/{table_id}/view")
def table_view(
    table_id: int,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
):
    return get_table_view(table_id=table_id, from_date=from_date, to_date=to_date)
