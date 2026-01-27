"""
PARSING STAGE 6/7: Filter Expression Parser

Builds an AST (Abstract Syntax Tree) from filter tokens using recursive descent parsing.
Operates on filter tokens from the Splitter stage (Stage 5).

Input: SplitResult with filter_tokens: List[InterpretedToken]
Output: FilterExpression (recursive AST with AND/OR/grouped)

Grammar:
    expression   := or_expr
    or_expr      := and_expr ('OR' and_expr)*
    and_expr     := condition (('AND' | IMPLICIT_AND) condition)*
    condition    := '(' expression ')' | field operator value_expr

    value_expr   := value_or
    value_or     := value_and ('OR' value_and)*
    value_and    := value_term ('AND' value_term)*
    value_term   := '(' value_expr ')' | range_value | simple_value
    range_value  := simple_value 'TO' simple_value
                  | simple_value 'TO'                  # Open-ended: >= value
                  | 'TO' simple_value                  # Open-ended: <= value

Operator precedence (highest to lowest):
    1. Parentheses ( )
    2. AND (explicit or implicit)
    3. OR (always explicit)
"""

from typing import List, Optional
from ..models.parser import InterpretedToken, SplitResult
from ..models.parser.filtering import FilterExpression, FilterCondition, LogicalOperator, ValueExpression
from ..models.validation import ValidationContext
from vlmx_sh2.enums import IssueStage, QueryWord, Bracket, RangeWord
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
        parser_instance = cls(filter_tokens, context)
        expression = parser_instance._parse_expression()
        
        # Return None if parsing failed
        if parser_instance._has_error or expression is None:
            return None
        
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
    
    # =============================================================================
    # Parser Instance for Recursive Descent
    # =============================================================================
    
    def __init__(self, tokens: List[InterpretedToken], context: ValidationContext):
        """Initialize parser instance for token stream."""
        self.tokens = tokens
        self.context = context
        self.position = 0
        self._has_error = False
    
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
    
    def _add_error(self, message: str, token_text: str = "") -> None:
        """Add error to validation context and mark parsing as failed."""
        self.context.add_error(
            stage=IssueStage.FILTER,
            message=message,
            token_text=token_text
        )
        self._has_error = True
    
    # =============================================================================
    # Recursive Descent Grammar Implementation
    # =============================================================================
    
    def _parse_expression(self) -> Optional[FilterExpression]:
        """
        Parse tokens into FilterExpression using recursive descent.
        
        Grammar entry point:
        expression := or_expr
        
        Returns:
            Parsed FilterExpression or None if parsing fails
        """
        if not self.tokens:
            self._add_error("Empty filter expression")
            return None
        
        return self._parse_or_expression()
    
    def _parse_or_expression(self) -> Optional[FilterExpression]:
        """
        Parse OR expressions: and_expr ('OR' and_expr)*
        
        OR has lowest precedence, so it's at the top level.
        
        Returns:
            FilterExpression (single or OR tree) or None if parsing fails
        """
        left_expr = self._parse_and_expression()
        if self._has_error or left_expr is None:
            return None
        
        while self._current_token() and self._is_or_keyword(self._current_token()):
            self._consume_token()  # consume 'OR'
            right_expr = self._parse_and_expression()
            if self._has_error or right_expr is None:
                return None
            left_expr = FilterExpression(
                left=left_expr,
                operator=LogicalOperator.OR,
                right=right_expr
            )
        
        return left_expr
    
    def _parse_and_expression(self) -> Optional[FilterExpression]:
        """
        Parse AND expressions: condition (('AND' | IMPLICIT_AND) condition)*
        
        Handles both explicit 'AND' and implicit AND (space-separated conditions).
        AND has higher precedence than OR.
        
        Returns:
            FilterExpression (single condition or AND tree) or None if parsing fails
        """
        left_expr = self._parse_condition()
        if self._has_error or left_expr is None:
            return None
        
        while self._current_token():
            current = self._current_token()
            
            # Check for explicit 'AND'
            if self._is_and_keyword(current):
                self._consume_token()  # consume 'AND'
                right_expr = self._parse_condition()
                if self._has_error or right_expr is None:
                    return None
                left_expr = FilterExpression(
                    left=left_expr,
                    operator=LogicalOperator.AND,
                    right=right_expr
                )
            # Check for implicit AND (start of new condition)
            elif self._is_condition_start():
                right_expr = self._parse_condition()
                if self._has_error or right_expr is None:
                    return None
                left_expr = FilterExpression(
                    left=left_expr,
                    operator=LogicalOperator.AND,
                    right=right_expr
                )
            else:
                # Not a continuation of AND expression
                break
        
        return left_expr
    
    def _parse_condition(self) -> Optional[FilterExpression]:
        """
        Parse single condition: '(' expression ')' | field operator value
        
        Handles parenthesized expressions and simple field conditions.
        
        Returns:
            FilterExpression (grouped or single condition) or None if parsing fails
        """
        current = self._current_token()
        if not current:
            self._add_error("Expected condition but found end of input")
            return None
        
        # Check for grouped expression: ( ... )
        if self._is_open_paren(current):
            return self._parse_grouped_expression()
        
        # Parse simple condition: field operator value
        return self._parse_simple_condition()
    
    def _parse_grouped_expression(self) -> Optional[FilterExpression]:
        """
        Parse grouped expression: '(' expression ')'
        
        Returns:
            FilterExpression with grouped field set or None if parsing fails
        """
        # Consume opening parenthesis
        open_paren = self._consume_token()
        if not self._is_open_paren(open_paren):
            token_text = open_paren.text if open_paren else "end of input"
            self._add_error(f"Expected '(' but found '{token_text}'", token_text)
            return None
        
        # Parse inner expression
        inner_expr = self._parse_expression()
        if self._has_error or inner_expr is None:
            return None
        
        # Consume closing parenthesis
        close_paren = self._consume_token()
        if not close_paren or not self._is_close_paren(close_paren):
            if close_paren:
                self._add_error(f"Expected ')' but found '{close_paren.text}'", close_paren.text)
            else:
                self._add_error("Expected ')' but found end of input")
            return None
        
        return FilterExpression(grouped=inner_expr)
    
    def _parse_simple_condition(self) -> Optional[FilterExpression]:
        """
        Parse simple condition: field operator value_expr
        
        Returns:
            FilterExpression with condition field set or None if parsing fails
        """
        # Need at least 3 tokens: field operator value
        available = len(self.tokens) - self.position
        if available < 3:
            self._add_error(f"Condition requires field, operator, and value (found {available} tokens)")
            return None
        
        # Extract field and operator
        field_token = self._consume_token()
        operator_token = self._consume_token()
        
        # Validate field
        if not field_token or not field_token.text:
            self._add_error("Empty field name", field_token.text if field_token else "")
            return None
        
        # Validate operator
        if not operator_token or not hasattr(operator_token, 'operator') or not operator_token.operator:
            operator_text = operator_token.text if operator_token else "None"
            self._add_error(f"Invalid operator: {operator_text}", operator_text)
            return None
        
        # Parse value expression
        value_expression = self._parse_value_expression()
        if self._has_error or value_expression is None:
            return None
        
        # Build condition
        condition = FilterCondition(
            field=field_token.text,
            operator=operator_token.operator,
            value=value_expression
        )
        
        return FilterExpression(condition=condition)
    
    # =============================================================================
    # Value Expression Parsing
    # =============================================================================
    
    def _parse_value_expression(self) -> Optional[ValueExpression]:
        """
        Parse value expression: value_or
        
        Entry point for value parsing.
        
        Returns:
            ValueExpression or None if parsing fails
        """
        return self._parse_value_or()
    
    def _parse_value_or(self) -> Optional[ValueExpression]:
        """
        Parse value OR expressions: value_and ('OR' value_and)*
        
        Handles: product|team|market
        
        Returns:
            ValueExpression (simple or OR tree) or None if parsing fails
        """
        left_expr = self._parse_value_and()
        if self._has_error or left_expr is None:
            return None
        
        while self._current_token() and self._is_or_keyword(self._current_token()) and self._is_in_value_context():
            self._consume_token()  # consume 'OR' / '|'
            right_expr = self._parse_value_and()
            if self._has_error or right_expr is None:
                return None
            left_expr = ValueExpression(
                left=left_expr,
                logic=LogicalOperator.OR,
                right=right_expr
            )
        
        return left_expr
    
    def _parse_value_and(self) -> Optional[ValueExpression]:
        """
        Parse value AND expressions: value_term ('AND' value_term)*
        
        Handles: (product|team)&market
        
        Returns:
            ValueExpression (simple or AND tree) or None if parsing fails
        """
        left_expr = self._parse_value_term()
        if self._has_error or left_expr is None:
            return None
        
        while self._current_token() and self._is_and_keyword(self._current_token()) and self._is_in_value_context():
            self._consume_token()  # consume 'AND' / '&'
            right_expr = self._parse_value_term()
            if self._has_error or right_expr is None:
                return None
            left_expr = ValueExpression(
                left=left_expr,
                logic=LogicalOperator.AND,
                right=right_expr
            )
        
        return left_expr
    
    def _parse_value_term(self) -> Optional[ValueExpression]:
        """
        Parse value term: '(' value_expr ')' | range_value | simple_value
        
        Handles parentheses, ranges, or simple values.
        
        Returns:
            ValueExpression or None if parsing fails
        """
        current = self._current_token()
        if not current:
            self._add_error("Expected value but found end of input")
            return None
        
        # Check for grouped value expression: ( ... )
        if self._is_open_paren(current):
            return self._parse_grouped_value_expression()
        
        # Try to parse as range or simple value
        return self._parse_range_or_simple_value()
    
    def _parse_grouped_value_expression(self) -> Optional[ValueExpression]:
        """
        Parse grouped value expression: '(' value_expr ')'
        
        Returns:
            ValueExpression or None if parsing fails
        """
        # Consume opening parenthesis
        open_paren = self._consume_token()
        if not self._is_open_paren(open_paren):
            token_text = open_paren.text if open_paren else "end of input"
            self._add_error(f"Expected '(' but found '{token_text}'", token_text)
            return None
        
        # Parse inner value expression
        inner_expr = self._parse_value_expression()
        if self._has_error or inner_expr is None:
            return None
        
        # Consume closing parenthesis
        close_paren = self._consume_token()
        if not close_paren or not self._is_close_paren(close_paren):
            if close_paren:
                self._add_error(f"Expected ')' but found '{close_paren.text}'", close_paren.text)
            else:
                self._add_error("Expected ')' but found end of input")
            return None
        
        return inner_expr  # Return inner expression directly, parentheses are just grouping
    
    def _parse_range_or_simple_value(self) -> Optional[ValueExpression]:
        """
        Parse range value or simple value.
        
        Handles:
        - Simple value: "product"
        - Range: 2022..2029, 2022.., ..2029
        
        Returns:
            ValueExpression or None if parsing fails
        """
        current = self._current_token()
        if not current:
            self._add_error("Expected value but found end of input")
            return None
        
        # Check if we start with 'TO' (..2029 case)
        if self._is_range_keyword(current):
            return self._parse_open_end_range()
        
        # Consume first value
        start_value = self._consume_token()
        if not start_value or not start_value.text:
            self._add_error("Empty value", start_value.text if start_value else "")
            return None
        
        # Check if next token is 'TO' (range case)
        next_token = self._current_token()
        if next_token and self._is_range_keyword(next_token):
            return self._parse_range_value(start_value.text)
        
        # Simple value case
        return ValueExpression(simple=start_value.text)
    
    def _parse_range_value(self, start_value: str) -> Optional[ValueExpression]:
        """
        Parse range value: start_value TO [end_value]
        
        Handles: 2022 TO 2029, 2022 TO (open-ended)
        
        Args:
            start_value: Already consumed start value
            
        Returns:
            ValueExpression with range or None if parsing fails
        """
        # Consume 'TO'
        to_token = self._consume_token()
        if not self._is_range_keyword(to_token):
            token_text = to_token.text if to_token else "end of input"
            self._add_error(f"Expected 'to' but found '{token_text}'", token_text)
            return None
        
        # Check if there's an end value (not end of value expression)
        next_token = self._current_token()
        if next_token and self._is_value_token(next_token) and not self._is_next_condition_start():
            # Consume end value
            end_value_token = self._consume_token()
            return ValueExpression(range_start=start_value, range_end=end_value_token.text)
        else:
            # Open-ended range: 2022..
            return ValueExpression(range_start=start_value, range_end=None)
    
    def _parse_open_end_range(self) -> Optional[ValueExpression]:
        """
        Parse open-ended range: TO end_value
        
        Handles: ..2029
        
        Returns:
            ValueExpression with range or None if parsing fails
        """
        # Consume 'TO'
        to_token = self._consume_token()
        if not self._is_range_keyword(to_token):
            token_text = to_token.text if to_token else "end of input"
            self._add_error(f"Expected 'to' but found '{token_text}'", token_text)
            return None
        
        # Must have an end value
        next_token = self._current_token()
        if not next_token or not self._is_value_token(next_token):
            self._add_error("Expected value after 'to' in range expression")
            return None
        
        end_value_token = self._consume_token()
        return ValueExpression(range_start=None, range_end=end_value_token.text)
    
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
    
    def _is_range_keyword(self, token: Optional[InterpretedToken]) -> bool:
        """Check if token is 'TO' range keyword."""
        return token is not None and token.range_word == RangeWord.TO
    
    def _is_value_token(self, token: Optional[InterpretedToken]) -> bool:
        """Check if token can be used as a value (not an operator, keyword, or bracket)."""
        if not token:
            return False
        return not (token.operator or token.query_word or token.range_word or token.bracket)
    
    def _is_in_value_context(self) -> bool:
        """Check if we're still in value parsing context (not at start of new condition)."""
        return not self._is_next_condition_start()
    
    def _is_next_condition_start(self) -> bool:
        """Check if upcoming tokens start a new condition (lookahead for field operator pattern)."""
        current = self._current_token()
        next_token = self._peek_token()
        
        if not current or not next_token:
            return False
        
        # Skip if current token is a keyword or bracket
        if current.query_word or current.bracket:
            return False
        
        # Check if next token is an operator (indicates field=value pattern)
        return next_token.operator is not None
    
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