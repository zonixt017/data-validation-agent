"""
app/routes/ai.py — AI helper endpoints for explainability and Q&A.

Routes:
    POST /ai/explain  → Generate an AI summary for current validation run
    POST /ai/qa       → Ask a question about rules/findings for current run
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.ai_assistant import (
    generate_explainer,
    answer_rule_question,
    get_provider_status,
)
from app.state import RESULT_STORE, AI_RESPONSE_CACHE

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
async def ai_status():
    """Return current provider/status without exposing secrets."""
    return {"ok": True, "data": get_provider_status()}


@router.post("/explain")
async def explain_results(request: Request):
    result_id = request.session.get("result_id")
    result = RESULT_STORE.get(result_id) if result_id else None
    if not result:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "No validation result found in session."},
        )

    cache_key = f"explain:{result_id}:{result.get('run_at')}"
    if cache_key in AI_RESPONSE_CACHE:
        return {"ok": True, "cached": True, "data": AI_RESPONSE_CACHE[cache_key]}

    data = generate_explainer(result)
    AI_RESPONSE_CACHE[cache_key] = data
    return {"ok": True, "cached": False, "data": data}


@router.post("/qa")
async def qa_results(request: Request):
    result_id = request.session.get("result_id")
    result = RESULT_STORE.get(result_id) if result_id else None
    if not result:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "No validation result found in session."},
        )

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    question = (payload.get("question") or "").strip()
    if len(question) > 500:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Question is too long (max 500 chars)."},
        )

    cache_key = f"qa:{result_id}:{result.get('run_at')}:{question.lower()}"
    if cache_key in AI_RESPONSE_CACHE:
        return {"ok": True, "cached": True, "data": AI_RESPONSE_CACHE[cache_key]}

    data = answer_rule_question(result, question)
    AI_RESPONSE_CACHE[cache_key] = data
    return {"ok": True, "cached": False, "data": data}
