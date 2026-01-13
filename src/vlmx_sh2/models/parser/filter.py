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
    value: Any = Field(description="Value to compare against")
    
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
FilterExpression.model_rebuild()