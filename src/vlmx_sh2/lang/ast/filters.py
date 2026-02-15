"""
Filter AST models.

These are pure, serializable syntax tree structures produced by the filter parser
and consumed by later lowering/execution stages.

Design goals:
- Portable: keep as plain data that can be mirrored as Rust structs/enums.
- Stable: avoid embedding Python runtime objects (handlers, registries, model classes).
- Serializable: JSON-friendly shapes (strings, numbers, lists, dicts, enums).

Notes:
- This module intentionally contains no parsing logic.
- Source spans are not modeled yet; add them here later if you want precise diagnostics.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from vlmx_sh2.core.enums import Operator


class LogicalOperator(str, Enum):
    """Logical operators for combining filter conditions."""

    AND = "and"
    OR = "or"


class ValueExpression(BaseModel):
    """
    Recursive value expression tree for complex filter values.

    Can represent:
      1) Simple value: "product"
      2) Range value: 2022..2029 (modeled as range_start/range_end)
      3) Compound value: (product|team)&market (modeled as left/logic/right)

    Exactly one of these shapes should be set.
    """

    # Simple value
    simple: Optional[str] = Field(default=None, description="Simple string value")

    # Range value (start TO end)
    range_start: Optional[str] = Field(
        default=None,
        description="Range start value (None = open-ended ..end)",
    )
    range_end: Optional[str] = Field(
        default=None,
        description="Range end value (None = open-ended start..)",
    )

    # Compound value (left LOGIC right)
    left: Optional["ValueExpression"] = Field(
        default=None,
        description="Left side of logical value expression",
    )
    logic: Optional[LogicalOperator] = Field(
        default=None,
        description="Logical operator for value combination (OR/AND)",
    )
    right: Optional["ValueExpression"] = Field(
        default=None,
        description="Right side of logical value expression",
    )

    model_config = {"arbitrary_types_allowed": True}

    def __str__(self) -> str:
        """Human-readable string form (debugging/display)."""
        if self.simple is not None:
            return self.simple
        if self.range_start is not None or self.range_end is not None:
            start = self.range_start or ""
            end = self.range_end or ""
            return f"{start}..{end}"
        if self.left and self.logic and self.right:
            # Use | or & in the compact display form
            # (first letter of "or"/"and" matches existing behavior)
            return f"{self.left}{self.logic.value[0]}{self.right}"
        return "EmptyValue"

    @property
    def is_simple_value(self) -> bool:
        return self.simple is not None

    @property
    def is_range_value(self) -> bool:
        return self.range_start is not None or self.range_end is not None

    @property
    def is_compound_value(self) -> bool:
        return (
            self.left is not None and self.logic is not None and self.right is not None
        )

    def validate_structure(self) -> bool:
        """
        Validate that exactly one value shape is set.

        Returns:
            True if valid structure, False otherwise.
        """
        types_set = sum(
            [
                self.simple is not None,
                self.is_range_value,
                self.is_compound_value,
            ]
        )
        return types_set == 1


class FilterCondition(BaseModel):
    """
    Single filter condition: field operator value.

    Examples:
      - category=product
      - date<2024-01-01
      - similarity>=0.7
    """

    field: str = Field(description="Field name to filter on")
    operator: Operator = Field(description="Comparison operator")
    value: ValueExpression = Field(description="Value expression to compare against")

    def __str__(self) -> str:
        return f"{self.field}{self.operator.value}{self.value}"


class FilterExpression(BaseModel):
    """
    Recursive filter expression tree for complex filtering.

    Can represent:
      1) Single condition: condition
      2) Logical expression: left operator right
      3) Grouped expression: grouped

    Exactly one of these shapes should be set.
    """

    # Single condition
    condition: Optional[FilterCondition] = Field(
        default=None,
        description="Single filter condition",
    )

    # Logical expression (left operator right)
    left: Optional["FilterExpression"] = Field(
        default=None,
        description="Left side of logical expression",
    )
    operator: Optional[LogicalOperator] = Field(
        default=None,
        description="Logical operator (AND/OR)",
    )
    right: Optional["FilterExpression"] = Field(
        default=None,
        description="Right side of logical expression",
    )

    # Grouped expression
    grouped: Optional["FilterExpression"] = Field(
        default=None,
        description="Grouped (parenthesized) expression",
    )

    model_config = {"arbitrary_types_allowed": True}

    def __str__(self) -> str:
        if self.condition:
            return str(self.condition)
        if self.grouped:
            return f"({self.grouped})"
        if self.left and self.operator and self.right:
            return f"{self.left} {self.operator.value} {self.right}"
        return "EmptyFilter"

    @property
    def is_single_condition(self) -> bool:
        return self.condition is not None

    @property
    def is_logical_expression(self) -> bool:
        return (
            self.left is not None
            and self.operator is not None
            and self.right is not None
        )

    @property
    def is_grouped_expression(self) -> bool:
        return self.grouped is not None

    def validate_structure(self) -> bool:
        """
        Validate that exactly one expression shape is set.

        Returns:
            True if valid structure, False otherwise.
        """
        types_set = sum(
            [
                self.condition is not None,
                self.is_logical_expression,
                self.grouped is not None,
            ]
        )
        return types_set == 1


# Resolve forward references for recursive Pydantic models
ValueExpression.model_rebuild()
FilterExpression.model_rebuild()
