#!/usr/bin/env python3
"""
Debug the delete command parsing.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser

def debug_delete_parsing():
    """Debug how 'delete brand vision' is being parsed."""
    parser = VLMXParser()
    
    test_command = "delete brand vision"
    print(f"Testing: '{test_command}'")
    
    result = parser.parse(test_command)
    
    print(f"\nParse Results:")
    print(f"  Valid: {result.is_valid}")
    print(f"  Input text: '{result.input_text}'")
    
    print(f"\nTokens:")
    for i, token in enumerate(result.tokens):
        print(f"  {i}: '{token.text}' -> {token.token_type} (word: {token.word.id if token.word else None})")
    
    print(f"\nRecognized Words:")
    for word in result.recognized_words:
        print(f"  {word.id} ({word.word_type.value})")
    
    print(f"\nExtracted Data:")
    print(f"  Action words: {[w.id for w in result.action_words]}")
    print(f"  Entity words: {[w.id for w in result.entity_words]}")
    print(f"  Attribute words: {[w.id for w in result.attribute_words]}")
    print(f"  Entity values: {result.entity_values}")
    print(f"  Attribute values: {result.attribute_values}")
    
    print(f"\nHandler Info:")
    print(f"  Has handler: {result.action_handler is not None}")
    print(f"  Has entity model: {result.entity_model is not None}")
    
    if result.errors:
        print(f"\nErrors: {result.errors}")
    
    if result.suggestions:
        print(f"\nSuggestions: {result.suggestions}")

if __name__ == "__main__":
    debug_delete_parsing()