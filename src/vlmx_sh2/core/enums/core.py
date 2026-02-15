"""
Core (non-UI) enums.

This module is intended for shared, foundational enums that describe system-level
concepts and are used across multiple layers (engine, lang, storage, ui).

Guidelines:
- Put *user-facing* domain/value enums in `forms.py` (e.g., Currency, Country).
- Put parsing-structure enums in `parser.py` (e.g., TokenType, Operator).
- Put validation pipeline enums in `validation.py` (e.g., IssueStage, IssueSeverity).
- Put execution/runtime system concepts here.
"""

from enum import Enum


class ContextLevel(int, Enum):
    """
    Context level within the shell.

    Levels represent how much context is currently "selected" by the user:
    - SYS: no organization selected (system/root)
    - ORG: organization selected
    - APP: app/module selected within organization (deepest context)

    Note:
        This is an `int` Enum because some code may compare numeric levels or
        serialize them as numbers. Keep values stable.
    """

    SYS = 0
    ORG = 1
    APP = 2


class Cardinality(str, Enum):
    """
    Cardinality classification for entities/records.

    Used primarily by schemas and handlers to determine whether an entity is
    expected to have a single record or multiple records.
    """

    SINGLE = "single"
    MULTIPLE = "multiple"
