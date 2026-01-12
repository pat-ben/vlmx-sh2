"""
Parser package.

Provides modular parsing functionality with clean separation of concerns:
- Tokenization: Breaking input into tokens
- Recognition: Matching tokens to known words
- Extraction: Extracting values and fields
- Parsing: Orchestrating the complete parsing process

The main entry point is VLMXParser, which coordinates all parsing steps.
"""

from .parser import VLMXParser
from .tokenizer import Tokenizer
from .recognizer import WordRecognizer
from ..words.macros import expand_macros

__all__ = [
    'VLMXParser',
    'Tokenizer',
    'WordRecognizer',
    'expand_macros',
]