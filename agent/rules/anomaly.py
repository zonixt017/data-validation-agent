"""
anomaly.py — Rule 3: Statistical anomaly detection.

Uses the Z-score method to detect outlier values in numeric fields.
Rows with |z-score| exceeding the configured threshold are flagged
as WARNING-level anomalies.
"""

import math
import numpy as np
import pandas as pd
from scipy import stats


def check_anomalies(df: pd.DataFrame, anomaly_config: dict) -> list[dict]:
    """
    Detect statistical anomalies in numeric fields using the Z-score method.

    For each configured field, computes the Z-score across all non-null values.
    Rows where the absolute Z-score exceeds the configured threshold are flagged.

    Args:
        df: The compliance dataset as a pandas DataFrame.
        anomaly_config: Dict with keys:
            - method (str): Detection method, currently only "zscore" supported.
            - zscore_threshold (float): Absolute Z-score threshold for flagging.
            - fields (list[str]): Fields to analyse for anomalies.

    Returns:
        List of finding dicts for every anomaly detected (severity = WARNING).
    """
    method = anomaly_config.get("method", "zscore")
    zscore_threshold = float(anomaly_config.get("zscore_threshold", 3.0))
    fields = anomaly_config.get("fields", [])

    if method != "zscore":
        raise ValueError(f"Unsupported anomaly detection method: '{method}'")

    findings = []

    for field in fields:
        if field not in df.columns:
            continue

        # Work only with non-null numeric values in this column
        series = pd.to_numeric(df[field], errors="coerce")
        non_null_mask = series.notna()
        non_null_values = series[non_null_mask]

        if len(non_null_values) < 3:
            # Not enough data for meaningful Z-score computation
            continue

        # Compute Z-scores for non-null entries
        z_scores = np.abs(stats.zscore(non_null_values.values))

        # Map back to original DataFrame indices
        non_null_indices = non_null_values.index

        for i, (orig_idx, z) in enumerate(zip(non_null_indices, z_scores)):
            if z > zscore_threshold:
                row_number = int(orig_idx) + 1  # 1-based

                entity_id_val = df.at[orig_idx, "entity_id"] if "entity_id" in df.columns else None
                try:
                    entity_id = (
                        str(entity_id_val)
                        if not _is_null(entity_id_val)
                        else "UNKNOWN"
                    )
                except Exception:
                    entity_id = "UNKNOWN"

                numeric_value = float(series.at[orig_idx])

                findings.append({
                    "row": row_number,
                    "entity_id": entity_id,
                    "rule": "ANOMALY_DETECTED",
                    "field": field,
                    "value": numeric_value,
                    "severity": "WARNING",
                    "message": (
                        f"{field} value {numeric_value} is anomalous "
                        f"(z-score: {z:.2f})"
                    ),
                })

    return findings


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
