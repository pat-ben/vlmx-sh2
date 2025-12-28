#!/usr/bin/env python3
"""
Test script for the refactored tokenizer.
Tests all the specified test cases to ensure the refactoring works correctly.
"""

import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.parser.tokenizer import Tokenizer
from vlmx_sh2.models.parser import ParsedToken, TokenType


def test_case_1_simple_command():
    """Test Case 1: Simple command"""
    print("=== Test Case 1: Simple command ===")
    input_text = "create company ACME"
    tokens = Tokenizer.tokenize(input_text)
    
    expected = [
        ("create", 0, TokenType.UNKNOWN),
        ("company", 7, TokenType.UNKNOWN),
        ("ACME", 15, TokenType.UNKNOWN)
    ]
    
    print(f"Input: '{input_text}'")
    print("Expected tokens:")
    for text, pos, token_type in expected:
        print(f"  - ParsedToken(text='{text}', position={pos}, token_type={token_type})")
    
    print("Actual tokens:")
    for token in tokens:
        print(f"  - ParsedToken(text='{token.text}', position={token.position}, token_type={token.token_type})")
    
    # Verify results
    assert len(tokens) == 3, f"Expected 3 tokens, got {len(tokens)}"
    for i, (expected_text, expected_pos, expected_type) in enumerate(expected):
        assert tokens[i].text == expected_text, f"Token {i}: expected text '{expected_text}', got '{tokens[i].text}'"
        assert tokens[i].position == expected_pos, f"Token {i}: expected position {expected_pos}, got {tokens[i].position}"
        assert tokens[i].token_type == expected_type, f"Token {i}: expected type {expected_type}, got {tokens[i].token_type}"
    
    print("✓ PASSED\n")


def test_case_2_key_value_pairs():
    """Test Case 2: Key=value pairs"""
    print("=== Test Case 2: Key=value pairs ===")
    input_text = "create company ACME entity=SA currency=EUR"
    tokens = Tokenizer.tokenize(input_text)
    
    expected = [
        ("create", 0, TokenType.UNKNOWN),
        ("company", 7, TokenType.UNKNOWN),
        ("ACME", 15, TokenType.UNKNOWN),
        ("entity", 20, TokenType.UNKNOWN),  # key
        ("SA", 27, TokenType.VALUE),        # value
        ("currency", 30, TokenType.UNKNOWN), # key
        ("EUR", 39, TokenType.VALUE)        # value
    ]
    
    print(f"Input: '{input_text}'")
    print("Expected tokens:")
    for text, pos, token_type in expected:
        print(f"  - ParsedToken(text='{text}', position={pos}, token_type={token_type})")
    
    print("Actual tokens:")
    for token in tokens:
        print(f"  - ParsedToken(text='{token.text}', position={token.position}, token_type={token.token_type})")
    
    # Verify results
    assert len(tokens) == 7, f"Expected 7 tokens, got {len(tokens)}"
    for i, (expected_text, expected_pos, expected_type) in enumerate(expected):
        assert tokens[i].text == expected_text, f"Token {i}: expected text '{expected_text}', got '{tokens[i].text}'"
        assert tokens[i].position == expected_pos, f"Token {i}: expected position {expected_pos}, got {tokens[i].position}"
        assert tokens[i].token_type == expected_type, f"Token {i}: expected type {expected_type}, got {tokens[i].token_type}"
    
    print("✓ PASSED\n")


def test_case_3_quoted_values():
    """Test Case 3: Quoted values (NEW)"""
    print("=== Test Case 3: Quoted values (NEW) ===")
    input_text = 'create company ACME vision="Build the future"'
    tokens = Tokenizer.tokenize(input_text)
    
    expected = [
        ("create", 0, TokenType.UNKNOWN),
        ("company", 7, TokenType.UNKNOWN),
        ("ACME", 15, TokenType.UNKNOWN),
        ("vision", 20, TokenType.UNKNOWN),  # key
        ("Build the future", 28, TokenType.VALUE)  # value without quotes
    ]
    
    print(f"Input: '{input_text}'")
    print("Expected tokens:")
    for text, pos, token_type in expected:
        print(f"  - ParsedToken(text='{text}', position={pos}, token_type={token_type})")
    
    print("Actual tokens:")
    for token in tokens:
        print(f"  - ParsedToken(text='{token.text}', position={token.position}, token_type={token.token_type})")
    
    # Verify results
    assert len(tokens) == 5, f"Expected 5 tokens, got {len(tokens)}"
    for i, (expected_text, expected_pos, expected_type) in enumerate(expected):
        assert tokens[i].text == expected_text, f"Token {i}: expected text '{expected_text}', got '{tokens[i].text}'"
        assert tokens[i].position == expected_pos, f"Token {i}: expected position {expected_pos}, got {tokens[i].position}"
        assert tokens[i].token_type == expected_type, f"Token {i}: expected type {expected_type}, got {tokens[i].token_type}"
    
    print("✓ PASSED\n")


def test_case_4_mixed_syntax():
    """Test Case 4: Mixed syntax (NEW)"""
    print("=== Test Case 4: Mixed syntax (NEW) ===")
    input_text = 'add brand vision="Empower entrepreneurs" target=SMB'
    tokens = Tokenizer.tokenize(input_text)
    
    expected = [
        ("add", 0, TokenType.UNKNOWN),
        ("brand", 4, TokenType.UNKNOWN),
        ("vision", 10, TokenType.UNKNOWN),
        ("Empower entrepreneurs", 18, TokenType.VALUE),
        ("target", 41, TokenType.UNKNOWN),
        ("SMB", 48, TokenType.VALUE)
    ]
    
    print(f"Input: '{input_text}'")
    print("Expected tokens:")
    for text, pos, token_type in expected:
        print(f"  - ParsedToken(text='{text}', position={pos}, token_type={token_type})")
    
    print("Actual tokens:")
    for token in tokens:
        print(f"  - ParsedToken(text='{token.text}', position={token.position}, token_type={token.token_type})")
    
    # Verify results
    assert len(tokens) == 6, f"Expected 6 tokens, got {len(tokens)}"
    for i, (expected_text, expected_pos, expected_type) in enumerate(expected):
        assert tokens[i].text == expected_text, f"Token {i}: expected text '{expected_text}', got '{tokens[i].text}'"
        assert tokens[i].position == expected_pos, f"Token {i}: expected position {expected_pos}, got {tokens[i].position}"
        assert tokens[i].token_type == expected_type, f"Token {i}: expected type {expected_type}, got {tokens[i].token_type}"
    
    print("✓ PASSED\n")


def test_case_5_edge_cases():
    """Test Case 5: Edge cases"""
    print("=== Test Case 5: Edge cases ===")
    
    # Empty quoted value
    print("--- Edge case: Empty quoted value ---")
    input_text = 'key=""'
    tokens = Tokenizer.tokenize(input_text)
    
    expected = [
        ("key", 0, TokenType.UNKNOWN),
        ("", 4, TokenType.VALUE)
    ]
    
    print(f"Input: '{input_text}'")
    print("Actual tokens:")
    for token in tokens:
        print(f"  - ParsedToken(text='{token.text}', position={token.position}, token_type={token.token_type})")
    
    assert len(tokens) == 2, f"Expected 2 tokens, got {len(tokens)}"
    assert tokens[0].text == "key"
    assert tokens[1].text == ""
    assert tokens[1].token_type == TokenType.VALUE
    print("✓ PASSED")
    
    # Single quotes
    print("--- Edge case: Single quotes ---")
    input_text = "key='single quoted'"
    tokens = Tokenizer.tokenize(input_text)
    
    expected = [
        ("key", 0, TokenType.UNKNOWN),
        ("single quoted", 5, TokenType.VALUE)
    ]
    
    print(f"Input: '{input_text}'")
    print("Actual tokens:")
    for token in tokens:
        print(f"  - ParsedToken(text='{token.text}', position={token.position}, token_type={token.token_type})")
    
    assert len(tokens) == 2, f"Expected 2 tokens, got {len(tokens)}"
    assert tokens[0].text == "key"
    assert tokens[1].text == "single quoted"
    assert tokens[1].token_type == TokenType.VALUE
    print("✓ PASSED")
    
    # Nested quotes (best effort)
    print("--- Edge case: Nested quotes ---")
    input_text = '''key="value with 'nested'"'''
    tokens = Tokenizer.tokenize(input_text)
    
    print(f"Input: {input_text}")
    print("Actual tokens:")
    for token in tokens:
        print(f"  - ParsedToken(text='{token.text}', position={token.position}, token_type={token.token_type})")
    
    assert len(tokens) == 2, f"Expected 2 tokens, got {len(tokens)}"
    assert tokens[0].text == "key"
    assert "nested" in tokens[1].text
    assert tokens[1].token_type == TokenType.VALUE
    print("✓ PASSED")
    
    print("✓ All edge cases PASSED\n")


def run_all_tests():
    """Run all test cases"""
    print("Running Tokenizer Refactoring Tests")
    print("=" * 50)
    
    try:
        test_case_1_simple_command()
        test_case_2_key_value_pairs()
        test_case_3_quoted_values()
        test_case_4_mixed_syntax()
        test_case_5_edge_cases()
        
        print("=" * 50)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("The tokenizer refactoring is working correctly.")
        
    except AssertionError as e:
        print(f"❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()