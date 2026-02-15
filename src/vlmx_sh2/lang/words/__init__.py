"""
DSL Words Package.

This package handles the complete word registry system for the VLMX DSL,
providing a unified interface for word lookup and management. The registry
combines auto-generated entity and field words with manual action words.

Public API:
    WORD_REGISTRY: Complete word registry dictionary
    get_word: Get a word by its ID
    get_all_words: Get all registered words
    get_words_by_type: Get words filtered by type
"""

from ...core.models.words import WordType
from .registry import WORD_REGISTRY, get_all_words, get_word, get_words_by_type

__all__ = [
    "WORD_REGISTRY",
    "get_word",
    "get_all_words",
    "get_words_by_type",
    "WordType",
]
