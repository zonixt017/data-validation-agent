"""
app/services/ai_assistant.py — AI helper functions for explainability features.

Supports provider-configured LLM calls for:
- OpenRouter
- Groq

Falls back to deterministic local responses when provider is disabled,
API keys are missing, or remote calls fail.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from typing import Any
from urllib import request as urlrequest


PROVIDER_DEFAULT_MODELS = {
    "openrouter": "openrouter/auto",
    "groq": "llama-3.1-8b-instant",
}


def get_provider_status() -> dict:
    """Return active provider config status (safe for UI/API)."""
    provider = (os.environ.get("LLM_PROVIDER") or "none").strip().lower()
    if provider not in {"openrouter", "groq"}:
        return {
            "provider": "none",
            "enabled": False,
            "model": None,
            "reason": "LLM_PROVIDER not configured for openrouter/groq",
        }

    api_key = _provider_api_key(provider)
    model = (os.environ.get("LLM_MODEL") or PROVIDER_DEFAULT_MODELS[provider]).strip()

    return {
        "provider": provider,
        "enabled": bool(api_key),
        "model": model,
        "reason": None if api_key else f"Missing API key for provider '{provider}'",
    }


def _provider_api_key(provider: str) -> str | None:
    """Resolve API key based on provider."""
    if provider == "openrouter":
        return os.environ.get("OPENROUTER_API_KEY")
    if provider == "groq":
        return os.environ.get("GROQ_API_KEY")
    return None


def _provider_endpoint(provider: str) -> str | None:
    """Resolve chat completions endpoint for provider."""
    if provider == "openrouter":
        return "https://openrouter.ai/api/v1/chat/completions"
    if provider == "groq":
        return "https://api.groq.com/openai/v1/chat/completions"
    return None


def _safe_value(value: Any) -> str:
    """Return a short, non-sensitive string representation for prompts/UI."""
    if value is None:
        return "—"
    text = str(value)
    if len(text) > 80:
        return text[:77] + "..."
    return text


def _compress_findings(findings: list[dict], limit: int = 80) -> list[dict]:
    """Limit and sanitize findings before sending to a model."""
    out = []
    for f in findings[:limit]:
        out.append(
            {
                "row": f.get("row"),
                "rule": f.get("rule"),
                "field": f.get("field"),
                "severity": f.get("severity"),
                "message": f.get("message"),
                "entity_id": _safe_value(f.get("entity_id")),
                "value": _safe_value(f.get("value")),
            }
        )
    return out


def _build_context(result: dict) -> dict:
    """Build compact grounded context from stored validation output."""
    findings = result.get("findings", [])
    by_rule = Counter(f.get("rule", "UNKNOWN") for f in findings)
    by_field = Counter(f.get("field", "UNKNOWN") for f in findings)

    return {
        "filename": result.get("filename"),
        "run_at": result.get("run_at"),
        "summary": {
            "total_records": result.get("total_records", 0),
            "total_findings": result.get("total_findings", 0),
            "critical_count": result.get("critical_count", 0),
            "warning_count": result.get("warning_count", 0),
            "pass_count": result.get("pass_count", 0),
            "pass_rate": result.get("pass_rate", 0),
            "escalation_required": result.get("escalation_required", False),
        },
        "top_rules": by_rule.most_common(5),
        "top_fields": by_field.most_common(5),
        "sample_findings": _compress_findings(findings, limit=80),
        "config_source": result.get("config_source"),
    }


def _hash_payload(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _call_configured_llm(system_prompt: str, user_prompt: str, temperature: float = 0.1) -> tuple[str, dict] | None:
    """
    Call configured LLM provider and return (provider_name, parsed_json).

    Returns None when provider is disabled, key missing, or call fails.
    """
    status = get_provider_status()
    provider = status["provider"]
    if provider == "none" or not status["enabled"]:
        return None

    api_key = _provider_api_key(provider)
    endpoint = _provider_endpoint(provider)
    model = status["model"]
    if not (api_key and endpoint and model):
        return None

    payload = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if provider == "openrouter":
        site_url = os.environ.get("OPENROUTER_SITE_URL", "https://render.com")
        app_name = os.environ.get("OPENROUTER_APP_NAME", "data-validation-agent")
        headers["HTTP-Referer"] = site_url
        headers["X-Title"] = app_name

    req = urlrequest.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return provider, json.loads(content)
    except Exception:
        return None


def generate_explainer(result: dict) -> dict:
    """Create AI explainer content for a validation result."""
    context = _build_context(result)

    system_prompt = (
        "You are a compliance data quality assistant. "
        "Use only provided context. Return strict JSON with keys: "
        "summary_text (string), top_issues (array of strings), "
        "actions (array of strings), confidence_notes (array of strings)."
    )
    user_prompt = (
        "Generate an executive explanation for this validation run. "
        "Focus on severity, recurring patterns, and practical remediation steps.\n\n"
        f"Context JSON:\n{json.dumps(context, ensure_ascii=False)}"
    )

    model_out = _call_configured_llm(system_prompt, user_prompt, temperature=0.1)
    if model_out:
        provider, payload = model_out
        return {
            "provider": provider,
            "summary_text": payload.get("summary_text", "No summary generated."),
            "top_issues": payload.get("top_issues", []),
            "actions": payload.get("actions", []),
            "confidence_notes": payload.get("confidence_notes", []),
            "context_hash": _hash_payload(context),
        }

    # Deterministic fallback
    summary = context["summary"]
    top_rules = [f"{name}: {count}" for name, count in context["top_rules"][:3]]
    top_fields = [f"{name}: {count}" for name, count in context["top_fields"][:3]]
    provider_state = get_provider_status()

    return {
        "provider": "local-fallback",
        "summary_text": (
            f"Run analyzed {summary['total_records']} record(s) with "
            f"{summary['total_findings']} finding(s): "
            f"{summary['critical_count']} critical and {summary['warning_count']} warning. "
            f"Escalation is {'required' if summary['escalation_required'] else 'not required'}."
        ),
        "top_issues": [
            "Most frequent rules: " + (", ".join(top_rules) if top_rules else "none"),
            "Most affected fields: " + (", ".join(top_fields) if top_fields else "none"),
            "Critical issues should be triaged before warning-level anomalies.",
        ],
        "actions": [
            "Fix missing required fields first for affected rows.",
            "Resolve threshold violations by verifying source-system constraints.",
            "Review warning anomalies after all critical findings are addressed.",
        ],
        "confidence_notes": [
            "Response generated from deterministic result context.",
            (
                "LLM provider disabled or unavailable. "
                f"Provider status: {provider_state['provider']}"
            ),
        ],
        "context_hash": _hash_payload(context),
    }


def answer_rule_question(result: dict, question: str) -> dict:
    """Answer rule-related Q&A grounded on result context only."""
    question = (question or "").strip()
    if not question:
        return {
            "provider": "local-fallback",
            "answer": "Please enter a question about rules or findings.",
            "bullets": [],
            "confidence_notes": ["No question provided."],
        }

    context = _build_context(result)
    system_prompt = (
        "You are a rule-based compliance assistant. "
        "Use only provided context and avoid fabricating dataset details. "
        "Return strict JSON with keys: answer (string), bullets (array of strings), "
        "confidence_notes (array of strings)."
    )
    user_prompt = (
        f"Question: {question}\n\n"
        "Answer using only this context JSON:\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )

    model_out = _call_configured_llm(system_prompt, user_prompt, temperature=0.0)
    if model_out:
        provider, payload = model_out
        return {
            "provider": provider,
            "answer": payload.get("answer", "No answer generated."),
            "bullets": payload.get("bullets", []),
            "confidence_notes": payload.get("confidence_notes", []),
            "context_hash": _hash_payload({"q": question, "ctx": context}),
        }

    # Deterministic fallback Q&A
    summary = context["summary"]
    top_rules = context["top_rules"]
    provider_state = get_provider_status()
    answer = (
        "This validator runs deterministic rule checks (missing values, thresholds, "
        "anomaly detection, cross-field checks) and aggregates findings by severity."
    )

    bullets = [
        f"Current run: {summary['total_findings']} findings ({summary['critical_count']} critical, {summary['warning_count']} warning).",
        f"Pass count shown: {summary['pass_count']} of {summary['total_records']}.",
    ]
    if top_rules:
        bullets.append(
            "Most frequent rules in this run: "
            + ", ".join(f"{name} ({count})" for name, count in top_rules[:3])
        )

    return {
        "provider": "local-fallback",
        "answer": answer,
        "bullets": bullets,
        "confidence_notes": [
            "Fallback answer uses local run context only.",
            (
                "LLM provider disabled or unavailable. "
                f"Provider status: {provider_state['provider']}"
            ),
        ],
        "context_hash": _hash_payload({"q": question, "ctx": context}),
    }
