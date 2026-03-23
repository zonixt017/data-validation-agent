"""
cross_field.py — Rule 4: Cross-field validation.

Validates conditional relationships between fields, defined in config.yaml.
For example: if status == "flagged", then reviewer_id must not be null.
Works generically from the configured rule list — no hardcoded logic.
"""

import math
import pandas as pd


def check_cross_fields(df: pd.DataFrame, cross_field_rules: list[dict]) -> list[dict]:
    """
    Validate cross-field conditions defined in the configuration.

    Iterates over each configured rule. For each rule:
    - Finds rows where if_field == if_value
    - Checks whether then_field satisfies then_condition for those rows
    - Reports CRITICAL violations for any rows that fail

    Supported then_condition values:
        - "not_null": the then_field must not be null/empty

    Args:
        df: The compliance dataset as a pandas DataFrame.
        cross_field_rules: List of rule dicts from config, each with:
            - description (str): Human-readable rule description.
            - if_field (str): The conditional field name.
            - if_value (str): The value that triggers the rule.
            - then_field (str): The field whose condition is checked.
            - then_condition (str): The condition to enforce.

    Returns:
        List of finding dicts for every cross-field violation (severity = CRITICAL).
    """
    findings = []

    for rule in cross_field_rules:
        if_field = rule.get("if_field")
        if_value = rule.get("if_value")
        then_field = rule.get("then_field")
        then_condition = rule.get("then_condition")
        description = rule.get("description", "Cross-field rule violation")

        if not all([if_field, if_value, then_field, then_condition]):
            continue  # Skip malformed rules

        if if_field not in df.columns or then_field not in df.columns:
            continue

        for idx, row in df.iterrows():
            row_number = int(idx) + 1  # 1-based

            # Check if the trigger condition is met
            if_field_value = row.get(if_field)
            if str(if_field_value).strip() != str(if_value).strip():
                continue

            # Get entity_id for context
            entity_id_val = row.get("entity_id", None)
            try:
                entity_id = (
                    str(entity_id_val)
                    if not _is_null(entity_id_val)
                    else "UNKNOWN"
                )
            except Exception:
                entity_id = "UNKNOWN"

            # Evaluate then_condition
            then_value = row.get(then_field)
            violation = _evaluate_condition(then_value, then_condition)

            if violation:
                findings.append({
                    "row": row_number,
                    "entity_id": entity_id,
                    "rule": "CROSS_FIELD_VIOLATION",
                    "field": then_field,
                    "value": None if _is_null(then_value) else then_value,
                    "severity": "CRITICAL",
                    "message": (
                        f"Record is '{if_value}' but {then_field} is missing "
                        f"— escalation required"
                    ),
                })

    return findings


def _evaluate_condition(value, condition: str) -> bool:
    """
    Evaluate whether a field value fails a given condition.

    Args:
        value: The field value to evaluate.
        condition: The condition name to check (e.g., "not_null").

    Returns:
        True if the condition is VIOLATED (i.e., a finding should be raised).
    """
    if condition == "not_null":
        return _is_null(value)
    # Unknown conditions are treated as non-violations (fail safe)
    return False


def _is_null(value) -> bool:
    """
    Check whether a value is null/NaN/empty.

    Args:
        value: Value to check.

    Returns:
        True if the value is None, NaN, pandas NA, or empty string.
    """
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    try:
        return pd.isna(value)
    except (TypeError, ValueError):
        return False
