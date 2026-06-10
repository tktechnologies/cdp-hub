"""cdp_skus intake sheet status column names (user-facing headers include robot emoji)."""
from __future__ import annotations

ROBOT_SUFFIX = " 🤖"
STATUS_COLUMN_IDS = ("PROCESSADO", "ENCONTRADO", "NOTIFICADO")

PICK_SHEET_FIELD_JS = """function pickSheetField(row, base) {
  if (!row || typeof row !== 'object') return '';
  const robot = base + ' 🤖';
  for (const k of [base, robot]) {
    const v = row[k];
    if (v !== null && v !== undefined && String(v).trim() !== '') return v;
  }
  return row[base] ?? row[robot] ?? '';
}
"""


def base_column_id(col_id: str) -> str:
    if col_id.endswith(ROBOT_SUFFIX):
        return col_id[: -len(ROBOT_SUFFIX)]
    return col_id


def sheet_column_id(col_id: str) -> str:
    base = base_column_id(col_id)
    if base in STATUS_COLUMN_IDS:
        return f"{base}{ROBOT_SUFFIX}"
    return col_id


def sheet_display_name(col_id: str) -> str:
    return sheet_column_id(col_id)


def patch_status_column_values(columns: dict) -> bool:
    value = columns.get("value")
    if not isinstance(value, dict):
        return False
    changed = False
    for col_id in STATUS_COLUMN_IDS:
        display = sheet_column_id(col_id)
        if col_id in value and display not in value:
            value[display] = value.pop(col_id)
            changed = True
        elif col_id in value and display in value:
            value.pop(col_id)
            changed = True
    return changed


def patch_status_column_schema(columns: dict) -> bool:
    """Set Google Sheets node displayName for robot-managed status columns."""
    if not isinstance(columns, dict):
        return False
    changed = False
    schema = columns.get("schema")
    if isinstance(schema, list):
        for entry in schema:
            if not isinstance(entry, dict):
                continue
            col_id = str(entry.get("id", ""))
            base = base_column_id(col_id)
            if base not in STATUS_COLUMN_IDS:
                continue
            expected = sheet_column_id(base)
            if entry.get("id") != expected:
                entry["id"] = expected
                changed = True
            if entry.get("displayName") != expected:
                entry["displayName"] = expected
                changed = True
    return changed


def patch_status_columns(columns: dict) -> bool:
    schema_changed = patch_status_column_schema(columns)
    values_changed = patch_status_column_values(columns)
    return schema_changed or values_changed
