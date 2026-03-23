"""
threshold.py — Rule 2: Threshold validation.

Checks each row's numeric fields against configured min/max thresholds.
Skips null values (already caught by missing_value check).
Returns a list of CRITICAL findings for any threshold breach.
"""

import math
import pandas as pd


def check_thresholds(df: pd.DataFrame, thresholds: dict) -> list[dict]:
    """
    Validate numeric fields against their configured min and max thresholds.

    Null values are skipped — they are handled by the missing value rule.
    Any value that falls below the configured minimum or above the configured
    maximum is reported as a CRITICAL THRESHOLD_VIOLATION.

    Args:
        df: The compliance dataset as a pandas DataFrame.
        thresholds: Dict mapping field names to {"min": float, "max": float}.

    Returns:
        List of finding dicts for every threshold violation found.
    """
    findings = []

    for idx, row in df.iterrows():
        row_number = int(idx) + 1  # 1-based

        entity_id_val = row.get("entity_id", None)
        try:
            entity_id = str(entity_id_val) if not _is_null(entity_id_val) else "UNKNOWN"
        except Exception:
            entity_id = "UNKNOWN"

        for field, limits in thresholds.items():
            value = row.get(field, None)

            # Skip nulls — already handled by missing value rule
            if _is_null(value):
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue

            min_val = limits.get("min")
            max_val = limits.get("max")

            if min_val is not None and numeric_value < min_val:
                findings.append(_build_finding(
                    row_number=row_number,
                    entity_id=entity_id,
                    field=field,
                    value=numeric_value,
                    message=f"{field} value {numeric_value} is below minimum threshold of {min_val}",
                ))
            elif max_val is not None and numeric_value > max_val:
                findings.append(_build_finding(
                    row_number=row_number,
                    entity_id=entity_id,
                    field=field,
                    value=numeric_value,
                    message=f"{field} value {numeric_value} exceeds maximum threshold of {max_val}",
                ))

    return findings


def _build_finding(
    row_number: int,
    entity_id: str,
    field: str,
    value: float,
    message: str,
) -> dict:
    """
    Build a standard threshold violation finding dict.

    Args:
        row_number: 1-based row number in the dataset.
        entity_id: Entity identifier string.
        field: The field that violated the threshold.
        value: The offending numeric value.
        message: Human-readable description of the violation.

    Returns:
        A findings dict with standard keys.
    """
    return {
        "row": row_number,
        "entity_id": entity_id,
        "rule": "THRESHOLD_VIOLATION",
        "field": field,
        "value": value,
        "severity": "CRITICAL",
        "message": message,
    }


def _is_null(value) -> bool:
    """
    Check whether a value is null/NaN.

    Args:
        value: Value to check.

    Returns:
        True if the value is None, NaN, or pandas NA.
    """
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    try:
        return pd.isna(value)
    except (TypeError, ValueError):
        return False
