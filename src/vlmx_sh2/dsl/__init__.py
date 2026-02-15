"""
Language subsystem package.

This package groups everything that defines and compiles the VLMX-SH2 command
language:

    words (vocabulary) -> parser -> AST -> IR -> engine

Design goals:
- Keep AST and IR as pure, portable data contracts (easy to serialize; easy to
  mirror in Rust later).
- Keep runtime behavior (handlers, storage, UI) out of this package.
- Provide a clear public API surface for the rest of the application.

Current codebase note:
- The repo is in the middle of a migration from a former `dsl/` vocabulary
  package and scattered parser/AST/IR modules. This package is intended to
  become the stable home of the language frontend.

Re-exports:
- AST filter types (canonical): `vlmx_sh2.dsl.FilterExpression`, etc.
- IR command types (canonical): `vlmx_sh2.dsl.IRCommand`, etc.

Non-goals:
- No handler registration or engine dispatch wiring should live here.
"""

from __future__ import annotations

# AST (pure syntax trees)
from vlmx_sh2.dsl.ast.filters import (
    FilterCondition,
    FilterExpression,
    LogicalOperator,
    ValueExpression,
)

# IR (stable executable intent contract)
from vlmx_sh2.dsl.ir.command import (
    IRCommand,
    IRCommandOrigin,
    IRTargetKind,
    IRTargetRef,
)

__all__ = [
    # AST
    "FilterCondition",
    "FilterExpression",
    "LogicalOperator",
    "ValueExpression",
    # IR
    "IRCommand",
    "IRCommandOrigin",
    "IRTargetKind",
    "IRTargetRef",
]
