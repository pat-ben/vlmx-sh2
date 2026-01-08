"""
Filter application functions for dynamic table filtering.

Provides functionality to apply FilterExpression trees to lists of records,
enabling complex filtering of entities with cardinality.MULTIPLE.
"""

from typing import List, Dict, Any, Union
from ..models.parser.filter import FilterExpression, FilterCondition, LogicalOperator
from ..models.parser.enums import Operator


class FilterApplicationError(Exception):
    """Raised when filter application fails."""
    pass


def apply_filters(records: List[Dict[str, Any]], filters: FilterExpression) -> List[Dict[str, Any]]:
    """
    Apply filter expression to list of records.
    
    Recursively evaluates the FilterExpression tree and returns records
    that match the filter conditions.
    
    Args:
        records: List of records to filter (each record is a dict)
        filters: FilterExpression tree to apply
        
    Returns:
        Filtered list of records that match the filter conditions
        
    Raises:
        FilterApplicationError: If filter application fails
        
    Examples:
        >>> records = [
        ...     {"name": "ACME", "category": "product", "size": "large"},
        ...     {"name": "TechCorp", "category": "team", "size": "small"},
        ...     {"name": "StartUp", "category": "product", "size": "small"}
        ... ]
        >>> # Filter: category=product
        >>> condition = FilterCondition(field="category", operator=Operator.EQUAL, value="product")
        >>> expr = FilterExpression(condition=condition)
        >>> filtered = apply_filters(records, expr)
        >>> # Result: [{"name": "ACME", ...}, {"name": "StartUp", ...}]
    """
    if not records:
        return []
    
    try:
        return [record for record in records if _evaluate_expression(record, filters)]
    except Exception as e:
        raise FilterApplicationError(f"Filter application failed: {str(e)}")


def _evaluate_expression(record: Dict[str, Any], expr: FilterExpression) -> bool:
    """
    Evaluate a filter expression against a single record.
    
    Args:
        record: Record to evaluate (dict of field-value pairs)
        expr: FilterExpression to evaluate
        
    Returns:
        True if record matches the expression, False otherwise
        
    Raises:
        FilterApplicationError: If expression structure is invalid
    """
    # Single condition
    if expr.is_single_condition:
        return _evaluate_condition(record, expr.condition)
    
    # Grouped expression
    elif expr.is_grouped_expression:
        return _evaluate_expression(record, expr.grouped)
    
    # Logical expression (left operator right)
    elif expr.is_logical_expression:
        left_result = _evaluate_expression(record, expr.left)
        right_result = _evaluate_expression(record, expr.right)
        
        if expr.operator == LogicalOperator.AND:
            return left_result and right_result
        elif expr.operator == LogicalOperator.OR:
            return left_result or right_result
        else:
            raise FilterApplicationError(f"Unknown logical operator: {expr.operator}")
    
    else:
        raise FilterApplicationError(f"Invalid expression structure: {expr}")


def _evaluate_condition(record: Dict[str, Any], condition: FilterCondition) -> bool:
    """
    Evaluate a single filter condition against a record.
    
    Args:
        record: Record to evaluate
        condition: FilterCondition to evaluate
        
    Returns:
        True if record matches the condition, False otherwise
        
    Raises:
        FilterApplicationError: If field doesn't exist or comparison fails
    """
    # Get field value from record
    if condition.field not in record:
        # Field doesn't exist - treat as None for comparison
        record_value = None
    else:
        record_value = record[condition.field]
    
    # Get filter value
    filter_value = condition.value
    
    # Apply operator comparison
    try:
        return _apply_operator(record_value, condition.operator, filter_value)
    except Exception as e:
        raise FilterApplicationError(f"Condition evaluation failed for {condition.field}: {str(e)}")


def _apply_operator(record_value: Any, operator: Operator, filter_value: Any) -> bool:
    """
    Apply operator comparison between record value and filter value.
    
    Handles type coercion and comparison logic for different data types.
    
    Args:
        record_value: Value from the record
        operator: Comparison operator
        filter_value: Value from the filter
        
    Returns:
        Boolean result of the comparison
    """
    # Handle None values
    if record_value is None:
        if operator == Operator.EQUAL:
            return filter_value is None or filter_value == "" or filter_value == "null"
        elif operator == Operator.NOT_EQUAL:
            return not (filter_value is None or filter_value == "" or filter_value == "null")
        else:
            return False  # Can't do range comparisons with None
    
    # Convert values to comparable types
    record_val, filter_val = _normalize_values(record_value, filter_value)
    
    # Apply comparison
    if operator == Operator.EQUAL:
        return record_val == filter_val
    elif operator == Operator.NOT_EQUAL:
        return record_val != filter_val
    elif operator == Operator.GREATER:
        return record_val > filter_val
    elif operator == Operator.LESS:
        return record_val < filter_val
    elif operator == Operator.GREATER_EQUAL:
        return record_val >= filter_val
    elif operator == Operator.LESS_EQUAL:
        return record_val <= filter_val
    else:
        raise FilterApplicationError(f"Unknown operator: {operator}")


def _normalize_values(record_value: Any, filter_value: Any) -> tuple[Any, Any]:
    """
    Normalize values for comparison by attempting type coercion.
    
    Attempts to convert both values to compatible types for comparison.
    Priority: number > string
    
    Args:
        record_value: Value from record
        filter_value: Value from filter
        
    Returns:
        Tuple of normalized (record_val, filter_val)
    """
    # Convert to strings for initial processing
    record_str = str(record_value) if record_value is not None else ""
    filter_str = str(filter_value) if filter_value is not None else ""
    
    # Try to convert both to numbers (int or float)
    record_num = _try_parse_number(record_str)
    filter_num = _try_parse_number(filter_str)
    
    if record_num is not None and filter_num is not None:
        # Both are numbers
        return record_num, filter_num
    
    # Try boolean conversion
    record_bool = _try_parse_boolean(record_str)
    filter_bool = _try_parse_boolean(filter_str)
    
    if record_bool is not None and filter_bool is not None:
        return record_bool, filter_bool
    
    # Fall back to case-insensitive string comparison
    return record_str.lower(), filter_str.lower()


def _try_parse_number(value: str) -> Union[int, float, None]:
    """
    Try to parse string as number (int or float).
    
    Returns:
        Parsed number or None if not a number
    """
    if not value:
        return None
    
    try:
        # Try int first
        if '.' not in value and 'e' not in value.lower():
            return int(value)
        else:
            return float(value)
    except ValueError:
        return None


def _try_parse_boolean(value: str) -> Union[bool, None]:
    """
    Try to parse string as boolean.
    
    Returns:
        Parsed boolean or None if not a boolean
    """
    if not value:
        return None
    
    value_lower = value.lower()
    if value_lower in ['true', 'yes', '1', 'on']:
        return True
    elif value_lower in ['false', 'no', '0', 'off']:
        return False
    else:
        return None


def count_matching_records(records: List[Dict[str, Any]], filters: FilterExpression) -> int:
    """
    Count records that match filter expression without loading them all.
    
    Useful for pagination and performance optimization.
    
    Args:
        records: List of records to count
        filters: FilterExpression to apply
        
    Returns:
        Count of matching records
    """
    count = 0
    for record in records:
        try:
            if _evaluate_expression(record, filters):
                count += 1
        except FilterApplicationError:
            # Skip records that can't be evaluated
            continue
    return count


def get_filter_fields(filters: FilterExpression) -> List[str]:
    """
    Extract all field names referenced in a filter expression.
    
    Useful for validating field existence and optimizing queries.
    
    Args:
        filters: FilterExpression to analyze
        
    Returns:
        List of unique field names used in the filter
    """
    fields = set()
    
    def _extract_fields(expr: FilterExpression):
        if expr.is_single_condition:
            fields.add(expr.condition.field)
        elif expr.is_grouped_expression:
            _extract_fields(expr.grouped)
        elif expr.is_logical_expression:
            _extract_fields(expr.left)
            _extract_fields(expr.right)
    
    _extract_fields(filters)
    return sorted(list(fields))