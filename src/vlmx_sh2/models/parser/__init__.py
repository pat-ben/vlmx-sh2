"""
Parser models.

Provides stage-based models for the parsing pipeline:
- Token: Output from tokenizer (text processing with position metadata)
- ClassifiedToken: Output from classifier (structural classification)  
- RecognizedToken: Output from recognizer (semantic classification)
- ParseResult: Complete parsing result
- Enums: All parser-related enums
"""

from vlmx_sh2.enums import Operator, QueryKeyword, Bracket, TokenClass, TokenType, ValueContext
from .token import Token
from .classified_token import ClassifiedToken
from .recognized_token import RecognizedToken
from .parse_result import ParseResult
from .parsed_command import ParsedCommand
from .split_result import SplitResult

__all__ = [
    # Enums
    "Operator",
    "QueryKeyword",
    "Bracket",
    "TokenClass",
    "TokenType",
    "ValueContext",
    
    # Models
    "Token",
    "ClassifiedToken", 
    "RecognizedToken",
    "SplitResult",
    "ParseResult",
    "ParsedCommand",
]