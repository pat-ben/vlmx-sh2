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
    
    _QUERY_KEYWORD_VALUES = {kw.value for kw in QueryKeyword}
    _BRACKET_VALUES = {br.value for br in Bracket}
    _OPERATOR_VALUES = {op.value for op in Operator}
    
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
        
        simple_tokens = [Token(text=rt.text, position=rt.position, was_quoted=rt.was_quoted, operator_after=rt.operator_after) for rt in recognized_filter_tokens]
        
        # Parse using existing recursive descent parser
        return self._parse_expression(simple_tokens)
    
    
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
            remaining = remaining[1:]
            right_expr, remaining = self._parse_and_expression(remaining)
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
                remaining = remaining[1:]
                right_expr, remaining = self._parse_condition(remaining)
                left_expr = FilterExpression(
                    left=left_expr,
                    operator=LogicalOperator.AND,
                    right=right_expr
                )
            elif self._is_condition_start(remaining):
                right_expr, remaining = self._parse_condition(remaining)
                left_expr = FilterExpression(
                    left=left_expr,
                    operator=LogicalOperator.AND,
                    right=right_expr
                )
            else:
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
        
        if tokens[0].text == Bracket.PAREN_OPEN.value:
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
            
            inner_expr = self._parse_expression(tokens[1:close_pos])
            return FilterExpression(grouped=inner_expr), tokens[close_pos + 1:]
        return self._parse_simple_condition(tokens)
    
    def _parse_simple_condition(self, tokens: List[Token]) -> Tuple[FilterExpression, List[Token]]:
        """
        Parse simple condition: field operator value
        
        Returns:
            Tuple of (expression, remaining_tokens)
        """
        if len(tokens) < 3:
            raise FilterParseError("Condition requires at least field, operator, and value")
        
        field, operator_text, value = tokens[0].text, tokens[1].text, tokens[2].text
        
        if not field:
            raise FilterParseError("Empty field name")
        
        if operator_text not in self._OPERATOR_VALUES:
            raise FilterParseError(f"Invalid operator: {operator_text}")
        
        if not value and value != "":
            raise FilterParseError("Empty value")
        
        condition = FilterCondition(field=field, operator=Operator(operator_text), value=value)
        return FilterExpression(condition=condition), tokens[3:]
    
    def _is_condition_start(self, tokens: List[Token]) -> bool:
        """
        Check if tokens start with a condition (field operator value pattern).
        
        Used to detect implicit AND conditions.
        """
        if len(tokens) < 2:
            return False
        
        first_token, second_token = tokens[0].text, tokens[1].text
        
        if first_token.lower() in self._QUERY_KEYWORD_VALUES or first_token in self._BRACKET_VALUES:
            return False
        
        return second_token in self._OPERATOR_VALUES
