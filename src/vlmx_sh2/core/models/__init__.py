"""
Core Pydantic model definitions for VLMX-SH2.

This package is the canonical home for shared data models/DTOs used across
multiple layers (lang/parser, engine, storage, ui, diagnostics).

Structure (current):
- `words.py`         : word registry models (ActionWord, EntityWord, etc.)
- `validation/`      : validation models (ValidationContext, ValidationIssue, ValidationRule)
"""

from .validation import *  # noqa: F403
from .validation.context import ValidationContext  # noqa: F401
from .validation.issue import ValidationIssue  # noqa: F401
from .validation.rule import ValidationRule  # noqa: F401
from .words import *  # noqa: F403

# Re-export explicit names for a stable public surface.
# (Avoiding dynamic __all__ construction keeps things simple and clear.)
from .words import (  # noqa: F401
    ActionWord,
    EntityWord,
    FieldWord,
    ModuleWord,
    SchemaWord,
    TargetWord,
    ToolWord,
    ViewWord,
    Word,
    WordType,
)

__all__ = [
    # words
    "Word",
    "WordType",
    "ActionWord",
    "EntityWord",
    "FieldWord",
    "ModuleWord",
    "SchemaWord",
    "TargetWord",
    "ToolWord",
    "ViewWord",
    # validation
    "ValidationContext",
    "ValidationIssue",
    "ValidationRule",
]
