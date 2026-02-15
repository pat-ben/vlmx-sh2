"""
IR (Intermediate Representation) package.

This package defines the *stable, serializable* contracts that form the ONLY
interface into the engine layer.

Architecture target:
    DSL -> parser -> AST -> IR -> engine

Key principles:
- Stable: IR should change slowly and intentionally.
- Serializable: IR must be JSON-friendly (and later easy to mirror in Rust).
- No runtime objects: IR must not embed Python callables, classes, or registry objects.
  (e.g., no ActionWord/EntityWord instances, no handler functions, no model classes)
- Engine boundary: the engine should accept IR types only, never parser tokens.

Practical implications for this codebase:
- Parser stages may emit tokens + AST (e.g., filter AST).
- A lowering step converts parser outputs (and wizard submissions) into IR.
- The router/handlers/storage should depend on IR, not on parser models.

This design is intended to make a future Rust port straightforward by mirroring
these structures as Rust structs/enums.
"""

from .command import IRCommand, IRCommandOrigin, IRTargetKind, IRTargetRef

__all__ = [
    "IRCommand",
    "IRCommandOrigin",
    "IRTargetKind",
    "IRTargetRef",
]
