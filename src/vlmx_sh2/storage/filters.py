"""Filter application for dynamic table filtering."""

from typing import List, Dict, Any, Union
from ..core.models.parser.filtering import FilterExpression, FilterCondition, LogicalOperator, ValueExpression
from vlmx_sh2.core.enums import Operator


class FilterApplicationError(Exception):
    """Raised when filter application fails."""
    pass


def apply_filters(records: List[Dict[str, Any]], filters: FilterExpression) -> List[Dict[str, Any]]:
    """Apply filter expression to list of records."""
    if not records:
        return []
    
    try:
        return [record for record in records if _evaluate_expression(record, filters)]
    except Exception as e:
        raise FilterApplicationError(f"Filter application failed: {str(e)}")


def _evaluate_expression(record: Dict[str, Any], expr: FilterExpression) -> bool:
    """Evaluate a filter expression against a single record."""
    if expr.is_single_condition:
        if not expr.condition:
            raise FilterApplicationError("Single condition expression has no condition")
        return _evaluate_condition(record, expr.condition)
    
    if expr.is_grouped_expression:
        if not expr.grouped:
            raise FilterApplicationError("Grouped expression has no grouped content")
        return _evaluate_expression(record, expr.grouped)
    
    if expr.is_logical_expression:
        if not expr.left or not expr.right:
            raise FilterApplicationError("Logical expression missing operands")
        
        left_result = _evaluate_expression(record, expr.left)
        right_result = _evaluate_expression(record, expr.right)
        
        return (left_result and right_result) if expr.operator == LogicalOperator.AND else (left_result or right_result)
    
    raise FilterApplicationError(f"Invalid expression structure: {expr}")


def _evaluate_condition(record: Dict[str, Any], condition: FilterCondition) -> bool:
    """Evaluate a single filter condition against a record."""
    record_value = record.get(condition.field)
    
    try:
        return _evaluate_value_expression(record_value, condition.operator, condition.value)
    except Exception as e:
        raise FilterApplicationError(f"Condition evaluation failed for {condition.field}: {str(e)}")


def _evaluate_value_expression(
    record_value: Any,
    operator: Operator,
    value_expr: ValueExpression
) -> bool:
    """Recursively evaluate a ValueExpression against a record value."""
    
    # Simple value
    if value_expr.is_simple_value:
        return _apply_operator(record_value, operator, value_expr.simple)
    
    # Range value
    if value_expr.is_range_value:
        result = True
        if value_expr.range_start is not None:
            result = result and _apply_operator(record_value, Operator.GREATER_EQUAL, value_expr.range_start)
        if value_expr.range_end is not None:
            result = result and _apply_operator(record_value, Operator.LESS_EQUAL, value_expr.range_end)
        return result
    
    # Compound value (left LOGIC right)
    if value_expr.is_compound_value:
        left_result = _evaluate_value_expression(record_value, operator, value_expr.left)
        right_result = _evaluate_value_expression(record_value, operator, value_expr.right)
        
        if value_expr.logic == LogicalOperator.OR:
            return left_result or right_result
        else:  # AND
            return left_result and right_result
    
    raise FilterApplicationError(f"Invalid value expression structure: {value_expr}")


def _apply_operator(record_value: Any, operator: Operator, filter_value: Any) -> bool:
    """Apply operator comparison between record value and filter value."""
    # Handle None values
    if record_value is None:
        null_values = {None, "", "null"}
        return (filter_value in null_values) == (operator == Operator.EQUAL)
    
    # Normalize values for comparison
    record_val, filter_val = _normalize_values(record_value, filter_value)
    
    # Apply comparison using operator mapping
    ops = {
        Operator.EQUAL: lambda r, f: r == f,
        Operator.NOT_EQUAL: lambda r, f: r != f,
        Operator.GREATER: lambda r, f: r > f,
        Operator.LESS: lambda r, f: r < f,
        Operator.GREATER_EQUAL: lambda r, f: r >= f,
        Operator.LESS_EQUAL: lambda r, f: r <= f,
    }
    
    if operator not in ops:
        raise FilterApplicationError(f"Unknown operator: {operator}")
    
    return ops[operator](record_val, filter_val)


def _normalize_values(record_value: Any, filter_value: Any) -> tuple[Any, Any]:
    """Normalize values for comparison by attempting type coercion."""
    record_str = str(record_value) if record_value is not None else ""
    filter_str = str(filter_value) if filter_value is not None else ""
    
    # Try numeric conversion
    for val_str in [record_str, filter_str]:
        if not val_str:
            continue
        try:
            record_num = int(record_str) if '.' not in record_str else float(record_str)
            filter_num = int(filter_str) if '.' not in filter_str else float(filter_str)
            return record_num, filter_num
        except ValueError:
            continue
    
    # Try boolean conversion
    bool_map = {'true': True, 'yes': True, '1': True, 'on': True,
                'false': False, 'no': False, '0': False, 'off': False}
    
    record_bool = bool_map.get(record_str.lower())
    filter_bool = bool_map.get(filter_str.lower())
    
    if record_bool is not None and filter_bool is not None:
        return record_bool, filter_bool
    
    # Fall back to case-insensitive string comparison
    return record_str.lower(), filter_str.lower()


def get_filter_fields(filters: FilterExpression) -> List[str]:
    """Extract all field names referenced in a filter expression."""
    fields = set()
    
    def extract(expr: FilterExpression):
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