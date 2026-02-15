"""
Engine adapter: IR -> legacy ParsedCommand (runtime objects) for existing handlers.

This module exists to support an incremental migration to a clean architecture:

    DSL -> parser -> AST -> IR -> engine

Target end-state:
- The engine (router/handlers/storage) should accept ONLY IR.
- Handlers should not depend on DSL runtime objects (ActionWord/TargetWord) or model classes.

Current reality:
- Existing handlers expect `ParsedCommand` with `ActionWord`/`TargetWord` objects and
  convenience properties like `target_model` and `entity_model`.

So this adapter bridges:
- Input: `IRCommand` (stable, serializable)
- Output: `ParsedCommand` (legacy runtime-rich object)

IMPORTANT:
- This adapter is an ENGINE-INTERNAL concern. It MUST NOT leak back into IR types.
- Keep all "registry lookups" and runtime object resolution here.
- Over time, handlers should be refactored to consume IR directly, and this adapter removed.
"""

from __future__ import annotations

from typing import Optional

from vlmx_sh2.lang.ir.command import IRCommand, IRTargetKind
from vlmx_sh2.lang.words.registry import get_word
from vlmx_sh2.models.parser.command import ParsedCommand
from vlmx_sh2.models.words import (
    ActionWord,
    EntityWord,
    FieldWord,
    ModuleWord,
    SchemaWord,
    TargetWord,
    ToolWord,
    ViewWord,
)

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def to_legacy_parsed_command(ir: IRCommand) -> ParsedCommand:
    """
    Convert stable IR into the legacy ParsedCommand expected by existing handlers.

    Resolution rules:
    - `action_id` is resolved via DSL registry -> ActionWord (required)
    - `target.id` is resolved via DSL registry -> TargetWord (optional)
    - `target.name` is mapped to ParsedCommand.target_name
    - `assignments` is mapped to ParsedCommand.field_values
    - `field_names` is mapped to ParsedCommand.field_names
    - `filters` is passed through (FilterExpression AST is already pure data)

    Raises:
        ValueError: if action_id cannot be resolved to an ActionWord.
    """
    action_word = _resolve_action_word(ir.action_id)
    target_word = _resolve_target_word(ir.target.id, ir.target.kind)

    return ParsedCommand(
        action=action_word,
        target=target_word,
        target_name=ir.target.name,
        field_values=dict(ir.assignments or {}),
        field_names=list(ir.field_names or []),
        filters=ir.filters,
        raw_input=ir.raw_input,
        # Legacy field: keep empty; token-level fidelity belongs to parser layer, not IR.
        command_tokens=[],
        # Legacy field: keep empty; filter token fidelity belongs to parser layer, not IR.
        filter_tokens=[],
    )


# -----------------------------------------------------------------------------
# Resolution helpers
# -----------------------------------------------------------------------------


def _resolve_action_word(action_id: str) -> ActionWord:
    """
    Resolve action_id -> ActionWord via DSL registry.

    This is intentionally strict: without a valid action, the engine cannot dispatch.
    """
    w = get_word(action_id)
    if not isinstance(w, ActionWord):
        raise ValueError(f"Unknown or invalid action_id '{action_id}'")
    return w


def _resolve_target_word(
    target_id: Optional[str], target_kind: IRTargetKind
) -> Optional[TargetWord]:
    """
    Resolve target_id -> TargetWord via DSL registry.

    Returns None if:
    - target_kind is NONE, or
    - target_id is missing/empty, or
    - registry lookup fails or does not match expected target kind.

    Notes:
    - We *do not* attempt fuzzy matching here; keep resolution deterministic.
    - `target_kind` is used as a guardrail, but we also accept correct instances even
      if kind mismatches to avoid over-breaking during migration.
    """
    if target_kind == IRTargetKind.NONE:
        return None
    if not target_id:
        return None

    w = get_word(target_id)
    if w is None:
        return None

    # Exact type acceptance
    if isinstance(
        w, (SchemaWord, ModuleWord, EntityWord, FieldWord, ViewWord, ToolWord)
    ):
        # Optionally enforce kind match if provided
        if _matches_kind(w, target_kind):
            return w
        # Migration-friendly: still return it if it's a valid TargetWord
        return w

    return None


def _matches_kind(word: TargetWord, kind: IRTargetKind) -> bool:
    """
    Check whether a resolved DSL word matches the IRTargetKind.
    """
    if kind == IRTargetKind.SCHEMA:
        return isinstance(word, SchemaWord)
    if kind == IRTargetKind.MODULE:
        return isinstance(word, ModuleWord)
    if kind == IRTargetKind.ENTITY:
        return isinstance(word, EntityWord)
    if kind == IRTargetKind.FIELD:
        return isinstance(word, FieldWord)
    if kind == IRTargetKind.VIEW:
        return isinstance(word, ViewWord)
    if kind == IRTargetKind.TOOL:
        return isinstance(word, ToolWord)
    if kind == IRTargetKind.NONE:
        return False
    return False
