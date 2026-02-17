"""Filter application for dynamic table filtering.

This module evaluates the *DSL filter AST* (`vlmx_sh2.dsl.ast.filters`) against
lists of plain dict records returned by storage backends.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from vlmx_sh2.core.enums import Operator
from vlmx_sh2.dsl.ast.filters import (
    FilterCondition,
    FilterExpression,
    LogicalOperator,
    ValueExpression,
)


class FilterApplicationError(Exception):
    """Raised when filter application fails."""


def apply_filters(
    records: list[dict[str, object]], filters: FilterExpression
) -> list[dict[str, object]]:
    """Apply filter expression to list of records."""
    if not records:
        return []

    try:
        return [record for record in records if _evaluate_expression(record, filters)]
    except FilterApplicationError:
        raise
    except Exception as e:
        raise FilterApplicationError(f"Filter application failed: {str(e)}")


def _evaluate_expression(record: dict[str, object], expr: FilterExpression) -> bool:
    """Evaluate a filter expression against a single record."""
    if expr.is_single_condition:
        if expr.condition is None:
            raise FilterApplicationError("Single condition expression has no condition")
        return _evaluate_condition(record, expr.condition)

    if expr.is_grouped_expression:
        if expr.grouped is None:
            raise FilterApplicationError("Grouped expression has no grouped content")
        return _evaluate_expression(record, expr.grouped)

    if expr.is_logical_expression:
        if expr.left is None or expr.right is None or expr.operator is None:
            raise FilterApplicationError("Logical expression missing operands/operator")

        left_result = _evaluate_expression(record, expr.left)
        right_result = _evaluate_expression(record, expr.right)

        return (
            (left_result and right_result)
            if expr.operator == LogicalOperator.AND
            else (left_result or right_result)
        )

    raise FilterApplicationError(f"Invalid expression structure: {expr}")


def _evaluate_condition(record: dict[str, object], condition: FilterCondition) -> bool:
    """Evaluate a single filter condition against a record."""
    record_value = record.get(condition.field)

    try:
        return _evaluate_value_expression(
            record_value, condition.operator, condition.value
        )
    except FilterApplicationError:
        raise
    except Exception as e:
        raise FilterApplicationError(
            f"Condition evaluation failed for {condition.field}: {str(e)}"
        )


def _evaluate_value_expression(
    record_value: object, operator: Operator, value_expr: ValueExpression
) -> bool:
    """Recursively evaluate a ValueExpression against a record value."""
    # Simple value
    if value_expr.is_simple_value:
        return _apply_operator(record_value, operator, value_expr.simple)

    # Range value
    if value_expr.is_range_value:
        result = True
        if value_expr.range_start is not None:
            result = result and _apply_operator(
                record_value, Operator.GREATER_EQUAL, value_expr.range_start
            )
        if value_expr.range_end is not None:
            result = result and _apply_operator(
                record_value, Operator.LESS_EQUAL, value_expr.range_end
            )
        return result

    # Compound value (left LOGIC right)
    if value_expr.is_compound_value:
        if (
            value_expr.left is None
            or value_expr.right is None
            or value_expr.logic is None
        ):
            raise FilterApplicationError(
                "Compound value expression missing operands/logic"
            )

        left_result = _evaluate_value_expression(
            record_value, operator, value_expr.left
        )
        right_result = _evaluate_value_expression(
            record_value, operator, value_expr.right
        )

        if value_expr.logic == LogicalOperator.OR:
            return left_result or right_result
        else:  # AND
            return left_result and right_result

    raise FilterApplicationError(f"Invalid value expression structure: {value_expr}")


def _apply_operator(
    record_value: object, operator: Operator, filter_value: object
) -> bool:
    """Apply operator comparison between record value and filter value."""
    # Handle None values
    if record_value is None:
        null_values = {None, "", "null"}
        return (filter_value in null_values) == (operator == Operator.EQUAL)

    # Normalize values for comparison
    record_val, filter_val = _normalize_values(record_value, filter_value)

    # Apply comparison using operator mapping.
    #
    # Type checkers don't allow ordering comparisons on `object`, but at runtime our
    # normalized values are intended to be comparable (numbers/bools/strings).
    ops: dict[Operator, Callable[[object, object], bool]] = {
        Operator.EQUAL: lambda r, f: r == f,
        Operator.NOT_EQUAL: lambda r, f: r != f,
        Operator.GREATER: lambda r, f: cast(Any, r) > cast(Any, f),
        Operator.LESS: lambda r, f: cast(Any, r) < cast(Any, f),
        Operator.GREATER_EQUAL: lambda r, f: cast(Any, r) >= cast(Any, f),
        Operator.LESS_EQUAL: lambda r, f: cast(Any, r) <= cast(Any, f),
    }

    if operator not in ops:
        raise FilterApplicationError(f"Unknown operator: {operator}")

    return bool(ops[operator](record_val, filter_val))


def _normalize_values(
    record_value: object, filter_value: object
) -> tuple[object, object]:
    """Normalize values for comparison by attempting type coercion."""
    record_str = str(record_value) if record_value is not None else ""
    filter_str = str(filter_value) if filter_value is not None else ""

    # Try numeric conversion
    for val_str in (record_str, filter_str):
        if not val_str:
            continue
        try:
            record_num = int(record_str) if "." not in record_str else float(record_str)
            filter_num = int(filter_str) if "." not in filter_str else float(filter_str)
            return record_num, filter_num
        except ValueError:
            continue

    # Try boolean conversion
    bool_map: dict[str, bool] = {
        "true": True,
        "yes": True,
        "1": True,
        "on": True,
        "false": False,
        "no": False,
        "0": False,
        "off": False,
    }

    record_bool = bool_map.get(record_str.lower())
    filter_bool = bool_map.get(filter_str.lower())

    if record_bool is not None and filter_bool is not None:
        return record_bool, filter_bool

    # Fall back to case-insensitive string comparison
    return record_str.lower(), filter_str.lower()


def get_filter_fields(filters: FilterExpression) -> list[str]:
    """Extract all field names referenced in a filter expression."""
    fields: set[str] = set()

    def extract(expr: FilterExpression) -> None:
        if expr.is_single_condition and expr.condition:
            fields.add(expr.condition.field)
        elif expr.is_grouped_expression and expr.grouped:
            extract(expr.grouped)
        elif expr.is_logical_expression:
            if expr.left:
                extract(expr.left)
            if expr.right:
                extract(expr.right)

    extract(filters)
    return sorted(fields)
