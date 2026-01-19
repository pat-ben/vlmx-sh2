"""

PARSING STAGE 2/6: Classification

Performs structural classification of tokens.
Converts Token objects to ClassifiedToken objects by:
- Identifying operators and brackets
- Stripping quotes and marking quoted text
- Marking remaining tokens as generic text

Does NOT perform semantic analysis (that's Recognizer's job).

"""

from typing import List
from ..models.parser import Token, ClassifiedToken
from ..models.validation import ValidationContext
from vlmx_sh2.enums import Operator, Bracket, TokenClass, IssueStage
from ..diagnostics import Validator


class Classifier:
    """
    PARSING STAGE 2/6: Classification
    
    Performs structural classification of tokens.
    Converts Token objects to ClassifiedToken objects by:
    - Identifying operators and brackets
    - Stripping quotes and marking quoted text
    - Marking remaining tokens as generic text
    
    Does NOT perform semantic analysis (that's Recognizer's job).
    """    

    # Class-level constants for efficient membership checks
    _QUOTE_CHARS = {'"', "'"}
    _BRACKET_VALUES = {bracket.value for bracket in Bracket}
    _OPERATOR_VALUES = {op.value for op in Operator}  # Set for O(1) membership checks

    @classmethod
    def classify(cls, tokens: List[Token], context: ValidationContext) -> List[ClassifiedToken]:
        """
        Classify tokens structurally.
        
        Args:
            tokens: List of Token objects from tokenizer
            context: ValidationContext for error reporting
            
        Returns:
            List of ClassifiedToken objects with structural classification
        """
        classified_tokens = []
        
        for token in tokens:
            classified_token = cls._classify_single_token(token)
            classified_tokens.append(classified_token)
        
        # Token-level validation (post-classification)
        # - Validates structural issues that become apparent after classification
        # - Non-blocking by default (collect ALL errors)
        # - Examples: unclosed quotes, mismatched brackets
        # - Validates the CLASSIFIED tokens, not the input tokens
        Validator.validate_tokens(IssueStage.CLASSIFIER, context, tokens=classified_tokens)
        
        return classified_tokens

    @classmethod
    def _classify_single_token(cls, token: Token) -> ClassifiedToken:
        """
        Classify a single token structurally.
        
        Classification rules:
        1. If text matches Operator enum values -> TokenClass.OPERATOR
        2. If text matches Bracket enum values -> TokenClass.BRACKET
        3. If text starts and ends with quotes -> TokenClass.QUOTED_TEXT (strip quotes)
        4. Otherwise -> TokenClass.TEXT
        
        Args:
            token: Token to classify
            
        Returns:
            ClassifiedToken with structural classification
        """
        text = token.text
        
        # Check for operators
        if text in cls._OPERATOR_VALUES:
            return ClassifiedToken(
                text=text,
                char_start=token.char_start,
                char_end=token.char_end,
                token_index=token.token_index,
                token_class=TokenClass.OPERATOR,
                operator=Operator(text)
            )
        
        # Check for brackets
        if text in cls._BRACKET_VALUES:
            return ClassifiedToken(
                text=text,
                char_start=token.char_start,
                char_end=token.char_end,
                token_index=token.token_index,
                token_class=TokenClass.BRACKET
            )
        
        # Check for quoted text
        if cls._is_quoted(text):
            return ClassifiedToken(
                text=text[1:-1],  # Strip quotes from text
                char_start=token.char_start,
                char_end=token.char_end,
                token_index=token.token_index,
                token_class=TokenClass.QUOTED_TEXT,
                was_quoted=True
            )
        
        # Default case: generic text
        return ClassifiedToken(
            text=text,
            char_start=token.char_start,
            char_end=token.char_end,
            token_index=token.token_index,
            token_class=TokenClass.TEXT
        )

    @staticmethod
    def _is_quoted(text: str) -> bool:
        """
        Check if text is properly quoted.
        
        Returns True if text starts and ends with matching quotes (" or ').
        """
        if len(text) < 2:
            return False
        
        return ((text.startswith('"') and text.endswith('"')) or 
                (text.startswith("'") and text.endswith("'")))