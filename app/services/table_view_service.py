from app.models.tables import get_table
from app.models.templates import get_template
from app.services.row_service import list_rows


def get_table_view(table_id: int, from_date: str, to_date: str) -> dict:
    # 1) Load table instance (name, template_id, etc.)
    table = get_table(table_id)

    # 2) Load template schema used by this table
    template = get_template(table["template_id"])

    # 3) Load rows for date range (already includes computed fields)
    rows = list_rows(table_id=table_id, from_date=from_date, to_date=to_date)

    # 4) Bundle everything frontend needs
    return {
        "table": table,
        "template": template,
        "rows": rows,
    }
