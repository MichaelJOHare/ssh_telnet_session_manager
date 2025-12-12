from __future__ import annotations

from .types import (
    SelectionBack,
    SelectionExit,
    SelectionInvalid,
    SelectionOk,
    SelectionResult,
)


def prompt_text(prompt: str) -> str:
    return input(prompt)


def prompt_yes_no(prompt: str, *, default: bool = False) -> bool:
    suffix = "(Y/n): " if default else "(y/N): "
    value = input(f"{prompt} {suffix}").strip()
    if value == "":
        return default
    return value.lower().startswith("y")


def prompt_selection(
    prompt: str,
    *,
    max_value: int,
    allow_back: bool = False,
    allow_exit: bool = True,
) -> SelectionResult:
    sel = input(prompt).strip()
    if allow_exit and sel.lower() == "e":
        return SelectionExit()
    if allow_back and sel.lower() == "b":
        return SelectionBack()
    if sel.isdigit():
        n = int(sel)
        if 1 <= n <= max_value:
            return SelectionOk(n)
    return SelectionInvalid()