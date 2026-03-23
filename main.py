"""
main.py — Entry point for the Data Validation Agent.

Orchestrates the complete validation pipeline:
    1. Load and validate the dataset (CSV)
    2. Run all rule-based validation checks
    3. Print structured console summary
    4. Generate the HTML compliance report
    5. Log results to output/validation.log

Usage:
    python main.py

The dataset must exist at data/sample_dataset.csv before running.
Generate it by running:
    python data/generate_dataset.py
"""

import os
import sys
import pandas as pd

# Ensure the project root is on sys.path so imports work correctly
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import logger as log_module
from agent.validator import DataValidator
from report.report_generator import generate_report


# ── Path constants ────────────────────────────────────────────────────────────
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.yaml")
DATASET_PATH = os.path.join(PROJECT_ROOT, "data", "sample_dataset.csv")
REPORT_PATH = os.path.join(PROJECT_ROOT, "output", "report.html")


def _print_divider(char: str = "─", width: int = 60) -> None:
    """Print a horizontal divider of the given character and width."""
    print(char * width)


def _print_header() -> None:
    """Print the stylised console header block."""
    _print_divider("═")
    print("  DATA VALIDATION AGENT — Compliance Pipeline")
    print("  Neon AI | Data Validation Suite v1.0")
    _print_divider("═")


def _print_summary(summary: dict) -> None:
    """
    Print the structured validation summary to stdout.

    Args:
        summary: The dict returned by DataValidator.validate().
    """
    _print_divider()
    print("VALIDATION SUMMARY")
    _print_divider()
    print(f"  Total Records Validated : {summary['total_records']}")
    print(f"  ✓ Records Passed        : {summary['pass_count']}")
    print(f"  ✗ Total Findings        : {summary['total_findings']}")
    print(f"  ● Critical Issues       : {summary['critical_count']}")
    print(f"  ▲ Warnings              : {summary['warning_count']}")
    _print_divider()

    if summary["escalation_required"]:
        print("  ⚠  COMPLIANCE ESCALATION REQUIRED")
        _print_divider()


def _print_findings(findings: list[dict]) -> None:
    """
    Print a structured table of all validation findings to stdout.

    Args:
        findings: List of finding dicts from the validation summary.
    """
    if not findings:
        print("  No findings — all records passed validation.")
        return

    # Sort: CRITICAL first, then WARNING; within each group sort by row
    severity_order = {"CRITICAL": 0, "WARNING": 1}
    sorted_findings = sorted(
        findings,
        key=lambda f: (
            severity_order.get(f.get("severity", "WARNING"), 99),
            f.get("row", 0),
        ),
    )

    col_widths = {
        "row": 5,
        "entity_id": 14,
        "rule": 24,
        "field": 22,
        "severity": 10,
        "message": 52,
    }

    header = (
        f"{'ROW':<{col_widths['row']}} "
        f"{'ENTITY ID':<{col_widths['entity_id']}} "
        f"{'RULE':<{col_widths['rule']}} "
        f"{'FIELD':<{col_widths['field']}} "
        f"{'SEVERITY':<{col_widths['severity']}} "
        f"MESSAGE"
    )
    print(header)
    print("-" * len(header))

    for f in sorted_findings:
        row = str(f.get("row", "?"))
        entity_id = str(f.get("entity_id", "?"))
        rule = str(f.get("rule", "?"))
        field = str(f.get("field", "?"))
        severity = str(f.get("severity", "?"))
        message = str(f.get("message", ""))[:col_widths["message"]]

        line = (
            f"{row:<{col_widths['row']}} "
            f"{entity_id:<{col_widths['entity_id']}} "
            f"{rule:<{col_widths['rule']}} "
            f"{field:<{col_widths['field']}} "
            f"{severity:<{col_widths['severity']}} "
            f"{message}"
        )
        print(line)


def main() -> None:
    """
    Run the complete Data Validation Agent pipeline.

    Steps:
        1. Print header and load the CSV dataset.
        2. Instantiate DataValidator with config.yaml.
        3. Run validation — all 4 rule modules execute in sequence.
        4. Print the summary and all findings to console.
        5. Generate the HTML report to output/report.html.

    Raises:
        SystemExit: If the dataset file cannot be found.
    """
    _print_header()

    # ── Step 1: Load dataset ──────────────────────────────────────────────────
    if not os.path.exists(DATASET_PATH):
        print(f"\n  ERROR: Dataset not found at {DATASET_PATH}")
        print("  Please run:  python data/generate_dataset.py\n")
        sys.exit(1)

    log_module.logger.info(f"Loading dataset: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    print(f"\n  Dataset loaded: {len(df)} records from {DATASET_PATH}\n")

    # ── Step 2: Validate ──────────────────────────────────────────────────────
    print("Running validation checks …")
    validator = DataValidator(config_path=CONFIG_PATH)
    summary = validator.validate(df)
    print()

    # ── Step 3: Console output ────────────────────────────────────────────────
    _print_summary(summary)
    print()
    print("FINDINGS DETAIL")
    _print_divider()
    _print_findings(summary["findings"])
    print()

    # ── Step 4: Generate report ───────────────────────────────────────────────
    _print_divider()
    print("Generating HTML report …")
    os.makedirs(os.path.join(PROJECT_ROOT, "output"), exist_ok=True)
    generate_report(summary, REPORT_PATH)
    print()

    _print_divider("═")
    print("  Pipeline complete. See output/report.html for full details.")
    _print_divider("═")


if __name__ == "__main__":
    main()
