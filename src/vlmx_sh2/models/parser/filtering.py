"""
Filter models for dynamic table filtering.

Contains data structures for representing filter expressions that can be
applied to list and show commands for schemas with cardinality.MULTIPLE.
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field

from vlmx_sh2.enums import Operator


class LogicalOperator(str, Enum):
    """Logical operators for combining filter conditions."""
    AND = "and"
    OR = "or"


class ValueExpression(BaseModel):
    """
    Recursive value expression tree for complex filter values.
    
    Can represent:
    1. Simple value: "product"
    2. Range value: 2022..2029
    3. Compound value: (product|team)&market
    
    Examples:
        - Simple: ValueExpression(simple="product")
        - Range: ValueExpression(range_start="2022", range_end="2029")
        - OR: ValueExpression(left=..., logic=OR, right=...)
        - AND: ValueExpression(left=..., logic=AND, right=...)
    """
    
    # Simple value
    simple: Optional[str] = Field(
        default=None,
        description="Simple string value"
    )
    
    # Range value (start TO end)
    range_start: Optional[str] = Field(
        default=None,
        description="Range start value (None = open-ended ..2029)"
    )
    range_end: Optional[str] = Field(
        default=None,
        description="Range end value (None = open-ended 2022..)"
    )
    
    # Compound value (left LOGIC right)
    left: Optional["ValueExpression"] = Field(
        default=None,
        description="Left side of logical value expression"
    )
    logic: Optional[LogicalOperator] = Field(
        default=None,
        description="Logical operator for value combination (OR/AND)"
    )
    right: Optional["ValueExpression"] = Field(
        default=None,
        description="Right side of logical value expression"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    def __str__(self) -> str:
        """String representation of the value expression."""
        if self.simple is not None:
            return self.simple
        elif self.range_start is not None or self.range_end is not None:
            start = self.range_start or ""
            end = self.range_end or ""
            return f"{start}..{end}"
        elif self.left and self.logic and self.right:
            return f"{self.left}{self.logic.value[0]}{self.right}"  # Use | or &
        else:
            return "EmptyValue"
    
    @property
    def is_simple_value(self) -> bool:
        """True if this is a simple value."""
        return self.simple is not None
    
    @property
    def is_range_value(self) -> bool:
        """True if this is a range value."""
        return self.range_start is not None or self.range_end is not None
    
    @property
    def is_compound_value(self) -> bool:
        """True if this is a compound value (left logic right)."""
        return all([self.left, self.logic, self.right])
    
    def validate_structure(self) -> bool:
        """
        Validate that exactly one value type is set.
        
        Returns:
            True if valid structure, False otherwise
        """
        types_set = sum([
            self.simple is not None,
            self.is_range_value,
            self.is_compound_value
        ])
        return types_set == 1


class FilterCondition(BaseModel):
    """
    Single filter condition: field operator value.
    
    Represents a single comparison operation like:
    - category=product
    - date<2024-01-01
    - similarity>=0.7
    
    Examples:
        >>> FilterCondition(field="category", operator=Operator.EQUAL, value="product")
        >>> FilterCondition(field="date", operator=Operator.LESS, value="2024-01-01")
        >>> FilterCondition(field="active", operator=Operator.NOT_EQUAL, value="false")
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
    1. Single condition: FilterCondition
    2. Logical expression: left LogicalOperator right
    3. Grouped expression: (inner_expression)
    
    This recursive structure allows for complex nested expressions like:
    (category=product & date<2024) | (category=team & date>=2024)
    
    Examples:
        >>> # Single condition
        >>> FilterExpression(condition=FilterCondition(...))
        
        >>> # Logical expression: A AND B
        >>> FilterExpression(
        ...     left=FilterExpression(condition=condition_a),
        ...     operator=LogicalOperator.AND,
        ...     right=FilterExpression(condition=condition_b)
        ... )
        
        >>> # Grouped expression: (A)
        >>> FilterExpression(grouped=FilterExpression(condition=condition_a))
    """
    
    # Single condition
    condition: Optional[FilterCondition] = Field(
        default=None,
        description="Single filter condition"
    )
    
    # Logical expression (left operator right)
    left: Optional['FilterExpression'] = Field(
        default=None,
        description="Left side of logical expression"
    )
    operator: Optional[LogicalOperator] = Field(
        default=None,
        description="Logical operator (AND/OR)"
    )
    right: Optional['FilterExpression'] = Field(
        default=None,
        description="Right side of logical expression"
    )
    
    # Grouped expression
    grouped: Optional['FilterExpression'] = Field(
        default=None,
        description="Grouped (parenthesized) expression"
    )
    
    class Config:
        # Allow self-referencing for recursive structure
        arbitrary_types_allowed = True
    
    def __str__(self) -> str:
        """String representation of the filter expression."""
        if self.condition:
            return str(self.condition)
        elif self.grouped:
            return f"({self.grouped})"
        elif self.left and self.operator and self.right:
            return f"{self.left} {self.operator.value} {self.right}"
        else:
            return "EmptyFilter"
    
    @property
    def is_single_condition(self) -> bool:
        """True if this is a single condition (not logical or grouped)."""
        return self.condition is not None
    
    @property
    def is_logical_expression(self) -> bool:
        """True if this is a logical expression (left operator right)."""
        return all([self.left, self.operator, self.right])
    
    @property
    def is_grouped_expression(self) -> bool:
        """True if this is a grouped expression."""
        return self.grouped is not None
    
    def validate_structure(self) -> bool:
        """
        Validate that exactly one expression type is set.
        
        Returns:
            True if valid structure, False otherwise
        """
        types_set = sum([
            self.condition is not None,
            self.is_logical_expression,
            self.grouped is not None
        ])
        return types_set == 1


# Update forward references
ValueExpression.model_rebuild()
FilterExpression.model_rebuild()