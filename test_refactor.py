#!/usr/bin/env python3
"""
Test script for the refactored VLMX-SH2 parser system.
"""

import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.dsl.parser import VLMXParser
from vlmx_sh2.dsl.words import expand_shortcuts, SHORTCUTS
from vlmx_sh2.models.context import Context

def test_shortcuts():
    """Test the shortcut expansion system."""
    print("=== Testing Shortcuts ===")
    
    test_cases = [
        "cc ACME entity=SA currency=EUR",
        "sb vision",
        "ub mission='Our new mission'",
        "show company name",
        "unknown_shortcut test"
    ]
    
    for test_input in test_cases:
        expanded = expand_shortcuts(test_input)
        print(f"Input: '{test_input}'")
        print(f"Expanded: '{expanded}'")
        print()

def test_parser():
    """Test the simplified parser."""
    print("=== Testing Parser ===")
    
    parser = VLMXParser()
    
    test_cases = [
        "create company ACME entity=SA currency=EUR",
        "cc TechCorp entity=LLC",
        "add brand vision='To revolutionize technology'",
        "show company name",
        "update metadata category=SaaS",
        "delete brand mission",
        "cd ACME",
        "invalid command xyz"
    ]
    
    for test_input in test_cases:
        print(f"Parsing: '{test_input}'")
        try:
            result = parser.parse(test_input)
            
            print(f"  Valid: {result.is_valid}")
            print(f"  Action words: {[w.id for w in result.action_words]}")
            print(f"  Entity words: {[w.id for w in result.entity_words]}")
            print(f"  Attributes: {result.attribute_values}")
            print(f"  Entity values: {result.entity_values}")
            print(f"  Has handler: {result.action_handler is not None}")
            print(f"  Has entity model: {result.entity_model is not None}")
            
            if result.errors:
                print(f"  Errors: {result.errors}")
            
            if result.suggestions:
                print(f"  Suggestions: {result.suggestions}")
            
        except Exception as e:
            print(f"  Error: {str(e)}")
        
        print()

async def test_execution():
    """Test handler execution (if handlers are implemented)."""
    print("=== Testing Execution ===")
    
    parser = VLMXParser()
    context = Context(level=0)  # SYS level
    
    test_cases = [
        "cd ~",  # This should work as navigate_handler exists
        # Other commands would need proper handler implementations
    ]
    
    for test_input in test_cases:
        print(f"Executing: '{test_input}'")
        try:
            result = parser.parse(test_input)
            
            if result.is_valid and result.action_handler:
                # Try to execute if we have a real handler
                if hasattr(result.action_handler, '__call__'):
                    execution_result = await parser.execute_parsed_command(result, context)
                    print(f"  Execution result: {execution_result}")
                else:
                    print(f"  Handler is not callable: {type(result.action_handler)}")
            else:
                print(f"  Cannot execute: valid={result.is_valid}, handler={result.action_handler is not None}")
        
        except Exception as e:
            print(f"  Execution error: {str(e)}")
        
        print()

def test_word_registry():
    """Test the word registry."""
    print("=== Testing Word Registry ===")
    
    from vlmx_sh2.dsl.words import get_all_words, get_word
    
    words = get_all_words()
    print(f"Total words in registry: {len(words)}")
    
    # Test some specific words
    test_word_ids = ['create', 'company', 'name', 'currency', 'cd']
    
    for word_id in test_word_ids:
        word = get_word(word_id)
        if word:
            print(f"  {word_id}: {word.word_type.value}, aliases: {word.aliases}")
        else:
            print(f"  {word_id}: NOT FOUND")
    
    print()

def main():
    """Run all tests."""
    print("VLMX-SH2 Refactored Parser Test")
    print("=" * 40)
    print()
    
    try:
        test_word_registry()
        test_shortcuts()
        test_parser()
        
        # Test execution (async)
        asyncio.run(test_execution())
        
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("All tests completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())