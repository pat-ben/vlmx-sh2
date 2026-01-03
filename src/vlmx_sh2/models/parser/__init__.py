"""
Parser models.

Provides stage-based models for the parsing pipeline:
- Token: Output from tokenizer (text processing only)
- RecognizedToken: Output from recognizer (adds classification)
- ParseResult: Complete parsing result
- Enums: All parser-related enums
"""

from .enums import Operator, QueryKeyword, Bracket, TokenType, ValueContext
from .token import Token
from .recognized_token import RecognizedToken
from .parse_result import ParseResult
from .parsed_command import ParsedCommand

__all__ = [
    # Enums
    "Operator",
    "QueryKeyword",
    "Bracket",
    "TokenType",
    "ValueContext",
    
    # Models
    "Token",
    "RecognizedToken",
    "ParseResult",
    "ParsedCommand",
]