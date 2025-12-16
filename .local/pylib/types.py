from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Literal, Protocol, TypeAlias, TypeVar


# ---- config-related types ----

@dataclass(frozen=True)
class Transport:
    key: str
    label: str
    config_file: Path


@dataclass(frozen=True)
class HostEntry:
    alias: str
    hostname: str
    port: str
    hostkey_algorithms: str = ""
    kex_algorithms: str = ""
    macs: str = ""


@dataclass(frozen=True)
class NormalizeResult:
    ok: bool
    value: str = ""
    error: str = ""


@dataclass(frozen=True)
class CategorizedHosts:
    main_hosts: list[str]
    group_map: dict[str, list[str]]
    group_names: list[str]


@dataclass
class MenuVars:
    main_hosts: list[str]
    group_map: dict[str, list[str]]
    group_names: list[str]
    labels: list[str]
    types: list[str]
    values: list[str]
    transport: Transport


# ---- menu callback types ----

class HostAction(Protocol):
    def __call__(self, host_label: str, transport: Transport, *, last_msg_out: list[str]) -> bool: ...


# ---- prompting / selection result types ----

T = TypeVar("T")


@dataclass(frozen=True)
class PromptOk(Generic[T]):
    value: T
    status: Literal["ok"] = "ok"


@dataclass(frozen=True)
class PromptInvalid:
    status: Literal["invalid"] = "invalid"


@dataclass(frozen=True)
class PromptCancel:
    status: Literal["cancel"] = "cancel"


PromptResult: TypeAlias = PromptOk[T] | PromptInvalid | PromptCancel


@dataclass(frozen=True)
class SelectionOk:
    value: int
    status: Literal["ok"] = "ok"


@dataclass(frozen=True)
class SelectionBack:
    status: Literal["back"] = "back"


@dataclass(frozen=True)
class SelectionExit:
    status: Literal["exit"] = "exit"


@dataclass(frozen=True)
class SelectionInvalid:
    status: Literal["invalid"] = "invalid"


SelectionResult: TypeAlias = SelectionOk | SelectionBack | SelectionExit | SelectionInvalid


@dataclass(frozen=True)
class Choice(Generic[T]):
    label: str
    value: T
    kind: str = ""  # e.g. 'host' or 'group'
