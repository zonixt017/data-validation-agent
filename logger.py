"""
logger.py — Structured logger for the Data Validation Agent.

Provides a named logger that writes to both console and file,
and exposes an escalate() function for CRITICAL compliance alerts.
"""

import logging
import os
import yaml

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

# Load config to get escalation label
def _load_escalation_label() -> str:
    """Load the escalation notify label from config.yaml."""
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config.get("escalation", {}).get("notify_label", "COMPLIANCE ESCALATION REQUIRED")
    except Exception:
        return "COMPLIANCE ESCALATION REQUIRED"


def get_logger() -> logging.Logger:
    """
    Create and return a structured logger named 'ValidationAgent'.

    Logs to both console (stdout) and output/validation.log.
    Format: [TIMESTAMP] [LEVEL] message
    """
    logger = logging.getLogger("ValidationAgent")

    # Avoid adding duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler("output/validation.log", mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Module-level logger instance
logger = get_logger()


def escalate(message: str) -> None:
    """
    Log a CRITICAL escalation alert with the compliance escalation label.

    Args:
        message: The escalation message to log.
    """
    label = _load_escalation_label()
    logger.critical(f"[{label}] {message}")
