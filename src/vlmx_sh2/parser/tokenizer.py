"""
Tokenizer for VLMX DSL parser.

A three-stage tokenization system that extracts and organizes tokens with metadata.
The tokenizer's sole responsibility is text processing - no semantic classification.
"""

import re
from typing import List, Dict, Any
from ..models.parser import Token, Operator, QueryKeyword, Bracket


class Tokenizer:
    """Clean three-stage tokenizer for VLMX DSL input."""
    
    @classmethod
    def tokenize(cls, text: str) -> List[Token]:
        """
        Tokenize input text into organized tokens with metadata.
        
        Three-stage process:
        1. Extract quoted strings
        2. Build full ordered list
        3. Build short-listed array (exclude operators/keywords)
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of Token objects with metadata
            
        Examples:
            >>> tokenize('create company "ACME"')
            [
                Token(text="create", position=0, was_quoted=False),
                Token(text="company", position=1, was_quoted=False),
                Token(text="ACME", position=2, was_quoted=True),
            ]
            
            >>> tokenize('vision="Our vision" currency=EUR')
            [
                Token(text="vision", position=0, operator_after=Operator.EQUAL),
                Token(text="Our vision", position=1, was_quoted=True),
                Token(text="currency", position=2, operator_after=Operator.EQUAL),
                Token(text="EUR", position=3),
            ]
        """
        # Stage 1: Extract quoted strings
        raw_tokens = cls._extract_quoted_strings(text)
        
        # Stage 2: Build full ordered list with metadata
        full_list = cls._build_full_list(raw_tokens)
        
        # Stage 3: Build short-listed array
        tokens = cls._build_shortlist(full_list)
        
        return tokens
    
    @classmethod
    def _extract_quoted_strings(cls, text: str) -> List[str]:
        """
        Extract tokens from text, treating quoted strings as single tokens.
        
        Handles both single and double quotes.
        Multi-word quoted strings are kept as one token.
        Key=value pairs with quoted values are kept as single tokens.
        
        Example:
            Input: 'create "ACME INTL" vision="Our vision"'
            Output: ['create', '"ACME INTL"', 'vision="Our vision"']
        """
        tokens = []
        i = 0
        current_token = ""
        in_quotes = False
        quote_char = None
        
        while i < len(text):
            char = text[i]
            
            if not in_quotes:
                if char in '"\'':
                    # Starting a quoted string - don't break current token
                    in_quotes = True
                    quote_char = char
                    current_token += char
                elif char.isspace():
                    # End of regular token
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                elif char in [bracket.value for bracket in Bracket]:
                    # Handle brackets as separate tokens using Bracket enum
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                    tokens.append(char)
                else:
                    current_token += char
            else:
                # Inside quotes
                current_token += char
                if char == quote_char:
                    # End of quoted string
                    in_quotes = False
                    quote_char = None
            
            i += 1
        
        # Add final token if exists
        if current_token.strip():
            tokens.append(current_token.strip())
        
        return tokens
    
    @classmethod
    def _build_full_list(cls, raw_tokens: List[str]) -> List[Dict[str, Any]]:
        """
        Build full ordered list with ALL elements and metadata.
        
        For each token:
        - Strip quotes if present (mark as was_quoted=True)
        - Identify if it's an excluded element (operator, keyword, bracket)
        - Separate key=value into ["key", "=", "value"]
        
        Example:
            Input: ['create', '"ACME"', 'vision="text"']
            Output: [
                {"text": "create", "was_quoted": False, "is_excluded": False},
                {"text": "ACME", "was_quoted": True, "is_excluded": False},
                {"text": "vision", "was_quoted": False, "is_excluded": False},
                {"text": "=", "was_quoted": False, "is_excluded": True},
                {"text": "text", "was_quoted": True, "is_excluded": False},
            ]
        """
        full_list = []
        
        for token in raw_tokens:
            # Check if this is a key=value token (contains operator)
            operator_match = cls._find_operator_in_token(token)
            
            if operator_match:
                key, operator, value = operator_match
                
                # Add key
                full_list.append({
                    "text": key,
                    "was_quoted": False,
                    "is_excluded": False
                })
                
                # Add operator
                full_list.append({
                    "text": operator,
                    "was_quoted": False,
                    "is_excluded": True
                })
                
                # Add value (handle quotes)
                was_quoted = False
                if value and ((value.startswith('"') and value.endswith('"')) or 
                             (value.startswith("'") and value.endswith("'"))):
                    was_quoted = True
                    value = value[1:-1]  # Strip quotes
                
                full_list.append({
                    "text": value,
                    "was_quoted": was_quoted,
                    "is_excluded": False
                })
            else:
                # Regular token (not key=value)
                text = token
                was_quoted = False
                
                # Handle quotes
                if text and ((text.startswith('"') and text.endswith('"')) or 
                           (text.startswith("'") and text.endswith("'"))):
                    was_quoted = True
                    text = text[1:-1]  # Strip quotes
                
                full_list.append({
                    "text": text,
                    "was_quoted": was_quoted,
                    "is_excluded": cls._is_excluded(text)
                })
        
        return full_list
    
    @classmethod
    def _build_shortlist(cls, full_list: List[Dict[str, Any]]) -> List[Token]:
        """
        Build short-listed array excluding operators/keywords.
        
        For each non-excluded token:
        - Check if next token is an operator → set operator_after
        - Assign 0-indexed position in short-list
        - Create Token object
        
        Example:
            Input: [
                {"text": "vision", "was_quoted": False, "is_excluded": False},
                {"text": "=", "was_quoted": False, "is_excluded": True},
                {"text": "text", "was_quoted": True, "is_excluded": False},
            ]
            Output: [
                Token(text="vision", position=0, operator_after=Operator.EQUAL),
                Token(text="text", position=1, was_quoted=True),
            ]
        """
        tokens = []
        position = 0
        
        for i, item in enumerate(full_list):
            if not item["is_excluded"]:
                # Check if next item is an operator
                operator_after = None
                if i + 1 < len(full_list):
                    next_item = full_list[i + 1]
                    if next_item["is_excluded"] and next_item["text"] in [op.value for op in Operator]:
                        operator_after = Operator(next_item["text"])
                
                tokens.append(Token(
                    text=item["text"],
                    position=position,
                    was_quoted=item["was_quoted"],
                    operator_after=operator_after
                ))
                position += 1
        
        return tokens
    
    @classmethod
    def _find_operator_in_token(cls, token: str) -> tuple[str, str, str] | None:
        """
        Find operator in token and split into key, operator, value.
        
        Returns:
            Tuple of (key, operator, value) or None if no operator found
        """
        # Check operators in order of precedence (longer operators first)
        # Use Operator enum values to ensure consistency
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
        
        return None
    
    @classmethod
    def _is_excluded(cls, text: str) -> bool:
        """
        Check if a token should be excluded from short-list.
        
        Excluded:
        - Operators: Uses Operator enum values (=, >, <, >=, <=, !=)
        - Query keywords: Uses QueryKeyword enum values (where, and, or) - case-insensitive
        - Brackets: Uses Bracket enum values ((, ), [, ])
        """
        if not text:
            return False
        
        # Operators - use Operator enum values
        operator_values = [op.value for op in Operator]
        if text in operator_values:
            return True
        
        # Query keywords (case-insensitive) - use QueryKeyword enum values
        query_keyword_values = [kw.value for kw in QueryKeyword]
        if text.lower() in query_keyword_values:
            return True
        
        # Brackets - use Bracket enum values
        bracket_values = [bracket.value for bracket in Bracket]
        if text in bracket_values:
            return True
        
        return False