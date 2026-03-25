# Data Validation Agent

> Agent 3 of the Neon AI Compliance Monitoring Suite

A rule-based compliance data validation platform built in Python. Upload any CSV dataset via the web UI and get instant validation against configurable regulatory rules — with an interactive dashboard and a one-click PDF compliance report.

**v0.2** adds a full FastAPI web layer on top of the existing rule engine. No CLI required.

---

## What It Does

The agent runs four independent validation checks against any structured dataset:

| # | Rule | Severity |
|---|------|----------|
| 1 | **Missing value detection** — required fields must not be null or empty | `CRITICAL` |
| 2 | **Threshold validation** — numeric fields must be within regulatory min/max bounds | `CRITICAL` |
| 3 | **Anomaly detection** — Z-score outlier detection on numeric fields | `WARNING` |
| 4 | **Cross-field validation** — conditional constraints between related fields | `CRITICAL` |

If any `CRITICAL` finding is detected, a **compliance escalation** is automatically triggered and logged.

---

## Architecture

```
data_validation_agent/
│
├── config.yaml                    # All thresholds, required fields, escalation rules
├── logger.py                      # Structured dual-output logger + escalate()
├── main.py                        # CLI entry point (v0.1 — still functional)
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Production container image
├── render.yaml                    # Render.com deploy config
│
├── app/                           # ★ v0.2 Web Layer
│   ├── main.py                    # FastAPI app with session middleware
│   ├── routes/
│   │   ├── upload.py              # GET / + POST /upload + POST /upload/sample
│   │   ├── results.py             # GET /results + GET /results/download (PDF)
│   │   └── config_editor.py       # GET /config + POST /config/save
│   └── templates/
│       ├── base.html              # Nav, Tailwind CDN, footer
│       ├── index.html             # Drag-and-drop upload form
│       ├── results.html           # Dashboard with findings table + entity breakdown
│       └── config_editor.html     # YAML textarea editor
│
├── static/css/custom.css          # Drop-zone transitions, sticky table header
│
├── data/
│   └── generate_dataset.py        # Synthetic dataset generator (40 records, seed=42)
│
├── agent/
│   ├── validator.py               # DataValidator — accepts config_path or config_dict
│   └── rules/
│       ├── missing_value.py       # Rule 1: Missing required fields
│       ├── threshold.py           # Rule 2: Out-of-bounds numeric values
│       ├── anomaly.py             # Rule 3: Z-score statistical outlier detection
│       └── cross_field.py         # Rule 4: Conditional field constraints
│
├── report/
│   ├── pdf_template.html          # WeasyPrint A4 PDF template
│   └── report_generator.py        # CLI HTML report generator (v0.1)
│
└── output/                        # Generated at runtime
    └── uploads/                   # Temp upload staging
```

### Pipeline Flow

```
main.py
  │
  ├─→ Existence check + load CSV via pandas
  │
  ├─→ DataValidator(config.yaml).validate(df)
  │     ├─→ check_missing_values()     →  CRITICAL findings
  │     ├─→ check_thresholds()         →  CRITICAL findings
  │     ├─→ check_anomalies()          →  WARNING findings
  │     └─→ check_cross_fields()       →  CRITICAL findings
  │
  ├─→ Console: structured summary table + full findings detail
  │
  ├─→ logger.escalate() if critical findings exist
  │
  ├─→ generate_report(summary) → output/report.html
  │
  └─→ output/validation.log
```

---

## Quick Start

**Prerequisites:** Python ≥ 3.11

### 1. Clone the repository

```bash
git clone https://github.com/zonixt017/data-validation-agent.git
cd data-validation-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** WeasyPrint (PDF generation) requires system libraries on some platforms:
> - **Ubuntu/Debian:** `apt-get install libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libcairo2`
> - **macOS (Homebrew):** `brew install pango cairo gdk-pixbuf`
> - **Windows:** Use WSL2 or run via Docker (see below).

### 3. Start the web UI

```bash
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. (Optional) Generate the sample dataset for CLI use

```bash
python data/generate_dataset.py
```

### 5. (Optional) CLI pipeline — v0.1 still works

```bash
python main.py
```

Produces `output/report.html`.

---

## Running with Docker

```bash
docker build -t data-validation-agent .
docker run -p 8000:8000 -e SESSION_SECRET_KEY=your-secret data-validation-agent
```

Open [http://localhost:8000](http://localhost:8000).

---

## Deploy to Render

1. Push the repository to GitHub.
2. In [Render Dashboard](https://render.com) → **New Web Service** → connect your repo.
3. Render will detect `render.yaml` and deploy automatically.
4. A `SESSION_SECRET_KEY` is auto-generated by Render via the `generateValue: true` setting.

---

## Sample Console Output

```
════════════════════════════════════════════════════════════
  DATA VALIDATION AGENT — Compliance Pipeline
  Neon AI | Data Validation Suite v1.0
════════════════════════════════════════════════════════════

  Dataset loaded: 40 records

Running validation checks …
  [✓] Missing value check complete
  [✓] Threshold validation complete
  [✓] Anomaly detection complete
  [✓] Cross-field validation complete

────────────────────────────────────────────────────────────
VALIDATION SUMMARY
────────────────────────────────────────────────────────────
  Total Records Validated : 40
  ✓ Records Passed        : 29
  ✗ Total Findings        : 15
  ● Critical Issues       : 12
  ▲ Warnings              : 3
────────────────────────────────────────────────────────────
  ⚠  COMPLIANCE ESCALATION REQUIRED
────────────────────────────────────────────────────────────
```

---

## Configuration

All validation rules live in `config.yaml` — nothing is hardcoded. Edit this file to adapt the agent to any dataset or regulatory context.

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

## Findings Format

Every finding across all four rule modules returns a consistent dict structure:

```python
{
    "row":       int,    # 1-based row number in the dataset
    "entity_id": str,    # Entity identifier (or "UNKNOWN" if missing)
    "rule":      str,    # "MISSING_VALUE" | "THRESHOLD_VIOLATION" |
                         # "ANOMALY_DETECTED" | "CROSS_FIELD_VIOLATION"
    "field":     str,    # The offending field name
    "value":     any,    # The actual value (None if missing)
    "severity":  str,    # "CRITICAL" or "WARNING"
    "message":   str,    # Human-readable description of the issue
}
```

---

## Sample Dataset — Injected Flaws

The generated dataset contains 40 records with 12 deliberate flaws for demonstration:

| Row | Flaw Type | Field | Severity |
|-----|-----------|-------|----------|
| 3 | Missing value | `risk_score` | CRITICAL |
| 7 | Missing value | `report_date` | CRITICAL |
| 12 | Missing value | `transaction_amount` | CRITICAL |
| 18 | Missing value | `entity_id` | CRITICAL |
| 5 | Threshold breach | `transaction_amount` = 2,500,000 | CRITICAL |
| 15 | Threshold breach | `risk_score` = 105 | CRITICAL |
| 25 | Threshold breach | `data_completeness` = -5 | CRITICAL |
| 9 | Anomaly (outlier) | `transaction_amount` = 9,800,000 | WARNING |
| 20 | Anomaly (outlier) | `risk_score` = 0.01 | WARNING |
| 30 | Anomaly (outlier) | `data_completeness` = 0.5 | WARNING |
| 22 | Cross-field | `status`=flagged, `reviewer_id`=null | CRITICAL |
| 35 | Cross-field | `status`=flagged, `reviewer_id`=null | CRITICAL |

> Note: Rows 9 and 25 produce both a threshold violation and an anomaly finding — both rules fire independently, which is correct and expected behaviour.

---

## Extending the Agent

### Adding a new validation rule

1. Create `agent/rules/your_rule.py` with a function:
```python
def check_your_rule(df, config) -> list[dict]:
    findings = []
    # your logic here
    # return findings in the standard dict format above
    return findings
```

2. Import and call it in `agent/validator.py` inside the `validate()` method.

3. Add any config it needs to `config.yaml`.

That's it — no changes needed anywhere else.

---

## Design Decisions

**Why a modular rule engine?**
Each rule is fully independent — it takes a dataframe and config, returns findings. Rules don't know about each other. This means you can add, remove, or modify any rule without touching the others.

**Why config-driven?**
Zero hardcoded thresholds or field names. The same agent adapts to any dataset by editing `config.yaml`. This is how real compliance tools work.

**Why consistent findings format?**
All four rule modules return the same dict structure. The report generator, logger, and console output don't need to know which rule produced a finding — they just process the list uniformly.

**Why Jinja2 for reports?**
The HTML report has no external dependencies — it opens in any browser with no internet connection required. Suitable for regulated environments where external CDN calls may be restricted.

---

## Roadmap

- `v0.1.0` — CLI pipeline with rule engine and HTML report ✅
- `v0.2.0` — Web UI with drag-and-drop upload, interactive results dashboard, PDF download, YAML config editor, Docker + Render deploy ✅
- `v0.3.0` — Validation history, user accounts, scheduled runs *(planned)*

---

## License

MIT — free to use, modify, and distribute.
