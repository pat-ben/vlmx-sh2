#!/usr/bin/env python3
"""
Test script for the new three-stage tokenizer.
Tests all the specified test cases from the refactoring prompt.
"""

import sys
sys.path.insert(0, 'src')

from vlmx_sh2.parser.tokenizer import Tokenizer
from vlmx_sh2.models.parser import Operator

def test_case(description: str, input_text: str, expected_results: list):
    """Test a single case and compare results."""
    print(f"\n=== {description} ===")
    print(f"Input: {input_text}")
    
    try:
        tokens = Tokenizer.tokenize(input_text)
        print(f"Got {len(tokens)} tokens:")
        
        for i, token in enumerate(tokens):
            print(f"  {i}: text='{token.text}', position={token.position}, was_quoted={token.was_quoted}, operator_after={token.operator_after}")
        
        # Verify against expected results
        if len(tokens) != len(expected_results):
            print(f"FAIL: Expected {len(expected_results)} tokens, got {len(tokens)}")
            return False
        
        for i, (token, expected) in enumerate(zip(tokens, expected_results)):
            checks = []
            
            if token.text != expected.get('text'):
                checks.append(f"text mismatch: got '{token.text}', expected '{expected.get('text')}'")
            
            if token.position != expected.get('position'):
                checks.append(f"position mismatch: got {token.position}, expected {expected.get('position')}")
            
            if token.was_quoted != expected.get('was_quoted', False):
                checks.append(f"was_quoted mismatch: got {token.was_quoted}, expected {expected.get('was_quoted', False)}")
            
            if token.operator_after != expected.get('operator_after'):
                checks.append(f"operator_after mismatch: got {token.operator_after}, expected {expected.get('operator_after')}")
            
            if checks:
                print(f"FAIL at token {i}: {', '.join(checks)}")
                return False
        
        print("PASS")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_tests():
    """Run all test cases."""
    print("Testing New Three-Stage Tokenizer")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: Simple command
    test_results.append(test_case(
        "Test 1: Simple command",
        "create company ACME",
        [
            {"text": "create", "position": 0, "was_quoted": False},
            {"text": "company", "position": 1, "was_quoted": False},
            {"text": "ACME", "position": 2, "was_quoted": False},
        ]
    ))
    
    # Test 2: Quoted entity value
    test_results.append(test_case(
        "Test 2: Quoted entity value",
        'create company "ACME"',
        [
            {"text": "create", "position": 0, "was_quoted": False},
            {"text": "company", "position": 1, "was_quoted": False},
            {"text": "ACME", "position": 2, "was_quoted": True},
        ]
    ))
    
    # Test 3: Multi-word quoted value
    test_results.append(test_case(
        "Test 3: Multi-word quoted value",
        'create company "ACME INTL"',
        [
            {"text": "create", "position": 0, "was_quoted": False},
            {"text": "company", "position": 1, "was_quoted": False},
            {"text": "ACME INTL", "position": 2, "was_quoted": True},
        ]
    ))
    
    # Test 4: Key=value with quotes
    test_results.append(test_case(
        "Test 4: Key=value with quotes",
        'vision="Our vision" currency=EUR',
        [
            {"text": "vision", "position": 0, "operator_after": Operator.EQUAL},
            {"text": "Our vision", "position": 1, "was_quoted": True},
            {"text": "currency", "position": 2, "operator_after": Operator.EQUAL},
            {"text": "EUR", "position": 3, "was_quoted": False},
        ]
    ))
    
    # Test 5: Mixed
    test_results.append(test_case(
        "Test 5: Mixed",
        'create company "ACME" vision="Our vision" currency=EUR',
        [
            {"text": "create", "position": 0, "was_quoted": False},
            {"text": "company", "position": 1, "was_quoted": False},
            {"text": "ACME", "position": 2, "was_quoted": True},
            {"text": "vision", "position": 3, "operator_after": Operator.EQUAL},
            {"text": "Our vision", "position": 4, "was_quoted": True},
            {"text": "currency", "position": 5, "operator_after": Operator.EQUAL},
            {"text": "EUR", "position": 6, "was_quoted": False},
        ]
    ))
    
    # Test 6: Different operators (note: "where" is excluded)
    test_results.append(test_case(
        "Test 6: Different operators",
        'where amount>1000 status="active"',
        [
            {"text": "amount", "position": 0, "operator_after": Operator.GREATER},
            {"text": "1000", "position": 1, "was_quoted": False},
            {"text": "status", "position": 2, "operator_after": Operator.EQUAL},
            {"text": "active", "position": 3, "was_quoted": True},
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

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)