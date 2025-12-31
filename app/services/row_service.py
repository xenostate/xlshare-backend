from app.services.template_service import get_template_schema_for_table
from app.utils.sanitize import filter_editable_keys
from app.models.rows import upsert_row
from app.models.rows import get_rows

def save_row(table_id: int, row_date: str, incoming_data: dict, user_id: int) -> dict:
    schema = get_template_schema_for_table(table_id)
    clean = filter_editable_keys(schema, incoming_data)
    return upsert_row(table_id=table_id, row_date=row_date, data=clean, user_id=user_id)


def list_rows(table_id: int, from_date: str, to_date: str) -> list[dict]:
    rows = get_rows(table_id, from_date, to_date)
    return [add_computed_fields(r) for r in rows]


def _to_number(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v.strip() == "":
        return 0.0
    return float(v)  # will throw if truly invalid

def _pct(fact, plan):
    plan = _to_number(plan)
    fact = _to_number(fact)
    if plan == 0:
        return None
    return 100.0 * fact / plan


def add_computed_fields(row: dict) -> dict:
    data = row.get("data") or {}
    # Work on a copy so we don't mutate unexpectedly
    out_data = dict(data)

    # Production computed fields
    prod_plan_td = _to_number(out_data.get("prod_plan_to_date_t"))
    prod_fact_td = _to_number(out_data.get("prod_fact_to_date_t"))
    out_data["prod_dev_to_date_t"] = prod_fact_td - prod_plan_td
    out_data["prod_pct_to_date"] = _pct(prod_fact_td, prod_plan_td)

    # Overburden computed fields
    ovb_plan_td = _to_number(out_data.get("ovb_plan_to_date_m3"))
    ovb_fact_td = _to_number(out_data.get("ovb_fact_to_date_m3"))
    out_data["ovb_dev_to_date_m3"] = ovb_fact_td - ovb_plan_td
    out_data["ovb_pct_to_date"] = _pct(ovb_fact_td, ovb_plan_td)

    # Return row with augmented data
    out = dict(row)
    out["data"] = out_data
    return out

