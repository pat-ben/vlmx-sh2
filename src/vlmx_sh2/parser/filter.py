"""
PARSING STAGE 6/7: Filter Expression Parser

Builds an AST (Abstract Syntax Tree) from filter tokens using recursive descent parsing.
Operates on filter tokens from the Splitter stage (Stage 5).

Input: SplitResult with filter_tokens: List[InterpretedToken]
Output: FilterExpression (recursive AST with AND/OR/grouped)

Grammar:
    expression  := or_expr
    or_expr     := and_expr ('OR' and_expr)*
    and_expr    := condition (('AND' | IMPLICIT_AND) condition)*
    condition   := '(' expression ')' | field operator value

Operator precedence (highest to lowest):
    1. Parentheses ( )
    2. AND (explicit or implicit)
    3. OR (always explicit)
"""

from typing import List, Optional
from ..models.parser import InterpretedToken, SplitResult, FilterParseError
from ..models.parser.filtering import FilterExpression, FilterCondition, LogicalOperator
from ..models.validation import ValidationContext
from vlmx_sh2.enums import IssueStage, QueryWord, Bracket
from ..diagnostics import Validator


class Filter:
    """
   
    Builds an AST (Abstract Syntax Tree) from filter tokens using recursive descent parsing.
    Operates on InterpretedToken objects from the Splitter stage.
    
    Supports:
    - Simple conditions: currency=EUR
    - Implicit AND: currency=EUR date<2025
    - Explicit AND: currency=EUR AND date<2025
    - OR expressions: currency=EUR OR currency=USD
    - Grouped expressions: (currency=EUR AND date<2025) OR status=active
    - All comparison operators: =, !=, <, >, <=, >=
    """
    
    # =============================================================================
    # Public API - Main Entry Point
    # =============================================================================
    
    @classmethod
    def parse(
        cls,
        split_result: SplitResult,
        context: ValidationContext
    ) -> Optional[FilterExpression]:
        """
        
        Processing:
        1. Check if filter exists in split_result
        2. Extract filter tokens
        3. Parse using recursive descent grammar
        4. Validate using diagnostic rules
        5. Return FilterExpression AST
        
        Args:
            split_result: Output from Splitter stage (Stage 5)
            context: ValidationContext for error reporting
            
        Returns:
            FilterExpression AST or None if no filter exists
            
        Examples:
            >>> # Input: [currency=EUR date<2025]
            >>> filter_tokens = [
            ...     InterpretedToken(text="currency", token_type=TokenType.WORD, ...),
            ...     InterpretedToken(text="=", token_type=TokenType.STRUCTURAL, operator=Operator.EQUAL, ...),
            ...     InterpretedToken(text="EUR", token_type=TokenType.VALUE, ...),
            ...     InterpretedToken(text="date", token_type=TokenType.WORD, ...),
            ...     InterpretedToken(text="<", token_type=TokenType.STRUCTURAL, operator=Operator.LESS, ...),
            ...     InterpretedToken(text="2025", token_type=TokenType.VALUE, ...)
            ... ]
            >>> split_result = SplitResult(filter_tokens=filter_tokens, has_filter=True, ...)
            >>> result = Filter.parse(split_result, context)
            >>> # Returns: FilterExpression with AND of two conditions
        """
        # Step 1: Check if filter exists
        if not split_result.has_filter:
            return None
        
        filter_tokens = split_result.filter_tokens
        if not filter_tokens:
            return None
        
        # Step 2: Validate the filter tokens
        # Runs all FILTER stage validation rules from diagnostics module
        Validator.validate_tokens(IssueStage.FILTER, context, tokens=filter_tokens)
        
        # Step 3: Parse using recursive descent
        try:
            parser_instance = cls(filter_tokens, context)
            expression = parser_instance._parse_expression()
            
            # Ensure we consumed all tokens
            if parser_instance.position < len(filter_tokens):
                remaining_tokens = filter_tokens[parser_instance.position:]
                remaining_text = ' '.join(token.text for token in remaining_tokens)
                context.add_error(
                    stage=IssueStage.FILTER,
                    message=f"Unexpected tokens after filter expression: {remaining_text}",
                    token_text=remaining_tokens[0].text if remaining_tokens else ""
                )
                return None
            
            return expression
            
        except FilterParseError as e:
            context.add_error(
                stage=IssueStage.FILTER,
                message=str(e)
            )
            return None
    
    # =============================================================================
    # Parser Instance for Recursive Descent
    # =============================================================================
    
    def __init__(self, tokens: List[InterpretedToken], context: ValidationContext):
        """Initialize parser instance for token stream."""
        self.tokens = tokens
        self.context = context
        self.position = 0
    
    def _current_token(self) -> Optional[InterpretedToken]:
        """Get current token or None if at end."""
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return None
    
    def _peek_token(self, offset: int = 1) -> Optional[InterpretedToken]:
        """Peek at token ahead by offset."""
        peek_pos = self.position + offset
        if peek_pos < len(self.tokens):
            return self.tokens[peek_pos]
        return None
    
    def _consume_token(self) -> Optional[InterpretedToken]:
        """Consume and return current token."""
        token = self._current_token()
        if token:
            self.position += 1
        return token
    
    # =============================================================================
    # Recursive Descent Grammar Implementation
    # =============================================================================
    
    def _parse_expression(self) -> FilterExpression:
        """
        Parse tokens into FilterExpression using recursive descent.
        
        Grammar entry point:
        expression := or_expr
        
        Returns:
            Parsed FilterExpression
            
        Raises:
            FilterParseError: If parsing fails
        """
        if not self.tokens:
            raise FilterParseError("Empty filter expression")
        
        return self._parse_or_expression()
    
    def _parse_or_expression(self) -> FilterExpression:
        """
        Parse OR expressions: and_expr ('OR' and_expr)*
        
        OR has lowest precedence, so it's at the top level.
        
        Returns:
            FilterExpression (single or OR tree)
        """
        left_expr = self._parse_and_expression()
        
        while self._current_token() and self._is_or_keyword(self._current_token()):
            self._consume_token()  # consume 'OR'
            right_expr = self._parse_and_expression()
            left_expr = FilterExpression(
                left=left_expr,
                operator=LogicalOperator.OR,
                right=right_expr
            )
        
        return left_expr
    
    def _parse_and_expression(self) -> FilterExpression:
        """
        Parse AND expressions: condition (('AND' | IMPLICIT_AND) condition)*
        
        Handles both explicit 'AND' and implicit AND (space-separated conditions).
        AND has higher precedence than OR.
        
        Returns:
            FilterExpression (single condition or AND tree)
        """
        left_expr = self._parse_condition()
        
        while self._current_token():
            current = self._current_token()
            
            # Check for explicit 'AND'
            if self._is_and_keyword(current):
                self._consume_token()  # consume 'AND'
                right_expr = self._parse_condition()
                left_expr = FilterExpression(
                    left=left_expr,
                    operator=LogicalOperator.AND,
                    right=right_expr
                )
            # Check for implicit AND (start of new condition)
            elif self._is_condition_start():
                right_expr = self._parse_condition()
                left_expr = FilterExpression(
                    left=left_expr,
                    operator=LogicalOperator.AND,
                    right=right_expr
                )
            else:
                # Not a continuation of AND expression
                break
        
        return left_expr
    
    def _parse_condition(self) -> FilterExpression:
        """
        Parse single condition: '(' expression ')' | field operator value
        
        Handles parenthesized expressions and simple field conditions.
        
        Returns:
            FilterExpression (grouped or single condition)
        """
        current = self._current_token()
        if not current:
            raise FilterParseError("Expected condition but found end of input")
        
        # Check for grouped expression: ( ... )
        if self._is_open_paren(current):
            return self._parse_grouped_expression()
        
        # Parse simple condition: field operator value
        return self._parse_simple_condition()
    
    def _parse_grouped_expression(self) -> FilterExpression:
        """
        Parse grouped expression: '(' expression ')'
        
        Returns:
            FilterExpression with grouped field set
        """
        # Consume opening parenthesis
        open_paren = self._consume_token()
        if not self._is_open_paren(open_paren):
            token_text = open_paren.text if open_paren else "end of input"
            raise FilterParseError(f"Expected '(' but found '{token_text}'")
        
        # Parse inner expression
        inner_expr = self._parse_expression()
        
        # Consume closing parenthesis
        close_paren = self._consume_token()
        if not close_paren or not self._is_close_paren(close_paren):
            if close_paren:
                raise FilterParseError(f"Expected ')' but found '{close_paren.text}'")
            else:
                raise FilterParseError("Expected ')' but found end of input")
        
        return FilterExpression(grouped=inner_expr)
    
    def _parse_simple_condition(self) -> FilterExpression:
        """
        Parse simple condition: field operator value
        
        Returns:
            FilterExpression with condition field set
        """
        # Need at least 3 tokens: field operator value
        available = len(self.tokens) - self.position
        if available < 3:
            raise FilterParseError(f"Condition requires field, operator, and value (found {available} tokens)")
        
        # Extract field, operator, value
        field_token = self._consume_token()
        operator_token = self._consume_token()
        value_token = self._consume_token()
        
        # Validate field
        if not field_token or not field_token.text:
            raise FilterParseError("Empty field name")
        
        # Validate operator
        if not operator_token or not hasattr(operator_token, 'operator') or not operator_token.operator:
            operator_text = operator_token.text if operator_token else "None"
            raise FilterParseError(f"Invalid operator: {operator_text}")
        
        # Validate value
        if not value_token or not value_token.text:
            raise FilterParseError("Empty value")
        
        # Build condition
        condition = FilterCondition(
            field=field_token.text,
            operator=operator_token.operator,
            value=value_token.text
        )
        
        return FilterExpression(condition=condition)
    
    # =============================================================================
    # Token Type Detection Utilities
    # =============================================================================
    
    def _is_or_keyword(self, token: Optional[InterpretedToken]) -> bool:
        """Check if token is 'OR' keyword."""
        return token is not None and token.query_word == QueryWord.OR
    
    def _is_and_keyword(self, token: Optional[InterpretedToken]) -> bool:
        """Check if token is 'AND' keyword."""
        return token is not None and token.query_word == QueryWord.AND
    
    def _is_open_paren(self, token: Optional[InterpretedToken]) -> bool:
        """Check if token is opening parenthesis '('."""
        return token is not None and token.bracket == Bracket.PAREN_OPEN
    
    def _is_close_paren(self, token: Optional[InterpretedToken]) -> bool:
        """Check if token is closing parenthesis ')'."""
        return token is not None and token.bracket == Bracket.PAREN_CLOSE
    
    def _is_condition_start(self) -> bool:
        """Check if current position starts a condition (field operator value pattern)."""
        current = self._current_token()
        next_token = self._peek_token()
        
        if not current or not next_token:
            return False
        
        # Skip if current token is a keyword or parenthesis
        if current.query_word or current.bracket:
            return False
        
        # Check if next token is an operator
        return next_token.operator is not None