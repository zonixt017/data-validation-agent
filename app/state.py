# app/state.py

# Global store for results to avoid session cookie size limits
RESULT_STORE: dict = {}

# Lightweight in-memory cache for AI responses, keyed by result_id + prompt hash.
# This avoids repeated model calls for identical requests in one server process.
AI_RESPONSE_CACHE: dict = {}
