"""
Parser package.

Provides modular parsing functionality with clean separation of concerns:
- Tokenization: Breaking input into tokens
- Recognition: Matching tokens to known words
- Extraction: Extracting values and fields
- Parsing: Orchestrating the complete parsing process

The main entry point is VLMXParser, which coordinates all parsing steps.
"""

from .parser_DEPRECATED import VLMXParser
from .tokenizer_DEPRECATED import Tokenizer
from .recognizer_DEPRECATED import WordRecognizer
from ..words.macros import expand_macros

__all__ = [
    'VLMXParser',
    'Tokenizer',
    'WordRecognizer',
    'expand_macros',
]