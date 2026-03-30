"""
app/main.py — FastAPI application entry point for the Data Validation Agent web UI.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.routes import upload, results, config_editor, ai
from app.state import RESULT_STORE

app = FastAPI(
    title="Data Validation Agent",
    version="0.2.0",
    description="Rule-based compliance data validation web application",
)

# Server-side result store — avoids overflowing the 4 KB session cookie.
# Keys are short UUIDs; only the key is stored in the session cookie.
# RESULT_STORE: dict = {}

SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(upload.router)
app.include_router(results.router)
app.include_router(config_editor.router)
app.include_router(ai.router)


@app.on_event("startup")
async def startup():
    os.makedirs("output/uploads", exist_ok=True)
