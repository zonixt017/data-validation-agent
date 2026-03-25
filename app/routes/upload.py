"""
app/routes/upload.py — Handles CSV/Excel file upload and validation orchestration.

Routes:
    GET  /               → Upload form (index.html)
    POST /upload         → Process uploaded file, store results in session
    POST /upload/sample  → Run validation on built-in sample data
"""

import os
import json
import tempfile
import uuid
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import yaml
from fastapi import APIRouter, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from agent.validator import DataValidator
from app.state import RESULT_STORE

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"
SAMPLE_DATA_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "sample_dataset.csv"
)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_default_config() -> dict:
    """Load the global config.yaml and return as dict."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _is_sample_dataset(df: pd.DataFrame) -> bool:
    """
    Return True if the DataFrame matches our synthetic sample dataset schema.
    Checks for the core compliance columns that the default config.yaml expects.
    """
    # Minimum required columns that identify this as our sample dataset
    sample_signature = {
        "entity_id", "report_date", "transaction_amount",
        "risk_score", "status", "reviewer_id", "data_completeness",
    }
    actual = {col.strip().lower() for col in df.columns}
    return sample_signature.issubset(actual)


def _auto_generate_config(df: pd.DataFrame) -> dict:
    """
    Build a sensible validation config automatically from the uploaded DataFrame.

    Rules applied:
    - required_fields  → every column in the dataset
    - thresholds       → every numeric column gets min/max derived from the data
                         (p1 and p99 percentiles, rounded to 2 dp)
    - anomaly_detection→ all numeric columns, z-score threshold 3.0
    - cross_field_rules→ empty (can't infer these automatically)
    - escalation       → same defaults as config.yaml
    """
    config = {
        "required_fields": list(df.columns),
        "thresholds": {},
        "anomaly_detection": {
            "method": "zscore",
            "zscore_threshold": 3.0,
            "fields": [],
        },
        "cross_field_rules": [],
        "escalation": {
            "critical_threshold": 1,
            "notify_label": "DATA QUALITY ALERT",
        },
    }

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue

        col_min = float(round(series.quantile(0.01), 2))
        col_max = float(round(series.quantile(0.99), 2))

        # Ensure min < max even for constant columns
        if col_min == col_max:
            col_min = float(round(series.min(), 2))
            col_max = float(round(series.max(), 2))
        if col_min == col_max:
            col_max = col_min + 1.0

        config["thresholds"][col] = {"min": col_min, "max": col_max}
        config["anomaly_detection"]["fields"].append(col)

    return config


# ---------------------------------------------------------------------------
# Core validation runner
# ---------------------------------------------------------------------------

def _run_validation(df: pd.DataFrame, filename: str, request: Request) -> None:
    """
    Choose the right config for this DataFrame, run DataValidator,
    and store the result in RESULT_STORE with a UUID key in the session.

    - If the file matches our sample dataset schema  → use config.yaml (default)
    - Otherwise                                      → auto-generate config
                                                       from the file's own columns
    """
    if _is_sample_dataset(df):
        config = _load_default_config()
        config_source = "default"
    else:
        config = _auto_generate_config(df)
        config_source = "auto"

    validator = DataValidator(config_dict=config)
    summary = validator.validate(df)

    serialisable_findings = json.loads(json.dumps(summary["findings"], default=str))

    findings_by_entity: dict[str, list] = {}
    for f in serialisable_findings:
        eid = f.get("entity_id", "UNKNOWN")
        findings_by_entity.setdefault(eid, []).append(f)

    pass_count = summary["pass_count"]
    total_records = summary["total_records"]

    result = {
        "filename": filename,
        "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_records": total_records,
        "total_findings": summary["total_findings"],
        "critical_count": summary["critical_count"],
        "warning_count": summary["warning_count"],
        "pass_count": pass_count,
        "pass_rate": (
            round(pass_count / total_records * 100, 1) if total_records else 0
        ),
        "escalation_required": summary["escalation_required"],
        "findings": serialisable_findings,
        "findings_by_entity": findings_by_entity,
        "config_source": config_source,   # "default" or "auto" — shown in UI
        "config_used": config,            # stored so results page can show it
    }

    result_id = str(uuid.uuid4())
    RESULT_STORE[result_id] = result
    request.session["result_id"] = result_id


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    error = request.session.pop("upload_error", None)
    return templates.TemplateResponse(request, "index.html", {"error": error})


@router.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Accept CSV or Excel uploads, run validation, redirect to results."""
    filename_lower = file.filename.lower()
    if not (
        filename_lower.endswith(".csv")
        or filename_lower.endswith(".xlsx")
        or filename_lower.endswith(".xls")
    ):
        request.session["upload_error"] = (
            "Unsupported file type. Please upload a CSV or Excel file (.csv, .xlsx, .xls)."
        )
        return RedirectResponse("/", status_code=303)

    tmp_path = None
    try:
        content = await file.read()

        # 10 MB guard
        if len(content) > 10 * 1024 * 1024:
            request.session["upload_error"] = (
                "File too large. Maximum allowed size is 10 MB."
            )
            return RedirectResponse("/", status_code=303)

        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Read into DataFrame
        if filename_lower.endswith(".csv"):
            df = pd.read_csv(tmp_path)
        else:
            df = pd.read_excel(tmp_path)

        if df.empty:
            request.session["upload_error"] = (
                "The uploaded file contains no data."
            )
            return RedirectResponse("/", status_code=303)

        _run_validation(df, file.filename, request)

    except Exception as exc:
        request.session["upload_error"] = f"Could not process file: {exc}"
        return RedirectResponse("/", status_code=303)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return RedirectResponse("/results", status_code=303)


@router.post("/upload/sample")
async def upload_sample(request: Request):
    """Run validation on the bundled sample dataset."""
    try:
        if SAMPLE_DATA_PATH.exists():
            df = pd.read_csv(SAMPLE_DATA_PATH)
            filename = "sample_dataset.csv"
        else:
            # Fallback: generate a minimal sample inline
            rng = np.random.default_rng(42)
            n = 40
            data = {
                "entity_id": [f"ENT-{i:04d}" for i in range(1, n + 1)],
                "report_date": (
                    pd.date_range("2025-01-01", periods=n, freq="D")
                    .strftime("%Y-%m-%d")
                    .tolist()
                ),
                "risk_score": rng.uniform(0, 100, n).round(1).tolist(),
                "transaction_amount": rng.uniform(100, 500_000, n).round(2).tolist(),
                "status": rng.choice(["clear", "flagged"], n).tolist(),
                "reviewer_id": [
                    f"REV-{rng.integers(1, 20):02d}" if rng.random() > 0.1 else None
                    for _ in range(n)
                ],
                "data_completeness": rng.uniform(70, 100, n).round(1).tolist(),
            }
            df = pd.DataFrame(data)
            df.loc[2, "risk_score"] = None
            df.loc[6, "report_date"] = None
            df.loc[4, "transaction_amount"] = 2_500_000.0
            df.loc[14, "risk_score"] = 105.0
            df.loc[21, "status"] = "flagged"
            df.loc[21, "reviewer_id"] = None
            filename = "sample_dataset_generated.csv"

        _run_validation(df, filename, request)

    except Exception as exc:
        request.session["upload_error"] = f"Sample validation error: {exc}"
        return RedirectResponse("/", status_code=303)

    return RedirectResponse("/results", status_code=303)
