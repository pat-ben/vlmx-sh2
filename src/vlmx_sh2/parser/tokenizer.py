"""
Tokenizer for parser.

A three-stage tokenization system that extracts and organizes tokens with metadata.
The tokenizer's sole responsibility is text processing - no semantic classification.
"""

from typing import List, Dict, Any, Tuple, NamedTuple
from ..models.parser import Token
from vlmx_sh2.enums import Operator, QueryKeyword, Bracket


class TokenizerResult(NamedTuple):
    """Output from tokenizer with separate token lists."""
    command_tokens: List[Token]  # Tokens outside [ ]
    filter_tokens: List[Token]   # Tokens inside [ ] (excluding brackets)
    has_filter: bool             # Quick check if filter exists


class TokenizerError(Exception):
    """Raised when tokenization fails."""
    pass


class Tokenizer:
    """Clean three-stage tokenizer for input."""
    
    @classmethod
    def tokenize(cls, text: str) -> TokenizerResult:
        """
        Tokenize input text into separate command and filter token lists.
        
        Three-stage process:
        1. Extract quoted strings
        2. Build full ordered list with metadata
        3. Split into command and filter tokens
        
        Args:
            text: Input text to tokenize
            
        Returns:
            TokenizerResult with separate command and filter token lists
        """
        # Stage 1: Extract quoted strings (unchanged)
        raw_tokens = cls._extract_quoted_strings(text)
        
        # Stage 2: Build full ordered list (unchanged)
        full_list = cls._build_full_list(raw_tokens)
        
        # Stage 3a: Split into command and filter portions (NEW)
        command_full_list, filter_full_list = cls._split_command_and_filter(full_list)
        
        # Stage 3b: Build command tokens
        command_tokens = cls._build_command_tokens(command_full_list)
        
        # Stage 3c: Build filter tokens
        filter_tokens = cls._build_filter_tokens(filter_full_list)
        
        return TokenizerResult(
            command_tokens=command_tokens,
            filter_tokens=filter_tokens,
            has_filter=len(filter_tokens) > 0
        )
    
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
    def _split_command_and_filter(
        cls, 
        full_list: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Split full_list into command and filter portions.
        
        Command: Everything OUTSIDE [ ]
        Filter: Everything INSIDE [ ] (excluding the [ ] brackets themselves)
        
        Returns:
            Tuple of (command_full_list, filter_full_list)
        """
        command_full_list = []
        filter_full_list = []
        
        inside_filter = False
        bracket_start = None
        
        for i, item in enumerate(full_list):
            token_text = item["text"]
            
            if token_text == "[":
                if bracket_start is not None:
                    raise TokenizerError("Nested [ brackets are not supported")
                bracket_start = i
                inside_filter = True
                # Don't include the [ itself
                
            elif token_text == "]":
                if not inside_filter:
                    raise TokenizerError("Found ] without matching [")
                inside_filter = False
                # Don't include the ] itself
                
            elif inside_filter:
                # Inside filter - add to filter list
                filter_full_list.append(item)
                
            else:
                # Outside filter - add to command list
                command_full_list.append(item)
        
        if inside_filter:
            raise TokenizerError("Found [ without matching ]")
        
        return command_full_list, filter_full_list
    
    @classmethod
    def _build_command_tokens(
        cls, 
        full_list: List[Dict[str, Any]]
    ) -> List[Token]:
        """
        Build command tokens from command full list:
        - Exclude operators and keywords
        - Keep position, was_quoted, operator_after metadata
        """
        # Keep existing _build_shortlist implementation exactly as is
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
    def _build_filter_tokens(
        cls, 
        filter_full_list: List[Dict[str, Any]]
    ) -> List[Token]:
        """
        Build filter tokens from filter full list.
        
        DIFFERENT from command tokens:
        - KEEP operators (=, <, >, etc.) as separate tokens
        - KEEP keywords (and, or) as separate tokens
        - KEEP parentheses ( ) as separate tokens
        - [ ] already excluded in split
        - Keep ALL metadata: position, was_quoted
        - operator_after not needed (operators are explicit)
        """
        tokens = []
        position = 0
        
        for item in filter_full_list:
            tokens.append(Token(
                text=item["text"],
                position=position,
                was_quoted=item["was_quoted"],
                operator_after=None  # Not needed - operators are explicit tokens
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