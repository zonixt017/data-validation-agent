"""
missing_value.py — Rule 1: Missing value detection.

Checks each row in the dataframe for missing values in required fields.
Returns a list of findings in the standard findings dict format.
"""

import pandas as pd
from typing import Any


def check_missing_values(df: pd.DataFrame, required_fields: list[str]) -> list[dict]:
    """
    Check all rows for missing values in the required fields.

    A value is considered missing if it is NaN, None, or an empty string.

    Args:
        df: The compliance dataset as a pandas DataFrame.
        required_fields: List of field names that must not be missing.

    Returns:
        List of finding dicts, each describing a missing value violation.
        Each finding has keys: row, entity_id, rule, field, value,
        severity, message.
    """
    findings = []

    for idx, row in df.iterrows():
        row_number = int(idx) + 1  # Convert to 1-based

        # Safely get entity_id (may itself be missing)
        entity_id_val = row.get("entity_id", None)
        try:
            entity_id = str(entity_id_val) if not _is_missing(entity_id_val) else "UNKNOWN"
        except Exception:
            entity_id = "UNKNOWN"

        for field in required_fields:
            value: Any = row.get(field, None)
            if _is_missing(value):
                findings.append({
                    "row": row_number,
                    "entity_id": entity_id,
                    "rule": "MISSING_VALUE",
                    "field": field,
                    "value": None,
                    "severity": "CRITICAL",
                    "message": f"Required field '{field}' is missing",
                })

    return findings


def _is_missing(value: Any) -> bool:
    """
    Determine whether a value should be considered missing.

    Args:
        value: The field value to check.

    Returns:
        True if the value is None, NaN, or empty string.
    """
    if value is None:
        return True
    if isinstance(value, float):
        import math
        return math.isnan(value)
    if isinstance(value, str):
        return value.strip() == ""
    # pandas NA
    try:
        return pd.isna(value)
    except (TypeError, ValueError):
        return False
