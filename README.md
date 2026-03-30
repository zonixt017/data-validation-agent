# Data Validation Agent

A rule-based compliance data validation platform built with Python and FastAPI. Upload any CSV dataset and get instant validation against configurable regulatory rules — with an interactive results dashboard and one-click PDF compliance report.

**Live Demo → [data-validation-agent.onrender.com](https://data-validation-agent.onrender.com)**

> ⚠️ Hosted on Render free tier — first load may take ~30 seconds to spin up.

---

## What It Does

The agent runs four independent validation checks against any structured dataset:

| # | Rule | Severity |
|---|------|----------|
| 1 | **Missing value detection** — required fields must not be null or empty | `CRITICAL` |
| 2 | **Threshold validation** — numeric fields must be within regulatory min/max bounds | `CRITICAL` |
| 3 | **Anomaly detection** — Z-score outlier detection on numeric fields | `WARNING` |
| 4 | **Cross-field validation** — conditional constraints between related fields | `CRITICAL` |

Any `CRITICAL` finding automatically triggers a **compliance escalation**, logged and surfaced in the UI.

---

## Stack

- **Backend:** Python 3.11, FastAPI, pandas, scipy
- **Frontend:** Jinja2 templates, Tailwind CSS
- **PDF Reports:** WeasyPrint
- **Config:** YAML-driven rule engine — no hardcoded thresholds
- **Deployment:** Docker, Render

---

## Architecture

```
data_validation_agent/
│
├── app/                        # FastAPI web layer
│   ├── main.py                 # App entry point, session middleware
│   ├── routes/
│   │   ├── upload.py           # CSV upload + sample dataset
│   │   ├── results.py          # Results dashboard + PDF download
│   │   └── config_editor.py    # Live YAML config editor
│   └── templates/              # Jinja2 HTML templates
│
├── agent/                      # Validation rule engine
│   ├── validator.py            # Orchestrates all rule modules
│   └── rules/
│       ├── missing_value.py
│       ├── threshold.py
│       ├── anomaly.py
│       └── cross_field.py
│
├── report/                     # PDF report generation
├── data/                       # Sample dataset generator
├── config.yaml                 # All rules, thresholds, escalation config
├── Dockerfile
└── render.yaml
```

### Pipeline

```
CSV Upload
    │
    └─→ DataValidator(config.yaml).validate(df)
          ├─→ check_missing_values()    →  CRITICAL findings
          ├─→ check_thresholds()        →  CRITICAL findings
          ├─→ check_anomalies()         →  WARNING findings
          └─→ check_cross_fields()      →  CRITICAL findings
                │
                ├─→ Results dashboard (pass rate, findings table, entity breakdown)
                ├─→ Compliance escalation if CRITICAL findings exist
                └─→ PDF report download
```

---

## Quick Start

**Prerequisites:** Python ≥ 3.11

```bash
git clone https://github.com/zonixt017/data-validation-agent.git
cd data-validation-agent
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000) — upload any CSV or use the built-in sample dataset.

> **WeasyPrint system deps (PDF generation):**
> - Ubuntu/Debian: `apt-get install libpango-1.0-0 libcairo2 libgdk-pixbuf-xlib-2.0-0`
> - macOS: `brew install pango cairo gdk-pixbuf`
> - Windows: Use Docker (see below)

---

## Docker

```bash
docker build -t data-validation-agent .
docker run -p 8000:8000 -e SESSION_SECRET_KEY=your-secret data-validation-agent
```

---

## AI Provider Setup (OpenRouter / Groq)

The AI Explainer and AI Rule Q&A features support provider-based setup using env vars.

### Supported providers
- `openrouter`
- `groq`
- fallback mode (`none`) when provider/key is missing

### Required environment variables
```bash
# choose provider: openrouter | groq
LLM_PROVIDER=openrouter

# provider model (optional; defaults are used if omitted)
LLM_MODEL=openrouter/auto

# keys (set only the one for your provider)
OPENROUTER_API_KEY=...
GROQ_API_KEY=...
```

Optional (OpenRouter headers):
```bash
OPENROUTER_SITE_URL=https://your-app-url.onrender.com
OPENROUTER_APP_NAME=data-validation-agent
```

### Render deployment notes
- Add these keys in **Render Dashboard → Environment**.
- Never commit API keys to GitHub.
- If provider is not configured, app automatically uses deterministic local fallback responses.

---

## Configuration

All validation rules live in `config.yaml` — nothing is hardcoded. Edit to adapt the agent to any dataset or regulatory context.

```yaml
required_fields:
  - entity_id
  - report_date
  - risk_score
  - transaction_amount

thresholds:
  risk_score:
    min: 0
    max: 100
  transaction_amount:
    min: 0
    max: 1000000

anomaly_detection:
  method: zscore
  zscore_threshold: 3
  fields:
    - transaction_amount
    - risk_score

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

## Extending the Agent

To add a new validation rule:

1. Create `agent/rules/your_rule.py` returning a list of finding dicts
2. Import and call it in `agent/validator.py`
3. Add any config it needs to `config.yaml`

All findings share a consistent format across every rule module:

```python
{
    "row":      int,   # 1-based row index
    "entity_id": str,  # Entity identifier
    "rule":     str,   # e.g. "MISSING_VALUE", "THRESHOLD_VIOLATION"
    "field":    str,   # Offending field name
    "value":    any,   # Actual value found
    "severity": str,   # "CRITICAL" or "WARNING"
    "message":  str,   # Human-readable description
}
```

---

## Releases

| Version | Description |
|---------|-------------|
| `v0.1.0` | CLI pipeline — rule engine, console output, HTML report |
| `v0.2.0` | FastAPI web UI, drag-and-drop upload, PDF download, YAML config editor, Docker + Render deployment |

---

## License

MIT
