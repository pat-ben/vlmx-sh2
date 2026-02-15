"""
Stable, serializable Intermediate Representation (IR) for commands.

This module defines the ONLY contract the engine layer should accept.

Design goals:
- Stable: change slowly and intentionally.
- Serializable: JSON-friendly; easy to mirror as Rust structs/enums.
- No runtime objects: do NOT embed Python callables, classes, or registry objects.
  (e.g., no ActionWord/EntityWord instances, no handler functions, no model classes)
- Engine-facing: engine should depend on these types only, not on parser tokens.

Notes:
- Filters are represented as AST from `vlmx_sh2.dsl.ast.filters` (pure data).
- This IR does not attempt to preserve full token-level fidelity; that stays in
  parser outputs and diagnostics. IR is the normalized, executable intent.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from vlmx_sh2.core.models.parser.filtering import FilterExpression


class IRCommandOrigin(str, Enum):
    """Where the IR command came from."""

    TEXT = "text"
    WIZARD = "wizard"
    OTHER = "other"


class IRTargetKind(str, Enum):
    """
    Kind of target referenced by a command.

    Keep this small and stable. This corresponds to your DSL word categories,
    but importantly: IR carries only *IDs* and *kind*, not registry objects.
    """

    SCHEMA = "schema"
    MODULE = "module"
    ENTITY = "entity"
    FIELD = "field"
    VIEW = "view"
    TOOL = "tool"
    NONE = "none"  # for commands that truly have no target (e.g., navigation)


class IRTargetRef(BaseModel):
    """
    Reference to a command target.

    Examples:
      - create company ACME -> kind=schema, id="company", name="ACME"
      - add brand vision=... -> kind=entity, id="brand"
      - apply neco -> kind=view, id="neco"
    """

    kind: IRTargetKind = Field(description="Target kind")
    id: Optional[str] = Field(
        default=None,
        description="Stable target identifier (e.g., 'company', 'brand', 'neco'). None if kind=NONE.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Optional target instance name (e.g., company name 'ACME').",
    )

    model_config = {"extra": "forbid"}

    @property
    def is_none(self) -> bool:
        return self.kind == IRTargetKind.NONE


class IRCommand(BaseModel):
    """
    Stable, serializable command IR.

    Fields are intentionally plain:
      - action_id/target are stable identifiers
      - assignments/field_names are basic collections
      - filters is an AST (pure data) that can be lowered further if desired

    This model should be easy to:
      - unit test (construct directly)
      - serialize to JSON
      - port to Rust
    """

    # Core intent
    action_id: str = Field(
        description="Action identifier (e.g., 'create', 'add', 'show', 'delete', 'fill')."
    )
    target: IRTargetRef = Field(
        default_factory=lambda: IRTargetRef(kind=IRTargetKind.NONE),
        description="Target reference (kind/id/name).",
    )

    # Data payload
    assignments: Dict[str, str] = Field(
        default_factory=dict,
        description="Field=value assignments (stringly-typed at IR boundary).",
    )
    field_names: List[str] = Field(
        default_factory=list,
        description="Standalone field names (e.g., 'delete brand vision mission').",
    )

    # Filtering (AST)
    filters: Optional[FilterExpression] = Field(
        default=None,
        description="Optional filter AST (pure data) for list/show/delete-row operations.",
    )

    # Metadata (kept minimal but useful)
    raw_input: str = Field(
        description="Original raw input string (for logs/diagnostics)."
    )
    origin: IRCommandOrigin = Field(
        default=IRCommandOrigin.TEXT, description="Origin of the command."
    )
    annotations: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Optional extra metadata. Keep engine logic independent of this field. "
            "Useful for tracing, experiments, and transitional migration."
        ),
    )

    model_config = {"extra": "forbid"}

    # ----------------------------
    # Convenience helpers (pure)
    # ----------------------------

    @property
    def target_id(self) -> Optional[str]:
        return self.target.id

    @property
    def target_name(self) -> Optional[str]:
        return self.target.name

    @property
    def has_target(self) -> bool:
        return not self.target.is_none and bool(self.target.id)

    @property
    def has_assignments(self) -> bool:
        return bool(self.assignments)

    @property
    def has_filters(self) -> bool:
        return self.filters is not None
