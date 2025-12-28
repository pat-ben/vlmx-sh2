#!/usr/bin/env python3
"""
Simple edge case testing for the improved tokenizer without unicode chars.
"""

import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.parser.tokenizer import Tokenizer
from vlmx_sh2.models.parser import ParsedToken, TokenType


def test_empty_values():
    """Test empty value handling"""
    print("=== Empty Value Tests ===")
    
    # Test empty quoted value
    input_text = 'key=""'
    tokens = Tokenizer.tokenize(input_text)
    print(f"Input: '{input_text}'")
    print("Tokens:", [(t.text, str(t.token_type)) for t in tokens])
    assert len(tokens) == 2
    assert tokens[0].text == "key"
    assert tokens[1].text == ""
    assert tokens[1].token_type == TokenType.VALUE
    print("PASSED")
    
    # Test key with no value
    input_text = 'key='
    tokens = Tokenizer.tokenize(input_text)
    print(f"Input: '{input_text}'")
    print("Tokens:", [(t.text, str(t.token_type)) for t in tokens])
    assert len(tokens) == 2
    assert tokens[0].text == "key"
    assert tokens[1].text == ""
    assert tokens[1].token_type == TokenType.VALUE
    print("PASSED")


def test_operator_edge_cases():
    """Test edge case operators"""
    print("\n=== Operator Edge Cases ===")
    
    # Test double equals
    result = Tokenizer._parse_attribute_token("key==value")
    print(f"key==value -> {result}")
    assert result == ("key", "=", "=value")
    print("PASSED")
    
    # Test comparison operators
    result = Tokenizer._parse_attribute_token("key>=10")
    print(f"key>=10 -> {result}")
    assert result == ("key", ">=", "10")
    print("PASSED")


def test_quote_safety():
    """Test quote mismatch handling"""
    print("\n=== Quote Safety Tests ===")
    
    # Test very long unclosed quote (should be limited)
    long_tokens = ['vision="start'] + [f'word{i}' for i in range(30)]
    result = Tokenizer._extract_quoted_value(long_tokens, 0)
    print(f"Long unclosed quote test: extracted {len(result[0].split())} words")
    print(f"Tokens consumed: {result[1]}")
    
    # Should not consume all 30+ tokens due to safety limit
    assert result[1] <= 21, f"Should limit tokens consumed, got {result[1]}"
    print("PASSED")


def test_complex_scenario():
    """Test complex real-world scenario"""
    print("\n=== Complex Scenario Test ===")
    
    input_text = 'create company name="ACME Corp" vision="Build future" entity= revenue>=1000'
    tokens = Tokenizer.tokenize(input_text)
    
    print(f"Input: '{input_text}'")
    print("Tokens:")
    for i, token in enumerate(tokens):
        print(f"  {i}: '{token.text}' ({token.token_type})")
    
    # Should have reasonable number of tokens
    assert len(tokens) >= 8, f"Expected at least 8 tokens, got {len(tokens)}"
    
    # Check for quoted company name (now with proper key=value format)
    company_tokens = [t for t in tokens if "ACME Corp" in t.text]
    assert len(company_tokens) == 1, "Should find ACME Corp token"
    
    # Check for quoted vision
    vision_tokens = [t for t in tokens if "Build future" in t.text]
    assert len(vision_tokens) == 1, "Should find Build future token"
    
    # Check for empty entity value
    empty_tokens = [t for t in tokens if t.text == "" and t.token_type == TokenType.VALUE]
    assert len(empty_tokens) >= 1, "Should handle empty entity value"
    
    print("PASSED")


def test_regression():
    """Test original cases still work"""
    print("\n=== Regression Tests ===")
    
    # Original simple case
    tokens = Tokenizer.tokenize("create company ACME")
    assert len(tokens) == 3
    print("Simple command: PASSED")
    
    # Original quoted case
    tokens = Tokenizer.tokenize('vision="Build the future"')
    assert len(tokens) == 2
    assert tokens[1].text == "Build the future"
    assert tokens[1].token_type == TokenType.VALUE
    print("Quoted value: PASSED")
    
    # Original key=value case
    tokens = Tokenizer.tokenize("entity=SA currency=EUR")
    assert len(tokens) == 4
    assert tokens[1].text == "SA" and tokens[1].token_type == TokenType.VALUE
    assert tokens[3].text == "EUR" and tokens[3].token_type == TokenType.VALUE
    print("Key=value: PASSED")


if __name__ == "__main__":
    try:
        test_empty_values()
        test_operator_edge_cases()
        test_quote_safety()
        test_complex_scenario()
        test_regression()
        print("\n" + "="*50)
        print("ALL TESTS PASSED! Tokenizer improvements working correctly.")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()