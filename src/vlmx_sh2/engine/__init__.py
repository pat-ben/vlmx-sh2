"""
Engine package.

This package contains the execution layer of VLMX-SH2.

Responsibilities:
- Accept stable, serializable IR (`vlmx_sh2.dsl.ir.*`)
- Route IR commands to registered handlers
- Execute handlers safely and return UI-agnostic results/requests
- Provide a single entrypoint (`CommandExecutor`) for the UI layer

Notes:
- Handlers are registered via importing `vlmx_sh2.engine.handlers`.
  The application entrypoint should ensure that import happens once at startup.
- Legacy adaptation (IR -> ParsedCommand) exists only to support incremental
  handler refactors and should be removed once handlers are fully IR-native.
"""

from __future__ import annotations

from .executor import CommandExecutor
from .router import Router, register_action_handler

__all__ = [
    "CommandExecutor",
    "Router",
    "register_action_handler",
]
