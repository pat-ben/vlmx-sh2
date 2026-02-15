"""
Lowering from parser/wizard inputs into stable IR.

This is the "Intermediate Layer" boundary:
- Inputs: parser outputs (tokens + AST) and wizard submissions
- Output: IRCommand (stable, serializable contract)

Key design constraints:
- IR must not embed runtime objects (no handler functions, no model classes, no DSL word objects).
- Lowering is allowed to *consult* the DSL registry to map words to stable IDs and kinds,
  but the produced IR must contain only plain data.

Current codebase context:
- Parser stages 0-6 produce TokensResult, which includes:
  - command_tokens: List[InterpretedToken]
  - filter_expression: Optional[FilterExpression]  (filter AST)
- Wizard flows currently build "ParsedCommand" directly; this module provides IR lowering
  so wizard submissions can bypass parser internals.

This module intentionally avoids importing engine/router/handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from vlmx_sh2.lang.ast.filters import FilterExpression
from vlmx_sh2.lang.ir.command import (
    IRCommand,
    IRCommandOrigin,
    IRTargetKind,
    IRTargetRef,
)

# We can consult the word registry for ID/kind mapping, but we must not return those objects.
from vlmx_sh2.lang.words.registry import get_word
from vlmx_sh2.models.words import (
    ActionWord,
    EntityWord,
    FieldWord,
    ModuleWord,
    SchemaWord,
    ToolWord,
    ViewWord,
    WordType,
)

if TYPE_CHECKING:
    from vlmx_sh2.models.parser.interpretation import InterpretedToken
    from vlmx_sh2.models.parser.tokens_result import TokensResult


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def lower_from_tokens_result(
    tokens_result: "TokensResult",
    *,
    raw_input: Optional[str] = None,
    annotations: Optional[Dict[str, Any]] = None,
) -> Optional[IRCommand]:
    """
    Lower a parser TokensResult (stages 0-6 output) into stable IRCommand.

    Returns:
        IRCommand if an action word can be identified, else None.

    Notes:
    - This performs the old "CommandBuilder stage 7" responsibilities, but produces IR.
    - It uses interpreted tokens to identify action/target/name/assignments/field_names.
    - It carries over filter_expression as-is (AST).
    """
    command_tokens: List["InterpretedToken"] = list(tokens_result.command_tokens or [])
    filter_expression: Optional[FilterExpression] = tokens_result.filter_expression

    # Action is required for an IRCommand
    action_id = _extract_action_id(command_tokens)
    if not action_id:
        return None

    target_ref = _extract_target_ref(command_tokens)

    target_name = _extract_target_name(command_tokens)
    if target_name:
        # Attach name to target ref (even if id is None, keep it for navigation-ish commands)
        target_ref = target_ref.model_copy(update={"name": target_name})

    assignments = _extract_field_assignments(command_tokens)
    field_names = _extract_standalone_field_names(command_tokens)

    return IRCommand(
        action_id=action_id,
        target=target_ref,
        assignments=assignments,
        field_names=field_names,
        filters=filter_expression,
        raw_input=raw_input if raw_input is not None else tokens_result.input_text,
        origin=IRCommandOrigin.TEXT,
        annotations=annotations or {},
    )


def lower_from_wizard(
    *,
    action_id: str,
    entity_id: str,
    entity_name: Optional[str],
    field_values: Dict[str, Any],
    record_id: Optional[str] = None,
    raw_input: Optional[str] = None,
    annotations: Optional[Dict[str, Any]] = None,
) -> Optional[IRCommand]:
    """
    Lower wizard submission data into IRCommand.

    This is intentionally stringly-typed at the IR boundary: values become strings.
    """
    # Validate action exists and is an action word in the DSL registry
    action_word = get_word(action_id)
    if not action_word or not isinstance(action_word, ActionWord):
        return None

    target_word = get_word(entity_id)
    if not target_word or not isinstance(
        target_word, (SchemaWord, EntityWord, ModuleWord, ViewWord, ToolWord, FieldWord)
    ):
        return None

    target_kind = _word_to_target_kind(target_word)
    target_ref = IRTargetRef(kind=target_kind, id=target_word.id, name=entity_name)

    # Convert to string assignments
    assignments: Dict[str, str] = {
        key: "" if value is None else str(value)
        for key, value in (field_values or {}).items()
    }

    # Preserve record id as an annotation (do not sneak engine-specific magic into assignments)
    merged_annotations = dict(annotations or {})
    if record_id is not None:
        merged_annotations["record_id"] = str(record_id)

    # Build a helpful raw_input if not provided
    if raw_input is None:
        parts = [action_id, entity_id]
        if entity_name:
            parts.append(f'"{entity_name}"')
        parts.extend([f"{k}={v}" for k, v in assignments.items()])
        raw_input = "[WIZARD] " + " ".join(parts)

    return IRCommand(
        action_id=action_word.id,
        target=target_ref,
        assignments=assignments,
        field_names=[],
        filters=None,
        raw_input=raw_input,
        origin=IRCommandOrigin.WIZARD,
        annotations=merged_annotations,
    )


# -----------------------------------------------------------------------------
# Lowering helpers (token -> IR fields)
# -----------------------------------------------------------------------------


def _extract_action_id(tokens: List["InterpretedToken"]) -> Optional[str]:
    """
    Find the action word from interpreted tokens and return its stable ID.
    """
    action_token = next(
        (t for t in tokens if getattr(t, "is_action_word", False)), None
    )
    if not action_token:
        return None

    word = getattr(action_token, "word", None)
    if isinstance(word, ActionWord):
        return word.id

    # Fallback: if token text looks like an action, still return text (keeps IR stable-ish)
    text = getattr(action_token, "text", None)
    return str(text) if text else None


def _extract_target_ref(tokens: List["InterpretedToken"]) -> IRTargetRef:
    """
    Extract the first non-field TargetWord (schema/entity/module/view/tool/field) as IRTargetRef.

    If no target is present, returns kind=NONE.
    """
    target_token = next(
        (
            t
            for t in tokens
            if getattr(t, "word", None)
            and isinstance(
                getattr(t, "word", None),
                (SchemaWord, ModuleWord, EntityWord, FieldWord, ViewWord, ToolWord),
            )
            # exclude field words when they are part of assignments; we still allow explicit field target for commands like
            # 'delete brand vision' where 'brand' is entity target and 'vision' is a field name, not the target.
        ),
        None,
    )

    if not target_token:
        return IRTargetRef(kind=IRTargetKind.NONE, id=None, name=None)

    w = target_token.word
    kind = _word_to_target_kind(w)
    return IRTargetRef(kind=kind, id=w.id, name=None)


def _extract_target_name(tokens: List["InterpretedToken"]) -> Optional[str]:
    """
    Extract a target instance name from the token stream.

    Existing behavior (CommandBuilder) used the first VALUE or UNKNOWN token.
    We'll keep that behavior for compatibility.
    """
    name_token = next(
        (
            t
            for t in tokens
            if getattr(t, "is_value", False) or getattr(t, "is_unknown", False)
        ),
        None,
    )
    text = getattr(name_token, "text", None) if name_token else None
    return str(text) if text else None


def _extract_field_assignments(tokens: List["InterpretedToken"]) -> Dict[str, str]:
    """
    Extract field=value assignments from interpreted tokens.

    Mirrors previous CommandBuilder behavior:
      field_token (field word) + operator_token (structural) + value_token (value)
    """
    assignments: Dict[str, str] = {}
    i = 0
    while i < len(tokens) - 2:
        field_token = tokens[i]
        op_token = tokens[i + 1]
        value_token = tokens[i + 2]

        if (
            getattr(field_token, "is_field_word", False)
            and getattr(op_token, "is_structural_token", False)
            and getattr(op_token, "operator", None) is not None
            and getattr(value_token, "is_value", False)
        ):
            field_name = str(getattr(field_token, "text", ""))
            value_text = str(getattr(value_token, "text", ""))
            if field_name:
                assignments[field_name] = value_text
            i += 3
            continue

        i += 1

    return assignments


def _extract_standalone_field_names(tokens: List["InterpretedToken"]) -> List[str]:
    """
    Extract standalone field names that are NOT part of a field=value assignment.

    This supports commands like:
      delete brand vision mission
      show organization name legal

    Implementation strategy:
    - Walk tokens; collect field words
    - Skip any field word that begins an assignment triplet field op value
    """
    field_names: List[str] = []

    i = 0
    while i < len(tokens):
        t = tokens[i]

        # Skip assignment triplets
        if (
            i < len(tokens) - 2
            and getattr(tokens[i], "is_field_word", False)
            and getattr(tokens[i + 1], "is_structural_token", False)
            and getattr(tokens[i + 1], "operator", None) is not None
            and getattr(tokens[i + 2], "is_value", False)
        ):
            i += 3
            continue

        if getattr(t, "is_field_word", False):
            name = str(getattr(t, "text", ""))
            if name:
                field_names.append(name)

        i += 1

    # De-dup while preserving order
    seen = set()
    unique: List[str] = []
    for n in field_names:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique


def _word_to_target_kind(word: Any) -> IRTargetKind:
    """
    Map DSL word object -> stable IRTargetKind.

    IMPORTANT: IR must not embed DSL word objects; we only use them here to map kind.
    """
    # Prefer WordType where available
    wt = getattr(word, "word_type", None)
    if wt == WordType.SCHEMA:
        return IRTargetKind.SCHEMA
    if wt == WordType.MODULE:
        return IRTargetKind.MODULE
    if wt == WordType.ENTITY:
        return IRTargetKind.ENTITY
    if wt == WordType.FIELD:
        return IRTargetKind.FIELD
    if wt == WordType.VIEW:
        return IRTargetKind.VIEW
    if wt == WordType.TOOL:
        return IRTargetKind.TOOL

    # Fallback by instance type
    if isinstance(word, SchemaWord):
        return IRTargetKind.SCHEMA
    if isinstance(word, ModuleWord):
        return IRTargetKind.MODULE
    if isinstance(word, EntityWord):
        return IRTargetKind.ENTITY
    if isinstance(word, FieldWord):
        return IRTargetKind.FIELD
    if isinstance(word, ViewWord):
        return IRTargetKind.VIEW
    if isinstance(word, ToolWord):
        return IRTargetKind.TOOL

    return IRTargetKind.NONE
