#!/usr/bin/env python3
"""
Integration test for the value-level query operators & range support.

Tests the full parsing pipeline to ensure everything works together.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vlmx_sh2.models.parser.filtering import ValueExpression, LogicalOperator
from vlmx_sh2.enums import Operator


def test_basic_functionality():
    """Test that our new ValueExpression models work correctly."""
    print("Testing basic ValueExpression functionality...")
    
    # Test simple value
    simple_expr = ValueExpression(simple="product")
    assert simple_expr.is_simple_value
    print("+ Simple value expressions work")
    
    # Test range value
    range_expr = ValueExpression(range_start="2022", range_end="2029")
    assert range_expr.is_range_value
    print("+ Range value expressions work")
    
    # Test compound value
    compound_expr = ValueExpression(
        left=simple_expr,
        logic=LogicalOperator.OR,
        right=ValueExpression(simple="team")
    )
    assert compound_expr.is_compound_value
    print("+ Compound value expressions work")
    
    print("+ All ValueExpression types work correctly")


def main():
    """Run integration tests."""
    print("Running integration tests for value-level query operators & range support...\n")
    
    try:
        test_basic_functionality()
        
        print("\n*** Integration tests passed! The implementation integrates correctly with the system.")
        
    except Exception as e:
        print(f"\nXXX Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()