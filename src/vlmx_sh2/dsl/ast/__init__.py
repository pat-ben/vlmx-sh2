"""
AST package.

This package contains pure, serializable syntax tree data structures produced by
parsers and consumed by later compilation/lowering stages.

Design goals:
- No runtime behavior (no handler functions, no registries).
- Keep structures portable to non-Python implementations (e.g., Rust).
- Keep this layer independent from engine concerns.
"""

from .filters import FilterCondition, FilterExpression, LogicalOperator, ValueExpression

__all__ = [
    "FilterCondition",
    "FilterExpression",
    "LogicalOperator",
    "ValueExpression",
]
