"""
Parser models.

Provides stage-based models for the parsing pipeline:
- Token: Output from tokenizer (text processing with position metadata)
- ClassifiedToken: Output from classifier (structural classification)  
- RecognizedToken: Output from recognizer (semantic classification)
- ParseResult: Complete parsing result
- Enums: All parser-related enums
"""

from vlmx_sh2.core.enums import Operator, QueryWord, Bracket, TokenClass, TokenType, ValueContext
from .token import Token
from .classification import ClassifiedToken
from .recognition import RecognizedToken
from .interpretation import InterpretedToken
from .parsing import ParseResult
from .command import ParsedCommand
from .splitting import SplitResult
from .tokens_result import TokensResult

__all__ = [
    # Enums
    "Operator",
    "QueryWord",
    "Bracket",
    "TokenClass",
    "TokenType",
    "ValueContext",
    
    # Models
    "Token",
    "ClassifiedToken", 
    "RecognizedToken",
    "InterpretedToken",
    "SplitResult",
    "ParseResult",
    "ParsedCommand",
    "TokensResult",
    
]