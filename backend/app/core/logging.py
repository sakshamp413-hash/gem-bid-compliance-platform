"""
PII-redacting logging.

A logging Filter scrubs Indian identifiers (PAN, GSTIN, CIN, Udyam No, Aadhaar,
email, phone) from every log record so sensitive data never lands in logs.
"""
from __future__ import annotations

import logging
import re
import sys

# --- PII patterns (Indian identifiers) ---
_PATTERNS: list[tuple[str, str]] = [
    # PAN: 5 letters + 4 digits + 1 letter
    (r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "[REDACTED_PAN]"),
    # GSTIN: 15 chars starting with 2-digit state + PAN + 3 chars
    (r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]{3}\b", "[REDACTED_GSTIN]"),
    # Udyam: UDYAM-XX-XX-XXXXXXX
    (r"\bUDYAM-[A-Z]{2}-\d{2}-\d{7}\b", "[REDACTED_UDYAM]"),
    # CIN: 21 chars
    (r"\b[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b", "[REDACTED_CIN]"),
    # Aadhaar-ish 12 digits
    (r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b", "[REDACTED_AADHAAR]"),
    # Email
    (r"\b[\w.+-]+@[\w-]+\.[\w.]+\b", "[REDACTED_EMAIL]"),
    # Phone (10-13 digits)
    (r"\b(?:\+91[- ]?)?[6-9]\d{9}\b", "[REDACTED_PHONE]"),
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = re.sub(pattern, repl, text)
    return text


class PIIRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if record.args:
                record.args = tuple(redact(str(a)) if isinstance(a, str) else a for a in record.args)
        except Exception:  # never break logging
            pass
        return True


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler.addFilter(PIIRedactionFilter())
    root.addHandler(handler)
    logging.getLogger("uvicorn.access").addFilter(PIIRedactionFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)