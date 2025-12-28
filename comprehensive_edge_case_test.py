#!/usr/bin/env python3
"""
Comprehensive edge case testing for the improved tokenizer.
Tests all the fixes implemented for the identified issues.
"""

import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.parser.tokenizer import Tokenizer
from vlmx_sh2.models.parser import ParsedToken, TokenType


def test_position_tracking():
    """Test improved position tracking accuracy"""
    print("=== Position Tracking Tests ===")
    
    # Test with mixed content
    input_text = 'create company ACME vision="Build future" entity=SA'
    tokens = Tokenizer.tokenize(input_text)
    
    print(f"Input: '{input_text}'")
    print("Position tracking:")
    for token in tokens:
        actual_substr = input_text[token.position:token.position + len(token.text)]
        print(f"  pos {token.position:2d}: '{token.text}' -> '{actual_substr}' {'✓' if token.text == actual_substr else '✗'}")
    
    # Verify positions are accurate
    for token in tokens:
        actual_substr = input_text[token.position:token.position + len(token.text)]
        if token.text != "Build future":  # Quoted values span multiple original positions
            assert token.text == actual_substr or "Build future" in token.text, \
                f"Position mismatch: token '{token.text}' at pos {token.position}, found '{actual_substr}'"
    
    print("✓ Position tracking PASSED\n")


def test_empty_values():
    """Test empty value handling"""
    print("=== Empty Value Tests ===")
    
    test_cases = [
        ('key=""', [("key", TokenType.UNKNOWN), ("", TokenType.VALUE)]),
        ("key=", [("key", TokenType.UNKNOWN), ("", TokenType.VALUE)]),
        ('desc="" name=test', [("desc", TokenType.UNKNOWN), ("", TokenType.VALUE), ("name", TokenType.UNKNOWN), ("test", TokenType.VALUE)]),
    ]
    
    for input_text, expected in test_cases:
        print(f"Input: '{input_text}'")
        tokens = Tokenizer.tokenize(input_text)
        
        print("Tokens:")
        for token in tokens:
            print(f"  - '{token.text}' ({token.token_type})")
        
        assert len(tokens) == len(expected), f"Expected {len(expected)} tokens, got {len(tokens)}"
        for i, (expected_text, expected_type) in enumerate(expected):
            assert tokens[i].text == expected_text, f"Token {i}: expected '{expected_text}', got '{tokens[i].text}'"
            assert tokens[i].token_type == expected_type, f"Token {i}: expected {expected_type}, got {tokens[i].token_type}"
        
        print("✓ PASSED")
    
    print("✓ All empty value tests PASSED\n")


def test_operator_edge_cases():
    """Test edge case operators"""
    print("=== Operator Edge Case Tests ===")
    
    test_cases = [
        ("key==value", [("key", "=", "=value")]),
        ("key>=10", [("key", ">=", "10")]),
        ("key!=test", [("key", "!=", "test")]),
        ("key<=5", [("key", "<=", "5")]),
        ("price>100", [("price", ">", "100")]),
        ("count<50", [("count", "<", "50")]),
    ]
    
    for input_token, expected in test_cases:
        result = Tokenizer._parse_attribute_token(input_token)
        print(f"'{input_token}' -> {result}")
        
        expected_result = expected[0]
        assert result == expected_result, f"Expected {expected_result}, got {result}"
        print("✓ PASSED")
    
    print("✓ All operator edge case tests PASSED\n")


def test_quote_safety_limits():
    """Test quote mismatch handling and safety limits"""
    print("=== Quote Safety Limit Tests ===")
    
    # Test unclosed quotes with safety limit
    print("--- Unclosed quote test ---")
    # Create a long token list to test safety limits
    long_input = 'vision="This is an unclosed quote that goes on ' + ' '.join([f'word{i}' for i in range(25)])
    tokens = Tokenizer.tokenize(long_input)
    
    print(f"Input: '{long_input[:50]}...'")
    print("Tokens:")
    for i, token in enumerate(tokens):
        if i < 5:  # Show first few tokens
            print(f"  {i}: '{token.text}' ({token.token_type})")
        elif i == 5:
            print("  ...")
    
    # Should have vision token and a value token (even if unclosed)
    assert len(tokens) >= 2, "Should have at least key and value tokens"
    assert tokens[0].text == "vision", "First token should be 'vision'"
    assert tokens[1].token_type == TokenType.VALUE, "Second token should be VALUE type"
    
    print("✓ Safety limit test PASSED")
    
    # Test properly closed quotes
    print("--- Properly closed quote test ---")
    normal_input = 'desc="This is properly closed"'
    tokens = Tokenizer.tokenize(normal_input)
    
    print(f"Input: '{normal_input}'")
    print("Tokens:")
    for token in tokens:
        print(f"  - '{token.text}' ({token.token_type})")
    
    assert len(tokens) == 2
    assert tokens[0].text == "desc"
    assert tokens[1].text == "This is properly closed"
    assert tokens[1].token_type == TokenType.VALUE
    
    print("✓ Proper quote handling PASSED")
    print("✓ All quote safety tests PASSED\n")


def test_complex_mixed_scenarios():
    """Test complex real-world scenarios"""
    print("=== Complex Mixed Scenario Tests ===")
    
    # Test complex business command
    complex_input = 'create company "ACME Corp" vision="Build the future" entity= revenue>=1000000 status!=""'
    tokens = Tokenizer.tokenize(complex_input)
    
    print(f"Input: '{complex_input}'")
    print("Tokens:")
    for token in tokens:
        print(f"  - '{token.text}' (pos: {token.position}, type: {token.token_type})")
    
    # Verify we get reasonable parsing
    assert len(tokens) >= 8, "Should parse multiple key-value pairs"
    
    # Check that quoted company name is handled
    company_tokens = [t for t in tokens if "ACME" in t.text]
    assert len(company_tokens) == 1, "Should find ACME company token"
    
    # Check that multi-word vision is handled
    vision_value_tokens = [t for t in tokens if "Build the future" in t.text]
    assert len(vision_value_tokens) == 1, "Should find complete vision value"
    
    # Check empty entity value
    empty_tokens = [t for t in tokens if t.text == "" and t.token_type == TokenType.VALUE]
    assert len(empty_tokens) >= 1, "Should handle empty values"
    
    print("✓ Complex scenario PASSED\n")


def test_regression_original_cases():
    """Ensure original test cases still work"""
    print("=== Regression Test (Original Cases) ===")
    
    # Original test cases should still pass
    original_cases = [
        ("create company ACME", 3),
        ("create company ACME entity=SA currency=EUR", 7),
        ('create company ACME vision="Build the future"', 5),
        ('add brand vision="Empower entrepreneurs" target=SMB', 6),
    ]
    
    for input_text, expected_count in original_cases:
        tokens = Tokenizer.tokenize(input_text)
        print(f"'{input_text}' -> {len(tokens)} tokens")
        assert len(tokens) == expected_count, f"Expected {expected_count} tokens, got {len(tokens)}"
        print("✓ PASSED")
    
    print("✓ All regression tests PASSED\n")


def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("Running Comprehensive Edge Case Tests")
    print("=" * 60)
    
    try:
        test_position_tracking()
        test_empty_values()
        test_operator_edge_cases()
        test_quote_safety_limits()
        test_complex_mixed_scenarios()
        test_regression_original_cases()
        
        print("=" * 60)
        print("🎉 ALL COMPREHENSIVE TESTS PASSED! 🎉")
        print("Tokenizer improvements are working correctly.")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_comprehensive_tests()