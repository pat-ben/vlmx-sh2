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
    
    # Class-level constants for excluded values
    _OPERATOR_VALUES = {op.value for op in Operator}
    _QUERY_KEYWORD_VALUES = {kw.value for kw in QueryKeyword}
    _BRACKET_VALUES = {bracket.value for bracket in Bracket}
    _QUOTE_CHARS = {'\"', "'"}
    
    # Pre-sorted operators by length (longest first) for efficient detection
    _OPERATORS_BY_LENGTH = sorted([op.value for op in Operator], key=len, reverse=True)

    # =============================================================================
    # 1. Public API (The Entry Point)
    # =============================================================================

    @classmethod
    def tokenize(cls, text: str) -> TokenizerResult:
        """
        Tokenize input text into separate command and filter token lists.
        
        Three-stage process:
        1. Extract raw token blocks
        2. Build full ordered list with metadata  
        3. Split into command and filter tokens
        """
        raw_tokens = cls._extract_token_blocks(text)
        full_list = cls._build_full_list(raw_tokens)
        command_full_list, filter_full_list = cls._split_command_and_filter(full_list)
        command_tokens = cls._build_command_tokens(command_full_list)
        filter_tokens = cls._build_filter_tokens(filter_full_list)
        
        return TokenizerResult(
            command_tokens=command_tokens,
            filter_tokens=filter_tokens,
            has_filter=len(filter_tokens) > 0
        )

    # =============================================================================
    # 2. Stage 1: Block Extraction (Lexing)
    # =============================================================================
    
    @classmethod
    def _extract_token_blocks(cls, text: str) -> List[str]:
        """Extract token blocks from text, treating quoted strings as single tokens."""
        tokens = []
        i = 0
        current_token = ""
        in_quotes = False
        quote_char = None
        
        while i < len(text):
            char = text[i]
            
            if not in_quotes:
                if char in cls._QUOTE_CHARS:
                    in_quotes = True
                    quote_char = char
                    current_token += char
                elif char.isspace():
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                elif char in cls._BRACKET_VALUES:
                    if current_token.strip():
                        tokens.append(current_token.strip())
                        current_token = ""
                    tokens.append(char)
                else:
                    current_token += char
            else:
                current_token += char
                if char == quote_char:
                    in_quotes = False
                    quote_char = None
            
            i += 1
        
        if current_token.strip():
            tokens.append(current_token.strip())
        
        return tokens

    @classmethod
    def _strip_quotes(cls, text: str) -> Tuple[str, bool]:
        """
        Strip quotes from a text and return whether it was quoted.

        Args:
            text: Input text that may have quotes

        Returns:
            Tuple of (stripped_text, was_quoted)
        """
        if not text:
            return text, False

        if ((text.startswith('"') and text.endswith('"')) or
                (text.startswith("'") and text.endswith("'"))):
            return text[1:-1], True
        return text, False

    # =============================================================================
    # 3. Stage 2: List Building & Triplet Handling
    # =============================================================================

    @classmethod
    def _build_full_list(cls, raw_tokens: List[str]) -> List[Dict[str, Any]]:
        """
        Build full ordered list with ALL elements and metadata.
        
        Separates key=value into ["key", "=", "value"] and handles quotes.
        """
        full_list = []
        
        for token in raw_tokens:
            operator_match = cls._find_operator_in_token(token)
            
            if operator_match:
                key, operator, value = operator_match
                cls._add_operator_triplet(full_list, key, operator, value)
            else:
                text, was_quoted = cls._strip_quotes(token)
                full_list.append({
                    "text": text,
                    "was_quoted": was_quoted,
                    "is_excluded": cls._is_excluded(text)
                })
        
        return full_list

    @classmethod
    def _find_operator_in_token(cls, token: str) -> tuple[str, str, str] | None:
        """
        Find operator in token and split into key, operator, value.

        Returns:
            Tuple of (key, operator, value) or None if no operator found
        """
        for operator in cls._OPERATORS_BY_LENGTH:
            if operator in token:
                parts = token.split(operator, 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    return key, operator, value

        return None

    @classmethod
    def _add_operator_triplet(cls, full_list: List[Dict[str, Any]], key: str, operator: str, value: str) -> None:
        """
        Add key, operator, and value as separate tokens to full_list.

        Args:
            full_list: List to append tokens to
            key: The key part before operator
            operator: The operator (=, >, <, etc.)
            value: The value part after operator (quotes will be stripped)
        """
        full_list.append({"text": key, "was_quoted": False, "is_excluded": False})
        full_list.append({"text": operator, "was_quoted": False, "is_excluded": True})

        value_text, was_quoted = cls._strip_quotes(value)
        full_list.append({"text": value_text, "was_quoted": was_quoted, "is_excluded": False})

    @classmethod
    def _is_excluded(cls, text: str) -> bool:
        """
        Check if a token should be excluded from short-list.

        Excluded:
        - Operators, Query keywords (case-insensitive), Brackets
        """
        if not text:
            return False

        return (text in cls._OPERATOR_VALUES or
                text.lower() in cls._QUERY_KEYWORD_VALUES or
                text in cls._BRACKET_VALUES)

    # =============================================================================
    # 4. Stage 3: Categorization & Filtering
    # =============================================================================

    @classmethod
    def _split_command_and_filter(
        cls, 
        full_list: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Split full_list into command and filter portions using index-based approach."""
        # Find bracket positions first
        bracket_start = None
        bracket_end = None
        
        for i, item in enumerate(full_list):
            if item["text"] == "[":
                if bracket_start is not None:
                    raise TokenizerError("Nested [ brackets are not supported")
                bracket_start = i
            elif item["text"] == "]":
                if bracket_start is None:
                    raise TokenizerError("Found ] without matching [")
                bracket_end = i
                break  # Only support one filter section
        
        # Validate bracket pairing
        if bracket_start is not None and bracket_end is None:
            raise TokenizerError("Found [ without matching ]")
        
        # Slice based on bracket positions
        if bracket_start is not None and bracket_end is not None:
            # Command: everything before [ and after ]
            command_full_list = full_list[:bracket_start] + full_list[bracket_end + 1:]
            # Filter: everything between [ and ] (excluding brackets)
            filter_full_list = full_list[bracket_start + 1:bracket_end]
        else:
            # No brackets - everything is command
            command_full_list = full_list[:]
            filter_full_list = []
        
        return command_full_list, filter_full_list

    @classmethod
    def _build_tokens_from_list(
        cls, 
        full_list: List[Dict[str, Any]], 
        include_excluded: bool
    ) -> List[Token]:
        """Build tokens from full list with unified logic."""
        tokens = []
        position = 0
        
        for i, item in enumerate(full_list):
            if include_excluded or not item["is_excluded"]:
                operator_after = None
                if not include_excluded and i + 1 < len(full_list):
                    next_item = full_list[i + 1]
                    if next_item["is_excluded"] and next_item["text"] in cls._OPERATOR_VALUES:
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
    def _build_command_tokens(cls, full_list: List[Dict[str, Any]]) -> List[Token]:
        """Build command tokens - exclude operators and keywords."""
        return cls._build_tokens_from_list(full_list, include_excluded=False)

    @classmethod
    def _build_filter_tokens(cls, full_list: List[Dict[str, Any]]) -> List[Token]:
        """Build filter tokens - include all tokens."""
        return cls._build_tokens_from_list(full_list, include_excluded=True)