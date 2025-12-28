#!/usr/bin/env python3
"""
Additional edge case tests for the tokenizer to ensure robustness.
"""

import sys
sys.path.insert(0, 'src')

from vlmx_sh2.parser.tokenizer import Tokenizer
from vlmx_sh2.models.parser import Operator

def test_edge_case(description: str, input_text: str):
    """Test an edge case and show the results."""
    print(f"\n=== {description} ===")
    print(f"Input: {input_text}")
    
    try:
        tokens = Tokenizer.tokenize(input_text)
        print(f"Got {len(tokens)} tokens:")
        
        for i, token in enumerate(tokens):
            print(f"  {i}: text='{token.text}', position={token.position}, was_quoted={token.was_quoted}, operator_after={token.operator_after}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

def run_edge_case_tests():
    """Run edge case tests."""
    print("Edge Case Tests for Tokenizer")
    print("=" * 50)
    
    # Test empty input
    test_edge_case("Empty input", "")
    
    # Test single quoted string
    test_edge_case("Single quoted string", '"hello world"')
    
    # Test empty quotes
    test_edge_case("Empty quotes", 'key=""')
    
    # Test single quotes
    test_edge_case("Single quotes", "key='single quoted value'")
    
    # Test mixed quotes
    test_edge_case("Mixed quotes", 'key1="double" key2=\'single\'')
    
    # Test multiple operators
    test_edge_case("Multiple operators", "amount>=100 price<50 status!=inactive")
    
    # Test query keywords
    test_edge_case("Query with keywords", "where name=john and age>25 or status=active")
    
    # Test brackets
    test_edge_case("Brackets", "find (name=john or name=jane) and [status=active]")
    
    # Test unclosed quotes (should handle gracefully)
    test_edge_case("Unclosed quotes", 'key="unclosed quote value')
    
    # Test complex nested case
    test_edge_case("Complex case", 'create company "ACME Corp" where vision="Build the future" and currency=EUR status="active"')

if __name__ == "__main__":
    run_edge_case_tests()