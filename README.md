# Data Validation Agent

A rule-based compliance data validation agent built with Python. It validates
a 40-record synthetic dataset against configurable rules, produces a structured
console summary, and generates a polished HTML compliance report.

---

## Architecture

```
data_validation_agent/
│
├── config.yaml                    # All thresholds, rules, and escalation settings
├── logger.py                      # Structured dual-output logger + escalate()
├── main.py                        # Entry point — orchestrates full pipeline
├── requirements.txt               # Python dependencies
│
├── data/
│   └── generate_dataset.py        # Synthetic dataset generator (40 records, seed=42)
│
├── agent/
│   ├── validator.py               # DataValidator class — orchestrates all rules
│   └── rules/
│       ├── missing_value.py       # Rule 1: Missing required fields → CRITICAL
│       ├── threshold.py           # Rule 2: Min/max threshold breaches → CRITICAL
│       ├── anomaly.py             # Rule 3: Z-score outlier detection → WARNING
│       └── cross_field.py        # Rule 4: Conditional field constraints → CRITICAL
│
├── report/
│   ├── template.html              # Jinja2 HTML report template
│   └── report_generator.py        # Renders template → output/report.html
│
└── output/                        # (created at runtime)
    ├── report.html
    └── validation.log
```

### Pipeline Flow

```
main.py
  │
  ├─→ Load CSV (data/sample_dataset.csv)
  │
  ├─→ DataValidator.validate(df)
  │     ├─→ check_missing_values()    → CRITICAL findings
  │     ├─→ check_thresholds()        → CRITICAL findings
  │     ├─→ check_anomalies()         → WARNING findings
  │     └─→ check_cross_fields()      → CRITICAL findings
  │
  ├─→ summary dict ─→ Console output (structured table)
  │
  ├─→ generate_report(summary) ─→ output/report.html
  │
  └─→ output/validation.log
```

---

## Quick Start

**Prerequisites:** Python ≥ 3.11

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate the synthetic dataset

```bash
python data/generate_dataset.py
```

This creates `data/sample_dataset.csv` with 40 records and 12 injected flaws.

### 3. Run the validation pipeline

```bash
python main.py
```

### 4. View the report

Open `output/report.html` in any browser.

---

## Validation Rules

| # | Module | Rule | Severity |
|---|--------|------|----------|
| 1 | `missing_value.py` | Required fields must not be null/empty | **CRITICAL** |
| 2 | `threshold.py` | Numeric fields must be within min/max bounds | **CRITICAL** |
| 3 | `anomaly.py` | Z-score outlier detection on numeric fields | WARNING |
| 4 | `cross_field.py` | Conditional constraints between fields | **CRITICAL** |

---

## Configuration (`config.yaml`)

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

## Expected Output

Running against the generated dataset produces **12 total findings**:

| Category | Count | Severity |
|----------|-------|----------|
| Missing values | 4 | CRITICAL |
| Threshold violations | 3 | CRITICAL |
| Cross-field violations | 2 | CRITICAL |
| Anomalies detected | 3 | WARNING |
| **Total** | **12** | — |

---

## Output Files

```
output/
├── report.html       # Interactive HTML compliance report
└── validation.log    # Timestamped log of the full run
```

---

## Findings Format

Each finding is a Python dict with the following keys:

```python
{
    "row":       int,    # 1-based row number in the dataset
    "entity_id": str,    # Entity identifier (or "UNKNOWN")
    "rule":      str,    # Rule name, e.g. "MISSING_VALUE"
    "field":     str,    # The offending field name
    "value":     any,    # The actual value (None if missing)
    "severity":  str,    # "CRITICAL" or "WARNING"
    "message":   str,    # Human-readable description
}
```

---

## Project Spec

See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full technical specification
and [`TASKS.md`](TASKS.md) for the implementation task breakdown.
