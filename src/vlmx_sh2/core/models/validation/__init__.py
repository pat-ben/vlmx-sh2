"""
Validation models package.

Exports core validation DTOs used throughout the parsing/diagnostics pipeline.

Canonical imports:
    from vlmx_sh2.core.models.validation import (
        ValidationContext,
        ValidationIssue,
        ValidationRule,
    )
"""

from .context import ValidationContext
from .issue import ValidationIssue
from .rule import ValidationRule

__all__ = [
    "ValidationContext",
    "ValidationIssue",
    "ValidationRule",
]
