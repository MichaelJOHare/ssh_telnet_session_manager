from __future__ import annotations

from .types import (
    SelectionBack,
    SelectionExit,
    SelectionInvalid,
    SelectionOk,
    SelectionResult,
)


def prompt_text(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return ""


def prompt_yes_no(prompt: str, *, 
                  default: bool = False) -> bool:
    suffix = "(Y/n): " if default else "(y/N): "
    try:
        value = input(f"{prompt} {suffix}").strip()
    except EOFError:
        return False
    if value == "":
        return default
    return value.lower().startswith("y")


def prompt_selection(prompt: str, *,
                     max_value: int, allow_back: bool = False, 
                     allow_exit: bool = True) -> SelectionResult:
    try:
        sel = input(prompt).strip()
    except EOFError:
        return SelectionExit() if allow_exit else (SelectionBack() if allow_back else SelectionInvalid())

    # capture ctrl+z (EOF) as exit or back
    if sel == "\x1a":
        return SelectionExit() if allow_exit else (SelectionBack() if allow_back else SelectionInvalid())
    if allow_exit and sel.lower() == "e":
        return SelectionExit()
    if allow_back and sel.lower() == "b":
        return SelectionBack()
    if sel.isdigit():
        n = int(sel)
        if 1 <= n <= max_value:
            return SelectionOk(n)
    return SelectionInvalid()