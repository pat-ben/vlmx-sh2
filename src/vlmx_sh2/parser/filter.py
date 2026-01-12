"""
Filter parser for extracting and parsing filter expressions.

Extracts filter expressions from token streams and builds structured
FilterExpression trees for dynamic table filtering.
"""

from typing import List, Optional, Tuple
from ..models.parser import Token, RecognizedToken
from ..models.parser.filter import FilterExpression, FilterCondition, LogicalOperator
from vlmx_sh2.enums import Operator, QueryKeyword, Bracket


class FilterParseError(Exception):
    """Raised when filter parsing fails."""
    pass


class FilterParser:
    """
    Parser for filter expressions in [ ] brackets.
    
    Handles the extraction and parsing of filter expressions from token streams,
    building structured FilterExpression trees using recursive descent parsing.
    
    Supports:
    - Simple conditions: [field=value]
    - Implicit AND: [field1=value1 field2=value2]
    - Explicit AND: [field1=value1 and field2=value2]
    - OR expressions: [field1=value1 or field2=value2]
    - Grouped expressions: [(field1=value1 & field2=value2) | field3=value3]
    - All comparison operators: =, !=, <, >, <=, >=
    """
    
    def parse_filters(self, recognized_filter_tokens: List[RecognizedToken]) -> Optional[FilterExpression]:
        """
        Parse filter expression from RECOGNIZED tokens.
        
        No need to re-tokenize! Tokens are already:
        - Split into individual pieces
        - Include operators, keywords, parentheses
        - Recognized (field names classified)
        
        Args:
            recognized_filter_tokens: List of RecognizedToken from tokenizer
            
        Returns:
            Parsed FilterExpression or None
        """
        if not recognized_filter_tokens:
            return None
        
        # Convert RecognizedToken to simple Token for parsing
        # (FilterParser doesn't need the word classification)
        simple_tokens = [
            Token(
                text=rt.text,
                position=rt.position,
                was_quoted=rt.was_quoted,
                operator_after=rt.operator_after
            )
            for rt in recognized_filter_tokens
        ]
        
        # Parse using existing recursive descent parser
        return self._parse_expression(simple_tokens)
    
    
    def _extract_filter_tokens(self, tokens: List[Token]) -> List[Token]:
        """
        Extract tokens between [ and ] brackets.
        
        Args:
            tokens: List of tokens to search
            
        Returns:
            List of tokens found between brackets
            
        Raises:
            FilterParseError: If brackets are mismatched
        """
        bracket_start = None
        bracket_end = None
        
        # Find bracket positions
        for i, token in enumerate(tokens):
            if token.text == Bracket.BRACKET_OPEN.value:
                if bracket_start is not None:
                    raise FilterParseError("Nested [ brackets are not supported")
                bracket_start = i
            elif token.text == Bracket.BRACKET_CLOSE.value:
                if bracket_start is None:
                    raise FilterParseError("Found ] without matching [")
                bracket_end = i
                break
        
        # Validate bracket matching
        if bracket_start is not None and bracket_end is None:
            raise FilterParseError("Found [ without matching ]")
        
        if bracket_start is None:
            return []  # No filters found
        
        # Extract tokens between brackets (exclusive)
        return tokens[bracket_start + 1:bracket_end]
    
    def _parse_expression(self, tokens: List[Token]) -> FilterExpression:
        """
        Parse tokens into FilterExpression using recursive descent.
        
        Grammar (operator precedence from highest to lowest):
        expression := or_expr
        or_expr := and_expr ('or' and_expr)*
        and_expr := condition (('and' | IMPLICIT) condition)*
        condition := '(' expression ')' | field operator value
        
        Args:
            tokens: Filter tokens to parse
            
        Returns:
            Parsed FilterExpression
            
        Raises:
            FilterParseError: If parsing fails
        """
        if not tokens:
            raise FilterParseError("Empty filter expression")
        
        # Start parsing from the top level (OR expressions)
        expr, remaining = self._parse_or_expression(tokens)
        
        if remaining:
            raise FilterParseError(f"Unexpected tokens after filter expression: {[t.text for t in remaining]}")
        
        return expr
    
    def _parse_or_expression(self, tokens: List[Token]) -> Tuple[FilterExpression, List[Token]]:
        """
        Parse OR expressions: and_expr ('or' and_expr)*
        
        Returns:
            Tuple of (expression, remaining_tokens)
        """
        left_expr, remaining = self._parse_and_expression(tokens)
        
        while remaining and remaining[0].text == QueryKeyword.OR.value:
            # Consume 'or'
            remaining = remaining[1:]
            
            # Parse right side
            right_expr, remaining = self._parse_and_expression(remaining)
            
            # Build logical expression
            left_expr = FilterExpression(
                left=left_expr,
                operator=LogicalOperator.OR,
                right=right_expr
            )
        
        return left_expr, remaining
    
    def _parse_and_expression(self, tokens: List[Token]) -> Tuple[FilterExpression, List[Token]]:
        """
        Parse AND expressions: condition (('and' | IMPLICIT) condition)*
        
        Handles both explicit 'and' and implicit AND (space-separated conditions).
        
        Returns:
            Tuple of (expression, remaining_tokens)
        """
        left_expr, remaining = self._parse_condition(tokens)
        
        while remaining:
            # Check for explicit 'and'
            if remaining[0].text == QueryKeyword.AND.value:
                # Consume 'and'
                remaining = remaining[1:]
                
                # Parse right side
                right_expr, remaining = self._parse_condition(remaining)
                
                # Build logical expression
                left_expr = FilterExpression(
                    left=left_expr,
                    operator=LogicalOperator.AND,
                    right=right_expr
                )
            else:
                # Check for implicit AND (next token is not 'or' and looks like start of condition)
                if self._is_condition_start(remaining):
                    # Parse right side (implicit AND)
                    right_expr, remaining = self._parse_condition(remaining)
                    
                    # Build logical expression with implicit AND
                    left_expr = FilterExpression(
                        left=left_expr,
                        operator=LogicalOperator.AND,
                        right=right_expr
                    )
                else:
                    # Not an AND continuation, stop here
                    break
        
        return left_expr, remaining
    
    def _parse_condition(self, tokens: List[Token]) -> Tuple[FilterExpression, List[Token]]:
        """
        Parse single condition: '(' expression ')' | field operator value
        
        Returns:
            Tuple of (expression, remaining_tokens)
        """
        if not tokens:
            raise FilterParseError("Expected condition but found end of input")
        
        # Check for grouped expression: ( ... )
        if tokens[0].text == Bracket.PAREN_OPEN.value:
            # Find matching closing parenthesis
            paren_count = 0
            close_pos = None
            
            for i, token in enumerate(tokens):
                if token.text == Bracket.PAREN_OPEN.value:
                    paren_count += 1
                elif token.text == Bracket.PAREN_CLOSE.value:
                    paren_count -= 1
                    if paren_count == 0:
                        close_pos = i
                        break
            
            if close_pos is None:
                raise FilterParseError("Unmatched opening parenthesis")
            
            # Parse content inside parentheses
            inner_tokens = tokens[1:close_pos]
            inner_expr = self._parse_expression(inner_tokens)
            
            # Return grouped expression
            grouped_expr = FilterExpression(grouped=inner_expr)
            remaining = tokens[close_pos + 1:]
            
            return grouped_expr, remaining
        
        # Parse regular condition: field operator value
        return self._parse_simple_condition(tokens)
    
    def _parse_simple_condition(self, tokens: List[Token]) -> Tuple[FilterExpression, List[Token]]:
        """
        Parse simple condition: field operator value
        
        Returns:
            Tuple of (expression, remaining_tokens)
        """
        if len(tokens) < 3:
            raise FilterParseError("Condition requires at least field, operator, and value")
        
        # Extract field, operator, value
        field_token = tokens[0]
        operator_token = tokens[1]
        value_token = tokens[2]
        
        # Validate field
        field = field_token.text
        if not field:
            raise FilterParseError("Empty field name")
        
        # Parse operator
        try:
            operator = Operator(operator_token.text)
        except ValueError:
            raise FilterParseError(f"Invalid operator: {operator_token.text}")
        
        # Extract value
        value = value_token.text
        if not value and value != "":  # Allow empty string as valid value
            raise FilterParseError("Empty value")
        
        # Create condition
        condition = FilterCondition(
            field=field,
            operator=operator,
            value=value
        )
        
        # Create expression
        expr = FilterExpression(condition=condition)
        
        return expr, tokens[3:]
    
    def _is_condition_start(self, tokens: List[Token]) -> bool:
        """
        Check if tokens start with a condition (field operator value pattern).
        
        Used to detect implicit AND conditions.
        
        Args:
            tokens: Tokens to check
            
        Returns:
            True if tokens look like start of a condition
        """
        if len(tokens) < 2:
            return False
        
        # Check if first token is not a keyword/operator and second token is an operator
        first_token = tokens[0].text
        second_token = tokens[1].text if len(tokens) > 1 else ""
        
        # First token should not be a keyword or bracket
        if first_token.lower() in [kw.value for kw in QueryKeyword]:
            return False
        
        if first_token in [br.value for br in Bracket]:
            return False
        
        # Second token should be an operator
        try:
            Operator(second_token)
            return True
        except ValueError:
            return False


def create_filter_from_tokens(tokens: List[Token]) -> FilterExpression:
    """
    Convenience function to create a filter expression from raw tokens.
    
    Args:
        tokens: Raw tokens to parse (should be filter content only, no brackets)
        
    Returns:
        Parsed FilterExpression
        
    Raises:
        FilterParseError: If parsing fails
    """
    parser = FilterParser()
    return parser._parse_expression(tokens)