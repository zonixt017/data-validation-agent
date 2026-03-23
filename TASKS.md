# Data Validation Agent — Build Tasks

## Instructions for the AI Agent

Read `PROJECT_SPEC.md` in full before starting. Every file you build must match the specifications in that document exactly — field names, function signatures, return formats, severity levels, and report structure. Do not make assumptions — if something is specified, follow it precisely.

Build everything in the order listed below. Do not skip steps. After completing all tasks, run the project end-to-end and confirm it works.

---

## Task List

### TASK 1 — Project Structure
Create the following empty files and folders exactly:
```
data_validation_agent/
├── data/
│   └── generate_dataset.py
├── agent/
│   ├── __init__.py
│   └── rules/
│       ├── __init__.py
│       ├── missing_value.py
│       ├── threshold.py
│       ├── anomaly.py
│       └── cross_field.py
│       └── validator.py
├── report/
│   ├── report_generator.py
│   └── template.html
├── output/
├── logger.py
├── config.yaml
├── main.py
└── README.md
```

---

### TASK 2 — config.yaml
Create `config.yaml` exactly as specified in the PROJECT_SPEC.md under "Config File" section. This file drives all validation rules — no values should be hardcoded anywhere else.

---

### TASK 3 — logger.py
Build the structured logger as specified. It must:
- Log to both console AND `output/validation.log`
- Format: `[TIMESTAMP] [LEVEL] message`
- Expose an `escalate(message)` function
- Use the escalation label from config

---

### TASK 4 — data/generate_dataset.py
Build the dataset generator exactly as specified:
- 40 records total
- All fields as defined in the dataset spec
- Inject all 12 flaws at exactly the rows specified
- Fixed random seed of 42 for reproducibility
- Saves to `data/sample_dataset.csv`
- Run this script first before anything else

---

### TASK 5 — agent/rules/missing_value.py
Build `check_missing_values(df, required_fields) -> list[dict]` exactly as specified. Return format must match the findings dict structure in PROJECT_SPEC.md precisely.

---

### TASK 6 — agent/rules/threshold.py
Build `check_thresholds(df, thresholds) -> list[dict]` exactly as specified. Skip nulls. Severity always CRITICAL.

---

### TASK 7 — agent/rules/anomaly.py
Build `check_anomalies(df, anomaly_config) -> list[dict]` using Z-score method. Include the computed z-score value in the message. Severity always WARNING.

---

### TASK 8 — agent/rules/cross_field.py
Build `check_cross_fields(df, cross_field_rules) -> list[dict]` as specified. Must work generically from the config rules — not hardcoded for just one rule.

---

### TASK 9 — agent/validator.py
Build the `DataValidator` class as specified:
- Loads config in `__init__`
- `validate(df)` runs all 4 rule modules in order
- Returns the full summary dict with all fields specified
- Triggers escalation via logger if critical findings exist

---

### TASK 10 — report/template.html
Build the full HTML report template using Jinja2 syntax:
- All 6 sections as specified (header, summary cards, escalation banner, findings table, per-record breakdown, footer)
- Internal CSS only — no external libraries
- Color-coded severity rows (red = CRITICAL, yellow = WARNING, green = PASS)
- Professional appearance — this will be reviewed by a technical founder
- Must render correctly in Chrome/Firefox with no errors

---

### TASK 11 — report/report_generator.py
Build `generate_report(summary, output_path)` as specified:
- Loads template.html via Jinja2
- Groups findings by severity and by row
- Writes to `output/validation_report.html`

---

### TASK 12 — main.py
Build the entry point as specified:
- Prints banner
- Loads dataset
- Runs validator
- Prints summary to console in the exact format shown in PROJECT_SPEC.md
- Generates report
- Prints completion message

---

### TASK 13 — README.md
Write a thorough README as specified:
- Project overview
- ASCII architecture diagram
- Module descriptions
- Install and run instructions
- How to extend with new rules
- Design decisions

---

### TASK 14 — End-to-End Verification
After all files are built:
1. Run `pip install pandas numpy scipy PyYAML jinja2`
2. Run `python data/generate_dataset.py` — confirm CSV is created with 40 rows
3. Run `python main.py` — confirm console output matches expected format in PROJECT_SPEC.md
4. Open `output/validation_report.html` in a browser — confirm all sections render correctly
5. Fix any import errors, path issues, or runtime exceptions before finishing

---

## Definition of Done

- All 14 tasks completed
- `python main.py` runs without errors
- Console output shows correct counts (12 findings, 9 critical, 3 warnings)
- `output/validation_report.html` opens in browser and looks professional
- All functions have docstrings
- No hardcoded values — everything from config.yaml
