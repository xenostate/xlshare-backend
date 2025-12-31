from app.models.tables import get_table
from app.models.templates import get_template

def get_template_schema_for_table(table_id: int) -> dict:
    table = get_table(table_id)
    template = get_template(table["template_id"])
    return template["schema_json"]
