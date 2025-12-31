import json

def filter_editable_keys(schema_json: dict, incoming: dict) -> dict:
    editable = {
        c["key"] for c in schema_json.get("columns", [])
        if c.get("editable") is True
    }
    return {k: incoming[k] for k in incoming.keys() if k in editable}
