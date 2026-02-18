"""
Handlers package.

This module wires engine action IDs to handler callables.

Architectural intent:
- The engine Router dispatches based on stable IR (`IRCommand.action_id`).
- Handlers accept `IRCommand` at the engine boundary (or adapt internally during migration).
- Registration happens here so importing `vlmx_sh2.engine.handlers` is enough to initialize
  the handler registry.

This keeps runtime behavior (handler functions) out of IR and preserves a clean:
    DSL -> parser -> AST -> IR -> engine
pipeline boundary.
"""

from __future__ import annotations

from vlmx_sh2.engine.router import register_action_handler

from .apps import apply_handler, run_handler
from .crud import (
    add_handler,
    create_handler,
    delete_handler,
    drop_handler,
    reset_handler,
    show_handler,
)
from .navigation import navigate_handler
from .wizard import fill_handler

# ---------------------------------------------------------------------------
# Action ID -> handler registrations
# ---------------------------------------------------------------------------
register_action_handler("create", create_handler)
register_action_handler("drop", drop_handler)
register_action_handler("add", add_handler)
register_action_handler("delete", delete_handler)
register_action_handler("reset", reset_handler)
register_action_handler("show", show_handler)
register_action_handler("cd", navigate_handler)

register_action_handler("fill", fill_handler)

register_action_handler("apply", apply_handler)
register_action_handler("run", run_handler)

__all__ = [
    # CRUD
    "create_handler",
    "drop_handler",
    "add_handler",
    "delete_handler",
    "reset_handler",
    "show_handler",
    # Navigation
    "navigate_handler",
    # Wizard
    "fill_handler",
    # Apps
    "apply_handler",
    "run_handler",
]
