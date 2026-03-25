"""
app/routes/config_editor.py — YAML config editor routes.

Routes:
    GET  /config        → Show config editor page
    POST /config/save   → Validate and save updated YAML, redirect back
    POST /config/reset  → Restore config.yaml to factory defaults
"""

import yaml
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"

# ---------------------------------------------------------------------------
# Factory default — this is always what "Reset to Defaults" restores.
# Never modify this constant. config.yaml may diverge but this stays fixed.
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_YAML = """\
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
"""


@router.get("/config", response_class=HTMLResponse)
async def config_editor(request: Request):
    saved = request.session.pop("config_saved", False)
    error = request.session.pop("config_error", None)

    with open(CONFIG_PATH) as f:
        config_yaml = f.read()

    return templates.TemplateResponse(
        request,
        "config_editor.html",
        {
            "config_yaml": config_yaml,
            "saved": saved,
            "error": error,
        },
    )


@router.post("/config/save")
async def config_save(request: Request, config_yaml: str = Form(...)):
    """Validate YAML syntax, write to disk, redirect with success flash."""
    try:
        parsed = yaml.safe_load(config_yaml)
        if not isinstance(parsed, dict):
            raise ValueError("Config must be a YAML mapping (dict).")
        with open(CONFIG_PATH, "w") as f:
            f.write(config_yaml)
        request.session["config_saved"] = True
    except Exception as exc:
        request.session["config_error"] = f"Invalid YAML: {exc}"

    return RedirectResponse("/config", status_code=303)


@router.post("/config/reset")
async def config_reset(request: Request):
    """Restore config.yaml to the factory default and redirect."""
    with open(CONFIG_PATH, "w") as f:
        f.write(DEFAULT_CONFIG_YAML)
    request.session["config_saved"] = True
    return RedirectResponse("/config", status_code=303)
