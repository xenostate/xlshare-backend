from datetime import date as dt_date
import calendar

from app.services.template_service import get_template_schema_for_table
from app.utils.sanitize import filter_editable_keys
from app.models.rows import upsert_row, get_rows, get_row

def save_row(table_id: int, row_date: str, incoming_data: dict, user_id: int) -> dict:
    schema = get_template_schema_for_table(table_id)
    clean = filter_editable_keys(schema, incoming_data)

    # Merge with existing stored data so unchanged fields are preserved.
    existing = get_row(table_id=table_id, row_date=row_date)
    existing_data = existing.get("data") if existing else {}
    merged = {**(existing_data or {}), **clean}

    return upsert_row(
        table_id=table_id,
        row_date=row_date,
        data=merged,
        user_id=user_id,
    )


def list_rows(table_id: int, from_date: str, to_date: str) -> list[dict]:
    # Always compute cumulative from the start of the month to ensure correct to-date values
    # even when the requested window starts mid-month.
    from_dt = dt_date.fromisoformat(from_date)
    to_dt = dt_date.fromisoformat(to_date)
    month_start = from_dt.replace(day=1).isoformat()

    rows = get_rows(table_id, month_start, to_date)
    rows_sorted = sorted(rows, key=lambda r: _to_date(r["row_date"]))

    running_prod = 0.0
    running_ovb = 0.0
    running_prod_plan = 0.0
    running_ovb_plan = 0.0
    prod_plan_month_total = None
    ovb_plan_month_total = None
    days_in_month = calendar.monthrange(from_dt.year, from_dt.month)[1]
    prod_plan_day_value = 0.0
    ovb_plan_day_value = 0.0
    computed = []
    for row in rows_sorted:
        data = row.get("data") or {}
        prod_day = _to_number(data.get("prod_fact_day_t")) or 0.0
        ovb_day = _to_number(data.get("ovb_fact_day_m3")) or 0.0

        if prod_plan_month_total is None:
            prod_plan_month_total = _to_number(data.get("prod_plan_to_date_t"))
        if ovb_plan_month_total is None:
            ovb_plan_month_total = _to_number(data.get("ovb_plan_to_date_m3"))

        prod_plan_day_value = (prod_plan_month_total or 0.0) / days_in_month
        ovb_plan_day_value = (ovb_plan_month_total or 0.0) / days_in_month

        running_prod += prod_day
        running_ovb += ovb_day
        running_prod_plan += prod_plan_day_value
        running_ovb_plan += ovb_plan_day_value

        computed.append(
            add_computed_fields(
                row,
                running_prod,
                running_ovb,
                running_prod_plan,
                running_ovb_plan,
                prod_plan_day_value,
                ovb_plan_day_value,
            )
        )

    # Return only rows within the requested window, keeping the computed to-date values.
    filtered = [
        r
        for r in computed
        if from_dt <= _to_date(r["row_date"]) <= to_dt
    ]

    # Normalize row_date to ISO strings in the response.
    for r in filtered:
        if isinstance(r.get("row_date"), dt_date):
            r["row_date"] = r["row_date"].isoformat()

    return filtered


def _to_date(value):
    if isinstance(value, dt_date):
        return value
    return dt_date.fromisoformat(str(value))


def _to_number(v):
    """
    Convert value to float; return None if it cannot be parsed.
    This keeps bad user input from crashing the view loader.
    """
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        stripped = v.strip()
        if stripped == "":
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _round2(v):
    if v is None:
        return None
    return round(v, 2)

def _pct(fact, plan):
    plan = _to_number(plan)
    fact = _to_number(fact)
    if plan is None or fact is None or plan == 0:
        return None
    return 100.0 * fact / plan


def add_computed_fields(
    row: dict,
    prod_fact_to_date: float,
    ovb_fact_to_date: float,
    prod_plan_to_date: float,
    ovb_plan_to_date: float,
    prod_plan_day: float,
    ovb_plan_day: float,
) -> dict:
    data = row.get("data") or {}
    # Work on a copy so we don't mutate unexpectedly
    out_data = dict(data)

    # Production computed fields (to-date fact and plan are enforced from running sums)
    prod_plan_td = prod_plan_to_date
    out_data["prod_fact_to_date_t"] = _round2(prod_fact_to_date)
    out_data["prod_plan_to_date_t"] = _round2(prod_plan_td)
    out_data["prod_plan_day_t"] = _round2(prod_plan_day)
    if prod_plan_td is not None:
        out_data["prod_dev_to_date_t"] = _round2(prod_fact_to_date - prod_plan_td)
    out_data["prod_pct_to_date"] = _round2(_pct(prod_fact_to_date, prod_plan_td))

    # Overburden computed fields
    ovb_plan_td = ovb_plan_to_date
    out_data["ovb_fact_to_date_m3"] = _round2(ovb_fact_to_date)
    out_data["ovb_plan_to_date_m3"] = _round2(ovb_plan_td)
    out_data["ovb_plan_day_m3"] = _round2(ovb_plan_day)
    if ovb_plan_td is not None:
        out_data["ovb_dev_to_date_m3"] = _round2(ovb_fact_to_date - ovb_plan_td)
    out_data["ovb_pct_to_date"] = _round2(_pct(ovb_fact_to_date, ovb_plan_td))

    # Return row with augmented data
    out = dict(row)
    out["data"] = out_data
    return out


def set_month_plan(
    table_id: int,
    month_start: dt_date,
    user_id: int,
    prod_plan_month: float | None = None,
    ovb_plan_month: float | None = None,
) -> list[dict]:
    """
    Update or set monthly plan totals for all rows in the month. Creates a stub
    row on the first day if none exist.
    """
    month_end = month_start.replace(
        day=calendar.monthrange(month_start.year, month_start.month)[1]
    )
    rows = get_rows(table_id, month_start.isoformat(), month_end.isoformat())

    targets = rows or [
        {
            "table_id": table_id,
            "row_date": month_start.isoformat(),
            "data": {},
        }
    ]

    updated = []
    for row in targets:
        data = dict(row.get("data") or {})
        if prod_plan_month is not None:
            data["prod_plan_to_date_t"] = prod_plan_month
        if ovb_plan_month is not None:
            data["ovb_plan_to_date_m3"] = ovb_plan_month
        updated.append(
            upsert_row(
                table_id=table_id,
                row_date=row["row_date"],
                data=data,
                user_id=user_id,
            )
        )
    return updated
