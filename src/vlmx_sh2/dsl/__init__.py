"""
DSL Words Package.

This package handles the complete word registry system for the VLMX DSL,
providing a unified interface for word lookup and management. The registry
combines auto-generated entity and field dsl with manual action dsl.

Public API:
    WORD_REGISTRY: Complete word registry dictionary
    get_word: Get a word by its ID
    get_all_words: Get all registered dsl
    get_words_by_type: Get dsl filtered by type
"""

from .registry import WORD_REGISTRY, get_word, get_all_words, get_words_by_type
from ..models.words import WordType

__all__ = [
    'WORD_REGISTRY',
    'get_word', 
    'get_all_words',
    'get_words_by_type',
    'WordType',
]