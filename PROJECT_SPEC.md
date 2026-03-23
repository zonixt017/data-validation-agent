# Data Validation Agent — Project Specification

## Overview

This is a Python-based AI compliance monitoring prototype called the **Data Validation Agent**. It is Agent 3 in a larger AI Compliance Monitoring system. Its purpose is to validate operational data before regulatory reporting — ensuring data integrity, detecting anomalies, and verifying compliance with regulatory rules.

This is an interview assignment prototype. It must be clean, modular, production-style code — not a notebook or script dump. The evaluator is a technical founder who will review code quality, architecture decisions, and the validation report output.

---

## Tech Stack

- **Language:** Python 3.10+
- **Data handling:** pandas, numpy
- **Config parsing:** PyYAML
- **Anomaly detection:** scipy (zscore), numpy (IQR)
- **Report generation:** Jinja2 (HTML report)
- **Logging:** Python standard logging module
- **No external AI/ML frameworks needed** — rule-based validation engine only

Install dependencies via:
```
pip install pandas numpy scipy PyYAML jinja2
```

---

## Full Folder Structure

```
data_validation_agent/
│
├── data/
│   ├── generate_dataset.py        # Script to generate sample_dataset.csv
│   └── sample_dataset.csv         # Generated synthetic compliance dataset (40 records)
│
├── agent/
│   ├── __init__.py                # Empty init
│   ├── validator.py               # Core orchestrator — runs all 4 rule modules
│   └── rules/
│       ├── __init__.py            # Empty init
│       ├── missing_value.py       # Rule 1: Missing value detection
│       ├── threshold.py           # Rule 2: Threshold validation
│       ├── anomaly.py             # Rule 3: Statistical anomaly detection
│       └── cross_field.py         # Rule 4: Cross-field validation
│
├── report/
│   ├── report_generator.py        # Loads results, renders Jinja2 HTML report
│   └── template.html              # Jinja2 HTML template for the validation report
│
├── output/
│   └── validation_report.html     # Final generated report (created at runtime)
│
├── logger.py                      # Structured logger + escalation handler
├── config.yaml                    # All thresholds, required fields, rules config
├── main.py                        # Entry point — ties everything together
├── PROJECT_SPEC.md                # This file
├── TASKS.md                       # Build task list
└── README.md                      # Architecture explanation + how to run
```

---

## Dataset Details

### File: `data/generate_dataset.py`

This script generates `data/sample_dataset.csv` with 40 records. It must be run once before the agent.

### Fields in the dataset:

| Field | Type | Description |
|---|---|---|
| entity_id | string | Unique identifier e.g. ENT-0001 |
| report_date | string (YYYY-MM-DD) | Date of the report submission |
| department | string | One of: Finance, Operations, Risk, Compliance |
| transaction_amount | float | Transaction value in currency |
| risk_score | float | Risk score between 0-100 |
| status | string | Either "clear" or "flagged" |
| reviewer_id | string | Assigned reviewer e.g. REV-001 |
| data_completeness | float | Percentage 0-100 |
| reported_by | string | User who submitted e.g. USER-001 |
| notes | string | Submission notes |

### Injected flaws (intentional, for validation demo):

| Row | Flaw Type | Field Affected | Expected Severity |
|---|---|---|---|
| 3 | Missing value | risk_score | CRITICAL |
| 7 | Missing value | report_date | CRITICAL |
| 12 | Missing value | transaction_amount | CRITICAL |
| 18 | Missing value | entity_id | CRITICAL |
| 5 | Threshold breach | transaction_amount = 2,500,000 | CRITICAL |
| 15 | Threshold breach | risk_score = 105 | CRITICAL |
| 25 | Threshold breach | data_completeness = -5 | CRITICAL |
| 9 | Anomaly (outlier) | transaction_amount = 9,800,000 | WARNING |
| 20 | Anomaly (outlier) | risk_score = 0.01 | WARNING |
| 30 | Anomaly (outlier) | data_completeness = 0.5 | WARNING |
| 22 | Cross-field | status=flagged, reviewer_id=null | CRITICAL |
| 35 | Cross-field | status=flagged, reviewer_id=null | CRITICAL |

All other rows (30 of them) are clean valid records.

---

## Config File: `config.yaml`

```yaml
required_fields:
  - entity_id
  - report_date
  - risk_score
  - transaction_amount
  - status
  - reviewer_id
  - data_completeness

thresholds:
  risk_score:
    min: 0
    max: 100
  transaction_amount:
    min: 0
    max: 1000000
  data_completeness:
    min: 0
    max: 100

anomaly_detection:
  method: zscore
  zscore_threshold: 3
  fields:
    - transaction_amount
    - risk_score
    - data_completeness

cross_field_rules:
  - description: "Flagged records must have a reviewer assigned"
    if_field: status
    if_value: "flagged"
    then_field: reviewer_id
    then_condition: not_null

escalation:
  critical_threshold: 1
  notify_label: "COMPLIANCE ESCALATION REQUIRED"
```

---

## Module Specifications

### `logger.py`

- Creates a logger named `ValidationAgent`
- Logs to both console and a file `output/validation.log`
- Log format: `[TIMESTAMP] [LEVEL] message`
- Exposes a function `escalate(message)` that logs at CRITICAL level with the escalation label from config
- Used by all other modules

### `agent/rules/missing_value.py`

- Function: `check_missing_values(df, required_fields) -> list[dict]`
- Iterates over each row in the dataframe
- For each required field, checks if value is null/NaN/empty string
- Returns a list of findings, each as:
```python
{
    "row": int,           # 1-based row number
    "entity_id": str,     # entity_id of that row if available, else "UNKNOWN"
    "rule": "MISSING_VALUE",
    "field": str,         # which field is missing
    "value": None,
    "severity": "CRITICAL",
    "message": "Required field 'risk_score' is missing"
}
```

### `agent/rules/threshold.py`

- Function: `check_thresholds(df, thresholds) -> list[dict]`
- For each field defined in thresholds config, checks if value is below min or above max
- Skips null values (already caught by missing value check)
- Returns findings in same dict format as above
- severity is always "CRITICAL"
- rule is "THRESHOLD_VIOLATION"
- message explains the breach e.g. "risk_score value 105.0 exceeds maximum threshold of 100"

### `agent/rules/anomaly.py`

- Function: `check_anomalies(df, anomaly_config) -> list[dict]`
- Uses Z-score method by default (from config)
- For each field in anomaly_config fields list:
  - Compute Z-score across all non-null values in that column
  - Flag rows where |zscore| > threshold (default 3.0)
- severity is "WARNING"
- rule is "ANOMALY_DETECTED"
- message includes the field, value, and computed z-score e.g. "transaction_amount value 9800000.0 is anomalous (z-score: 4.82)"
- Returns findings in same dict format

### `agent/rules/cross_field.py`

- Function: `check_cross_fields(df, cross_field_rules) -> list[dict]`
- Iterates over rules defined in config
- For the rule: if status == "flagged" then reviewer_id must not be null
- Checks each row where the if_field matches if_value
- If then_field fails then_condition, it's a violation
- severity is "CRITICAL"
- rule is "CROSS_FIELD_VIOLATION"
- message e.g. "Record is 'flagged' but reviewer_id is missing — escalation required"

### `agent/validator.py`

- Class: `DataValidator`
- `__init__(self, config_path)`: loads config.yaml using PyYAML
- `validate(self, df) -> dict`: runs all 4 rule modules in sequence, collects all findings
- Returns a validation summary dict:
```python
{
    "total_records": int,
    "total_findings": int,
    "critical_count": int,
    "warning_count": int,
    "pass_count": int,           # records with zero findings
    "escalation_required": bool,
    "findings": list[dict],      # all findings combined
    "timestamp": str             # ISO format datetime
}
```
- After running, calls logger to log summary stats
- If escalation_required is True, calls `escalate()` from logger

### `report/report_generator.py`

- Function: `generate_report(summary: dict, output_path: str)`
- Loads `report/template.html` using Jinja2
- Passes summary dict to template
- Groups findings by severity for display
- Groups findings by row number so each record shows all its issues together
- Writes rendered HTML to `output/validation_report.html`
- Logs the output path on completion

### `report/template.html`

A clean, professional HTML report. Must include:

1. **Header section:**
   - Title: "Data Validation Agent — Compliance Report"
   - Timestamp of validation run
   - Agent name and version

2. **Summary cards (4 cards in a row):**
   - Total Records Validated
   - Total Findings
   - Critical Issues
   - Warnings

3. **Escalation banner (conditional):**
   - If escalation_required is True, show a prominent red banner: "⚠ COMPLIANCE ESCALATION REQUIRED — Critical validation failures detected"

4. **Findings table:**
   - Columns: Row, Entity ID, Rule, Field, Value, Severity, Message
   - Color-coded rows: red background for CRITICAL, yellow for WARNING
   - Sortable by severity

5. **Per-record breakdown section:**
   - Groups all findings by entity_id
   - Shows each entity with a list of all issues found

6. **Footer:**
   - "Generated by Data Validation Agent v1.0 | Neon AI Compliance Suite"

Style: Clean, modern, professional. Use internal CSS only (no external libraries). Dark header, white body, colored severity badges. Must look impressive when opened in a browser.

### `main.py`

```
1. Print banner: "Data Validation Agent v1.0 — Starting..."
2. Load dataset from data/sample_dataset.csv using pandas
3. Instantiate DataValidator with config.yaml
4. Run validator.validate(df)
5. Print summary to console (total records, findings, critical count, warnings)
6. Call generate_report() with summary
7. Print: "Validation complete. Report saved to output/validation_report.html"
```

### `README.md`

Must include:
1. Project overview (2-3 sentences)
2. Architecture diagram (text-based, ASCII)
3. Module descriptions (one paragraph each)
4. How to install dependencies
5. How to run (`python data/generate_dataset.py` then `python main.py`)
6. Sample output description
7. How to extend — adding new rules
8. Design decisions section explaining why modular rule engine was chosen

---

## Validation Result Severity Levels

| Severity | Color | Meaning |
|---|---|---|
| CRITICAL | Red | Regulatory violation — must be fixed before reporting |
| WARNING | Yellow | Anomalous but not a hard rule violation — review recommended |
| PASS | Green | No issues found for this record |

---

## Expected Output When Running

```
Data Validation Agent v1.0 — Starting...
Loading dataset: 40 records found
Running validation...
  [✓] Missing value check complete
  [✓] Threshold validation complete
  [✓] Anomaly detection complete
  [✓] Cross-field validation complete

========================================
VALIDATION SUMMARY
========================================
Total Records:     40
Total Findings:    12
Critical Issues:   9
Warnings:          3
Clean Records:     28
Escalation:        REQUIRED
========================================

[CRITICAL] COMPLIANCE ESCALATION REQUIRED
Report saved to: output/validation_report.html
```

---

## Important Notes for the Builder

- All modules must be importable independently
- No hardcoded values anywhere — everything comes from config.yaml
- The validation findings list must be consistent in structure across all 4 rule modules — same dict keys every time
- The report must open correctly in any modern browser with no external dependencies
- Code must have docstrings on every function and class
- The generate_dataset.py script must be idempotent — running it multiple times always produces the same dataset (use fixed random seed: 42)
