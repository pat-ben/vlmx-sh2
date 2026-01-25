"""
PARSING STAGE 2/7: Classification

Structural classification of tokens into TEXT, OPERATOR, and BRACKET categories.
This stage does not look at semantic, only structure.
"""

from typing import List
from ..models.parser import Token, ClassifiedToken
from ..models.validation import ValidationContext
from vlmx_sh2.enums import Operator, Bracket, TokenClass, IssueStage
from ..diagnostics import Validator
from .tokenizer import Tokenizer
from .tokenizer import BRACKET_VALUES


class Classifier:
    """Structural classification of tokens into TEXT, OPERATOR, and BRACKET categories."""    

    # =============================================================================
    # CLASS CONSTANTS
    # =============================================================================

    _QUERY_SYMBOLS = {"&": "and", "&&": "and", "|": "or", "||": "or"}
    _OPERATOR_VALUES = {op.value for op in Operator}  # Set for membership checks    
    
    # =============================================================================
    # PUBLIC API
    # =============================================================================
    @classmethod
    def classify(cls, tokens: List[Token], context: ValidationContext) -> List[ClassifiedToken]:
        """        
        Converts Token objects to ClassifiedToken objects with structural
        classification (TEXT, OPERATOR, BRACKET). Strips quotes and unescapes
        escaped quotes for TEXT tokens.
        
        Args:
            tokens: List of Token objects from tokenizer
            context: ValidationContext for error reporting
            
        Returns:
            List of ClassifiedToken objects with structural classification
        """
        # Classify all tokens
        classified_tokens = [cls._classify_single_token(token) for token in tokens]
        
        # Validates structural issues (unclosed quotes, mismatched brackets)
        Validator.validate_tokens(IssueStage.CLASSIFIER, context, tokens=classified_tokens)
        
        return classified_tokens

    # =============================================================================
    # PRIVATE HELPERS
    # =============================================================================
    @classmethod
    def _normalize_query_symbol(cls, text: str) -> str:
        """
        Normalize query symbols to their word equivalents.
        
        Converts symbols like & and | to their keyword forms (and, or)
        to ensure consistent handling throughout the parsing pipeline.

        """
        return cls._QUERY_SYMBOLS.get(text, text)

    @staticmethod
    def _unescape_quotes(text: str) -> str:
        """
        Remove backslash escapes from quoted content.       
        """
        return text.replace('\\"', '"').replace("\\'", "'")

    @classmethod
    def _classify_single_token(cls, token: Token) -> ClassifiedToken:
        """
        Classify single token as OPERATOR, BRACKET, or TEXT.
        
        Processing:
        1. Normalize query symbols (& → and, | → or)
        2. Check if operator or bracket (using normalized text)
        3. For text: check if quoted, strip quotes, unescape escaped quotes
        
        Note: Query keywords (and, or) are classified as TEXT, not OPERATOR.
        They will be recognized as words by the Recognizer stage.
        """
        text = token.text
        
        # Normalize query keyword symbols to words before classification
        normalized_text = cls._normalize_query_symbol(text)
        
        # Check for operators using normalized text
        if normalized_text in cls._OPERATOR_VALUES:
            return cls._create_classified_token(
                text=normalized_text,
                token_class=TokenClass.OPERATOR,
                operator=Operator(normalized_text)
            )
        
        # Check for brackets using normalized text
        if normalized_text in BRACKET_VALUES:
            return cls._create_classified_token(
                text=normalized_text,
                token_class=TokenClass.BRACKET,
                bracket=Bracket(normalized_text)
            )
        
        # Check if original text is quoted using Tokenizer's method
        has_quotes, _ = Tokenizer.has_quotes(text)
        
        # Strip quotes and unescape if quoted
        if has_quotes:
            stripped_text = text[1:-1]  # Remove outer quotes
            stripped_text = cls._unescape_quotes(stripped_text)  # Unescape \" and \'
        else:
            stripped_text = normalized_text
        
        # All text uses TEXT class (was_quoted indicates if quoted)
        return cls._create_classified_token(
            text=stripped_text,
            token_class=TokenClass.TEXT,
            was_quoted=has_quotes
        )

    @classmethod
    def _create_classified_token(
        cls,
        text: str,
        token_class: TokenClass,
        **extra_fields
    ) -> ClassifiedToken:
        """
        Create ClassifiedToken.
        """
        return ClassifiedToken(
            text=text,
            token_class=token_class,
            **extra_fields
        )

