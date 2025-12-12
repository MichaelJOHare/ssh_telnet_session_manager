"""Python command line menu for ssh/telnet connections.

You can add hosts to ~/.ssh/config and ~/.telnet/config as well as connect to them.
"""

from __future__ import annotations

from .types import (
	Choice,
	HostEntry,
	NormalizeResult,
	PromptCancel,
	PromptInvalid,
	PromptOk,
	PromptResult,
	SelectionBack,
	SelectionExit,
	SelectionInvalid,
	SelectionOk,
	SelectionResult,
	Transport,
	TransportConfig,
)

__all__ = [
	"Choice",
	"HostEntry",
	"NormalizeResult",
	"PromptCancel",
	"PromptInvalid",
	"PromptOk",
	"PromptResult",
	"SelectionBack",
	"SelectionExit",
	"SelectionInvalid",
	"SelectionOk",
	"SelectionResult",
	"Transport",
	"TransportConfig",
]
