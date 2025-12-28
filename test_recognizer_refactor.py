#!/usr/bin/env python3
"""
Test script for the refactored WordRecognizer with ValueContext classification.
"""

import sys
sys.path.insert(0, 'src')

from vlmx_sh2.parser.tokenizer import Tokenizer
from vlmx_sh2.parser.recognizer import WordRecognizer
from vlmx_sh2.models.parser import TokenType, ValueContext


def test_recognition_case(description: str, input_text: str, expected_results: list):
    """Test a recognition case and compare results."""
    print(f"\n=== {description} ===")
    print(f"Input: {input_text}")
    
    try:
        # Stage 1: Tokenize
        tokenizer = Tokenizer()
        tokens = tokenizer.tokenize(input_text)
        
        # Stage 2: Recognize
        recognizer = WordRecognizer()
        recognized_tokens = recognizer.process_tokens(tokens)
        
        print(f"Got {len(recognized_tokens)} recognized tokens:")
        
        success = True
        for i, token in enumerate(recognized_tokens):
            expected = expected_results[i] if i < len(expected_results) else {}
            
            print(f"  {i}: '{token.text}' -> {token.token_type}")
            print(f"      Type: {type(token).__name__}")
            print(f"      Word: {token.word.id if token.word else None}")
            print(f"      Value context: {token.value_context}")
            print(f"      Was quoted: {token.was_quoted}")
            
            # Check expectations
            if expected.get('token_type') and token.token_type != expected['token_type']:
                print(f"      FAIL: Expected token_type {expected['token_type']}, got {token.token_type}")
                success = False
            
            if expected.get('value_context') and token.value_context != expected['value_context']:
                print(f"      FAIL: Expected value_context {expected['value_context']}, got {token.value_context}")
                success = False
            
            if expected.get('word_type') and (not token.word or token.word.word_type.name != expected['word_type']):
                print(f"      FAIL: Expected word_type {expected['word_type']}, got {token.word.word_type.name if token.word else None}")
                success = False
        
        if success:
            print("PASS")
        else:
            print("FAIL")
        
        return success
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_tests():
    """Run all test cases."""
    print("Testing Refactored WordRecognizer")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Basic command
    test_results.append(test_recognition_case(
        "Test 1: Basic command",
        'create company "ACME"',
        [
            {"token_type": TokenType.WORD, "word_type": "WordType.ACTION"},
            {"token_type": TokenType.WORD, "word_type": "WordType.ENTITY"},
            {"token_type": TokenType.VALUE, "value_context": ValueContext.ENTITY}
        ]
    ))
    
    # Test 2: Attributes with quoted and unquoted values
    test_results.append(test_recognition_case(
        "Test 2: Field values",
        'vision="Our vision" currency=EUR',
        [
            {"token_type": TokenType.WORD, "word_type": "FIELD"},
            {"token_type": TokenType.VALUE, "value_context": ValueContext.FIELD},
            {"token_type": TokenType.WORD, "word_type": "FIELD"},
            {"token_type": TokenType.VALUE, "value_context": ValueContext.FIELD}
        ]
    ))
    
    # Test 3: Unquoted entity value (should be UNKNOWN)
    test_results.append(test_recognition_case(
        "Test 3: Unquoted entity (validation)",
        'create company ACME',
        [
            {"token_type": TokenType.WORD, "word_type": "ACTION"},
            {"token_type": TokenType.WORD, "word_type": "ENTITY"},
            {"token_type": TokenType.UNKNOWN}  # Not quoted, so not entity value
        ]
    ))
    
    # Test 4: Unknown tokens with suggestions
    test_results.append(test_recognition_case(
        "Test 4: Unknown tokens",
        'xyz123 company "ACME"',
        [
            {"token_type": TokenType.UNKNOWN},
            {"token_type": TokenType.WORD, "word_type": "ENTITY"},
            {"token_type": TokenType.VALUE, "value_context": ValueContext.ENTITY}
        ]
    ))
    
    # Test 5: Mixed complex case
    test_results.append(test_recognition_case(
        "Test 5: Complex mixed case",
        'add brand "Super Brand" vision="Our vision" currency=EUR',
        [
            {"token_type": TokenType.WORD, "word_type": "ACTION"},
            {"token_type": TokenType.WORD, "word_type": "ENTITY"},
            {"token_type": TokenType.VALUE, "value_context": ValueContext.ENTITY},
            {"token_type": TokenType.WORD, "word_type": "FIELD"},
            {"token_type": TokenType.VALUE, "value_context": ValueContext.FIELD},
            {"token_type": TokenType.WORD, "word_type": "FIELD"},
            {"token_type": TokenType.VALUE, "value_context": ValueContext.FIELD}
        ]
    ))
    
    # Summary
    print(f"\n{'='*50}")
    print(f"TEST SUMMARY")
    print(f"{'='*50}")
    passed = sum(test_results)
    total = len(test_results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("ALL TESTS PASSED!")
        return True
    else:
        print("Some tests failed")
        return False


def test_specific_properties():
    """Test the specific property methods on RecognizedToken."""
    print(f"\n{'='*50}")
    print("Testing RecognizedToken Properties")
    print('='*50)
    
    # Test token creation
    tokenizer = Tokenizer()
    recognizer = WordRecognizer()
    
    tokens = tokenizer.tokenize('create company "ACME" vision="text"')
    recognized = recognizer.process_tokens(tokens)
    
    # Test properties
    for i, token in enumerate(recognized):
        print(f"\nToken {i}: '{token.text}'")
        print(f"  is_word: {token.is_word}")
        print(f"  is_value: {token.is_value}")
        print(f"  is_unknown: {token.is_unknown}")
        print(f"  is_entity_value: {token.is_entity_value}")
        print(f"  is_field_value: {token.is_field_value}")
        print(f"  is_action_word: {token.is_action_word}")
        print(f"  is_entity_word: {token.is_entity_word}")
        print(f"  is_field_word: {token.is_field_word}")
        print(f"  token_type: {token.token_type}")
        print(f"  value_context: {token.value_context}")


if __name__ == "__main__":
    success = run_tests()
    test_specific_properties()
    sys.exit(0 if success else 1)