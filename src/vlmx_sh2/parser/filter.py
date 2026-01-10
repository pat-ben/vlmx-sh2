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
    
    def parse_filters(self, tokens: List[RecognizedToken]) -> Optional[FilterExpression]:
        """
        Parse filter expressions from recognized token list.
        
        Args:
            tokens: List of recognized tokens from the parser
            
        Returns:
            Parsed FilterExpression or None if no filters found
            
        Raises:
            FilterParseError: If filter syntax is invalid
        """
        # For now, return None since we need the raw input to properly parse filters
        # This is used by VLMXParser which passes raw input for filter parsing
        return None
    
    def parse_filters_from_raw_input(self, raw_input: str) -> Optional[FilterExpression]:
        """
        Parse filter expressions from raw input text.
        
        This method can properly handle brackets since it works with the original text.
        
        Args:
            raw_input: Original user input text
            
        Returns:
            Parsed FilterExpression or None if no filters found
            
        Raises:
            FilterParseError: If filter syntax is invalid
        """
        # Expand macros first
        from ..dsl.macros import expand_macros
        expanded_input = expand_macros(raw_input)
        
        # Tokenize to get brackets
        from ..parser.tokenizer import Tokenizer
        raw_tokens_with_brackets = Tokenizer._extract_quoted_strings(expanded_input)
        
        # Find filter boundaries in raw tokens
        filter_token_texts = self._extract_filter_token_texts(raw_tokens_with_brackets)
        if not filter_token_texts:
            return None
        
        # Convert to Token objects for parsing
        filter_tokens = []
        for i, text in enumerate(filter_token_texts):
            # Parse operators within tokens
            if self._contains_operator(text):
                key, op, val = self._parse_attribute_token(text)
                filter_tokens.append(Token(text=key, position=len(filter_tokens)))
                filter_tokens.append(Token(text=op, position=len(filter_tokens)))
                filter_tokens.append(Token(text=val, position=len(filter_tokens)))
            else:
                filter_tokens.append(Token(text=text, position=len(filter_tokens)))
        
        # Parse the filter tokens into an expression tree
        return self._parse_expression(filter_tokens)
    
    def _reconstruct_raw_input(self, tokens: List[RecognizedToken]) -> str:
        """Reconstruct approximate raw input from recognized tokens."""
        # This is a simplified reconstruction - in practice we'd pass raw input
        parts = []
        for i, token in enumerate(tokens):
            text = f'"{token.text}"' if token.was_quoted else token.text
            if token.operator_after:
                text += token.operator_after.value
            parts.append(text)
        return " ".join(parts)
    
    def _extract_filter_token_texts(self, raw_tokens: List[str]) -> List[str]:
        """Extract filter content from raw token list with brackets."""
        bracket_start = None
        bracket_end = None
        
        # Find bracket positions
        for i, token in enumerate(raw_tokens):
            if token == "[":
                if bracket_start is not None:
                    raise FilterParseError("Nested [ brackets are not supported")
                bracket_start = i
            elif token == "]":
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
        return raw_tokens[bracket_start + 1:bracket_end]
    
    def _contains_operator(self, text: str) -> bool:
        """Check if text contains a comparison operator."""
        operators = [op.value for op in Operator]
        return any(op in text for op in operators)
    
    def _parse_attribute_token(self, token: str) -> Tuple[str, str, str]:
        """Parse field=value token into (field, operator, value)."""
        # Check operators in order of precedence (longer operators first)
        operators = [
            Operator.GREATER_EQUAL.value,  # ">="
            Operator.LESS_EQUAL.value,     # "<="
            Operator.NOT_EQUAL.value,      # "!="
            Operator.EQUAL.value,          # "="
            Operator.GREATER.value,        # ">"
            Operator.LESS.value,           # "<"
        ]
        
        for operator in operators:
            if operator in token:
                parts = token.split(operator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    return key, operator, value
        
        raise FilterParseError(f"No operator found in token: {token}")
    
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