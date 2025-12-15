from __future__ import annotations

from .types import NormalizeResult


# takes raw group or nickname string and trims whitespace, enforces alphanumeric, adjusts case
def normalize_identifier(raw: str, *, 
                         case_mode: str = "lower", allow_empty: bool = False) -> NormalizeResult:
    trimmed = "".join((raw or "").split())

    if trimmed == "":
        if allow_empty:
            return NormalizeResult(ok=True, value="")
        return NormalizeResult(ok=False, error="empty")

    if not trimmed.isalnum():
        return NormalizeResult(ok=False, error="non_alnum")

    if case_mode == "upper":
        return NormalizeResult(ok=True, value=trimmed.upper())
    if case_mode == "lower":
        return NormalizeResult(ok=True, value=trimmed.lower())
    return NormalizeResult(ok=True, value=trimmed)
