"""
generate_dataset.py — Synthetic compliance dataset generator.

Generates sample_dataset.csv with 40 records including intentional flaws
for use by the Data Validation Agent. Uses a fixed random seed of 42 for
reproducibility. Run this script once before running main.py.

Usage:
    python data/generate_dataset.py
"""

import os
import pandas as pd
import numpy as np
from datetime import date, timedelta

# Fixed random seed for reproducibility
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

NUM_RECORDS = 40
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "sample_dataset.csv")


def generate_dataset() -> pd.DataFrame:
    """
    Generate a synthetic compliance dataset with 40 records.

    Includes 30 clean records and 12 injected flaws at specific rows
    as defined in the project specification.

    Returns:
        pd.DataFrame: The generated dataset.
    """
    departments = ["Finance", "Operations", "Risk", "Compliance"]
    statuses = ["clear", "flagged"]

    # Base date for report_dates
    base_date = date(2024, 1, 1)

    records = []
    for i in range(1, NUM_RECORDS + 1):
        entity_id = f"ENT-{i:04d}"
        report_date = (base_date + timedelta(days=i - 1)).strftime("%Y-%m-%d")
        department = departments[(i - 1) % len(departments)]
        transaction_amount = round(np.random.uniform(1000, 500000), 2)
        risk_score = round(np.random.uniform(1, 80), 2)
        status = "clear"
        reviewer_id = f"REV-{((i - 1) % 5) + 1:03d}"
        data_completeness = round(np.random.uniform(60, 99), 2)
        reported_by = f"USER-{((i - 1) % 10) + 1:03d}"
        notes = f"Submission notes for record {i}"

        records.append({
            "entity_id": entity_id,
            "report_date": report_date,
            "department": department,
            "transaction_amount": transaction_amount,
            "risk_score": risk_score,
            "status": status,
            "reviewer_id": reviewer_id,
            "data_completeness": data_completeness,
            "reported_by": reported_by,
            "notes": notes,
        })

    df = pd.DataFrame(records)

    # -----------------------------------------------------------------------
    # Inject flaws as specified in PROJECT_SPEC.md (1-based row indices)
    # -----------------------------------------------------------------------

    # Missing values — CRITICAL
    df.at[2, "risk_score"] = np.nan           # Row 3 (0-indexed: 2)
    df.at[6, "report_date"] = np.nan          # Row 7 (0-indexed: 6)
    df.at[11, "transaction_amount"] = np.nan  # Row 12 (0-indexed: 11)
    df.at[17, "entity_id"] = np.nan           # Row 18 (0-indexed: 17)

    # Threshold breaches — CRITICAL
    df.at[4, "transaction_amount"] = 2500000.0   # Row 5: exceeds max 1,000,000
    df.at[14, "risk_score"] = 105.0              # Row 15: exceeds max 100
    df.at[24, "data_completeness"] = -5.0        # Row 25: below min 0

    # Anomalies (statistical outliers) — WARNING
    df.at[8, "transaction_amount"] = 9800000.0   # Row 9: extreme outlier
    df.at[19, "risk_score"] = 0.01               # Row 20: extreme outlier
    df.at[29, "data_completeness"] = 0.5         # Row 30: extreme outlier

    # Cross-field violations — CRITICAL
    # status=flagged but reviewer_id=null
    df.at[21, "status"] = "flagged"              # Row 22
    df.at[21, "reviewer_id"] = np.nan

    df.at[34, "status"] = "flagged"              # Row 35
    df.at[34, "reviewer_id"] = np.nan

    return df


def main():
    """Generate and save the dataset CSV."""
    df = generate_dataset()
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset generated: {len(df)} records saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
