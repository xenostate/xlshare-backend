from fastapi import FastAPI, Query, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from datetime import datetime

from app.db import get_connection
from app.services.row_service import save_row, list_rows
from app.services.table_view_service import get_table_view
from app.models.tables import list_tables, create_month_table, get_table_by_template_and_period
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_user_by_token,
    register_user,
    sanitize_user,
)
from app.services.row_service import set_month_plan

app = FastAPI(title="Coal Reports API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:5173"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class LoginRequest(BaseModel):
    login: str
    password: str


class CreateMonthRequest(BaseModel):
    template_id: int
    year: int
    month: int


class PlanUpdate(BaseModel):
    month: str  # YYYY-MM or YYYY-MM-DD
    prod_plan_month_t: float | None = None
    ovb_plan_month_m3: float | None = None


class CreateUserRequest(BaseModel):
    login: str
    name: str
    password: str
    is_admin: bool = False


def get_current_user(token: str = Depends(oauth2_scheme)):
    return get_user_by_token(token)


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
def debug_save_row(
    table_id: int,
    row_date: str,
    payload: dict = Body(...),
    current_user=Depends(get_current_user),
):
    user_id = current_user["id"]
    return save_row(table_id=table_id, row_date=row_date, incoming_data=payload, user_id=user_id)


@app.get("/debug/tables/{table_id}/rows")
def debug_list_rows(
    table_id: int,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    current_user=Depends(get_current_user),
):
    return list_rows(table_id=table_id, from_date=from_date, to_date=to_date)


@app.get("/tables/{table_id}/view")
def table_view(
    table_id: int,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    current_user=Depends(get_current_user),
):
    return get_table_view(table_id=table_id, from_date=from_date, to_date=to_date)


@app.get("/tables")
def list_tables_route(
    template_id: int,
    current_user=Depends(get_current_user),
):
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return list_tables(template_id)


@app.post("/tables/create-month")
def create_month_route(
    payload: CreateMonthRequest,
    current_user=Depends(get_current_user),
):
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    try:
        period_start = datetime(payload.year, payload.month, 1).date().isoformat()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year or month",
        )

    name = f"Отчет по углю — {payload.year:04d}-{payload.month:02d}"
    try:
        return create_month_table(
            template_id=payload.template_id,
            name=name,
            period_start=period_start,
        )
    except Exception as e:
        # Unique violation or other DB issues
        if hasattr(e, "pgcode") and e.pgcode == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Table for this month already exists",
            )
        raise


@app.get("/tables/current")
def current_table(
    template_id: int,
    current_user=Depends(get_current_user),
):
    today = datetime.utcnow().date()
    period_start = today.replace(day=1).isoformat()
    table = get_table_by_template_and_period(template_id, period_start)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current month table not found",
        )
    return table


@app.put("/tables/{table_id}/plan")
def update_plan(
    table_id: int,
    payload: PlanUpdate,
    current_user=Depends(get_current_user),
):
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    # Normalize month start
    month_str = payload.month
    if len(month_str) == 7:  # YYYY-MM
        month_str = f"{month_str}-01"
    try:
        month_start = datetime.fromisoformat(month_str).date().replace(day=1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid month format. Use YYYY-MM or YYYY-MM-DD.",
        )

    if payload.prod_plan_month_t is None and payload.ovb_plan_month_m3 is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one plan value to update.",
        )

    set_month_plan(
        table_id=table_id,
        month_start=month_start,
        user_id=current_user["id"],
        prod_plan_month=payload.prod_plan_month_t,
        ovb_plan_month=payload.ovb_plan_month_m3,
    )
    return {"status": "ok"}


@app.post("/auth/login")
def auth_login(payload: LoginRequest):
    user = authenticate_user(login=payload.login, password=payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login or password",
        )
    token = create_access_token({"sub": str(user["id"])})
    return {"access_token": token, "token_type": "bearer", "user": sanitize_user(user)}


@app.get("/me")
def me(current_user=Depends(get_current_user)):
    return sanitize_user(current_user)


@app.post("/admin/users")
def create_user_admin(
    payload: CreateUserRequest,
    current_user=Depends(get_current_user),
):
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    user = register_user(
        email=payload.login,
        name=payload.name,
        password=payload.password,
        is_admin=payload.is_admin,
    )
    return sanitize_user(user)
