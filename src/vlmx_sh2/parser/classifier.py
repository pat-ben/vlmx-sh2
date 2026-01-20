"""
PARSING STAGE 2/8: Classification

Structural classification of tokens into TEXT, OPERATOR, and BRACKET categories.
"""

from typing import List
from ..models.parser import Token, ClassifiedToken
from ..models.validation import ValidationContext
from vlmx_sh2.enums import Operator, Bracket, TokenClass, IssueStage
from ..diagnostics import Validator


class Classifier:
    """Structural classification of tokens into TEXT, OPERATOR, and BRACKET categories."""    

    # =============================================================================
    # CLASS CONSTANTS
    # =============================================================================
    _QUOTE_CHARS = {'"', "'"}
    _QUERY_SYMBOLS = {"&": "and", "&&": "and", "|": "or", "||": "or"}
    _BRACKET_VALUES = {bracket.value for bracket in Bracket}
    _OPERATOR_VALUES = {op.value for op in Operator}  # Set for O(1) membership checks    
    
    # =============================================================================
    # PUBLIC API
    # =============================================================================
    @classmethod
    def classify(cls, tokens: List[Token], context: ValidationContext) -> List[ClassifiedToken]:
        """Classify tokens structurally."""
        classified_tokens = []
        
        for token in tokens:
            classified_token = cls._classify_single_token(token)
            classified_tokens.append(classified_token)
        
        # Post-classification validation
        # Validates structural issues (unclosed quotes, mismatched brackets)
        # on CLASSIFIED tokens (non-blocking, collects all errors)
        Validator.validate_tokens(IssueStage.CLASSIFIER, context, tokens=classified_tokens)
        
        return classified_tokens

    # =============================================================================
    # PRIVATE HELPERS
    # =============================================================================
    @classmethod
    def _normalize_query_keyword(cls, text: str) -> str:
        """
        Normalize query keyword symbols to their word equivalents.
        
        Converts symbols like & and | to their keyword forms (and, or)
        to ensure consistent handling throughout the parsing pipeline.
        
        Args:
            text: Token text to potentially normalize
            
        Returns:
            Normalized text if it's a query keyword symbol, otherwise original text
            
        Examples:
            >>> Classifier._normalize_query_keyword("&")
            "and"
            >>> Classifier._normalize_query_keyword("|")
            "or"
            >>> Classifier._normalize_query_keyword("create")
            "create"
        """
        return cls._QUERY_SYMBOLS.get(text, text)

    @classmethod
    def _classify_single_token(cls, token: Token) -> ClassifiedToken:
        """Classify single token as OPERATOR, BRACKET, or TEXT."""
        text = token.text
        
        # Normalize query keyword symbols to words before classification
        normalized_text = cls._normalize_query_keyword(text)
        
        # Check for operators using normalized text
        if normalized_text in cls._OPERATOR_VALUES:
            return cls._create_classified_token(
                token, 
                TokenClass.OPERATOR,
                text=normalized_text,
                operator=Operator(normalized_text)
                # was_quoted intentionally omitted (defaults to None)
            )
        
        # Check for brackets using normalized text
        if normalized_text in cls._BRACKET_VALUES:
            return cls._create_classified_token(
                token,
                TokenClass.BRACKET,
                text=normalized_text,
                bracket=Bracket(normalized_text)
                # was_quoted intentionally omitted (defaults to None)
            )
        
        # Check if original text is quoted (and strip quotes if so)
        is_quoted = cls._is_quoted(text)
        stripped_text = text[1:-1] if is_quoted else normalized_text
        
        # All text uses TEXT class (was_quoted indicates if quoted)
        return cls._create_classified_token(
            token,
            TokenClass.TEXT,
            text=stripped_text,
            was_quoted=is_quoted
        )

    @classmethod
    def _create_classified_token(
        cls, 
        token: Token, 
        token_class: TokenClass,
        text: str | None = None,
        **extra_fields
    ) -> ClassifiedToken:
        """Create ClassifiedToken with common fields pre-filled."""
        return ClassifiedToken(
            text=text if text is not None else token.text,
            char_start=token.char_start,
            char_end=token.char_end,
            token_index=token.token_index,
            token_class=token_class,
            **extra_fields
        )

    @staticmethod
    def _is_quoted(text: str) -> bool:
        """Check if text is properly quoted."""
        if len(text) < 2:
            return False
        
        first, last = text[0], text[-1]
        return first == last and first in ('"', "'")