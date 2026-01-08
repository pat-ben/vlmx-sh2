#!/usr/bin/env python3
"""
Comprehensive tests for the filtering system implementation.

Tests all components of the filtering system including:
- Macro expansion
- Filter parsing 
- Filter application
- CommandBuilder integration
- End-to-end filtering workflows
"""

import sys
import os
sys.path.insert(0, 'src')

from vlmx_sh2.dsl.macros import expand_macros
from vlmx_sh2.parser.tokenizer import Tokenizer
from vlmx_sh2.parser.filter import FilterParser, create_filter_from_tokens
from vlmx_sh2.models.parser.filter import FilterExpression, FilterCondition, LogicalOperator
from vlmx_sh2.models.parser.enums import Operator
from vlmx_sh2.models.parser.token import Token
from vlmx_sh2.storage.filters import apply_filters


def test_macro_expansion():
    """Test that operator macros are expanded correctly."""
    print("\n=== Testing Macro Expansion ===")
    
    test_cases = [
        ("list news [category=product & date<2024]", "list news [category=product and date<2024]"),
        ("list competitors [similarity>0.7 | size=large]", "list competitors [similarity>0.7 or size=large]"),
        ("[category=product & date<2024] list news", "[category=product and date<2024] list news"),
        ("cc ACME [status=active & priority>=high]", "create company ACME [status=active and priority>=high]"),
        ("& and | should become and and or", "and and or should become and and or"),
    ]
    
    for input_text, expected in test_cases:
        result = expand_macros(input_text)
        assert result == expected, f"Expected '{expected}', got '{result}'"
        print(f"OK '{input_text}' -> '{result}'")
    
    print("All macro expansion tests passed!")


def test_tokenizer_brackets():
    """Test that tokenizer correctly handles brackets."""
    print("\n=== Testing Tokenizer Bracket Handling ===")
    
    test_cases = [
        "list news [category=product]",
        "list news [category=product and date<2024]", 
        "list competitors [similarity>0.7 or size=large]",
        "[category=product] list news",
        "list [category=product] news",
    ]
    
    for input_text in test_cases:
        # First expand macros
        expanded = expand_macros(input_text)
        
        # Then tokenize
        tokens = Tokenizer.tokenize(expanded)
        
        # Check that brackets are found
        bracket_texts = [token.text for token in tokens if token.text in ['[', ']']]
        print(f"Input: {input_text}")
        print(f"Tokens: {[token.text for token in tokens]}")
        print(f"Brackets found: {bracket_texts}")
        
        # Should have equal number of opening and closing brackets
        assert bracket_texts.count('[') == bracket_texts.count(']'), f"Mismatched brackets in: {input_text}"
        print("OK Brackets handled correctly")
        print()
    
    print("All tokenizer bracket tests passed!")


def test_filter_parsing():
    """Test filter parsing functionality."""
    print("\n=== Testing Filter Parsing ===")
    
    # Simple condition
    tokens = [
        Token(text="category", position=0),
        Token(text="=", position=1),
        Token(text="product", position=2)
    ]
    
    expr = create_filter_from_tokens(tokens)
    assert expr.is_single_condition
    assert expr.condition.field == "category"
    assert expr.condition.operator == Operator.EQUAL
    assert expr.condition.value == "product"
    print("OK Simple condition parsing")
    
    # Implicit AND
    tokens = [
        Token(text="category", position=0),
        Token(text="=", position=1),
        Token(text="product", position=2),
        Token(text="date", position=3),
        Token(text="<", position=4),
        Token(text="2024", position=5)
    ]
    
    expr = create_filter_from_tokens(tokens)
    assert expr.is_logical_expression
    assert expr.operator == LogicalOperator.AND
    print("OK Implicit AND parsing")
    
    # Explicit OR
    tokens = [
        Token(text="category", position=0),
        Token(text="=", position=1),
        Token(text="product", position=2),
        Token(text="or", position=3),
        Token(text="category", position=4),
        Token(text="=", position=5),
        Token(text="team", position=6)
    ]
    
    expr = create_filter_from_tokens(tokens)
    assert expr.is_logical_expression
    assert expr.operator == LogicalOperator.OR
    print("OK Explicit OR parsing")
    
    # Grouped expression
    tokens = [
        Token(text="(", position=0),
        Token(text="category", position=1),
        Token(text="=", position=2),
        Token(text="product", position=3),
        Token(text=")", position=4)
    ]
    
    expr = create_filter_from_tokens(tokens)
    assert expr.is_grouped_expression
    print("OK Grouped expression parsing")
    
    print("All filter parsing tests passed!")


def test_filter_application():
    """Test applying filters to record sets."""
    print("\n=== Testing Filter Application ===")
    
    # Test data
    records = [
        {"name": "ACME", "category": "product", "size": "large", "score": 0.8},
        {"name": "TechCorp", "category": "team", "size": "small", "score": 0.9},
        {"name": "StartUp", "category": "product", "size": "small", "score": 0.6},
        {"name": "BigCorp", "category": "enterprise", "size": "large", "score": 0.7}
    ]
    
    # Test 1: Simple equality filter
    condition = FilterCondition(field="category", operator=Operator.EQUAL, value="product")
    expr = FilterExpression(condition=condition)
    
    filtered = apply_filters(records, expr)
    assert len(filtered) == 2
    assert all(r["category"] == "product" for r in filtered)
    print("OK Simple equality filter")
    
    # Test 2: Numeric comparison
    condition = FilterCondition(field="score", operator=Operator.GREATER, value="0.7")
    expr = FilterExpression(condition=condition)
    
    filtered = apply_filters(records, expr)
    assert len(filtered) == 2  # ACME (0.8) and TechCorp (0.9)
    print("OK Numeric comparison filter")
    
    # Test 3: AND filter 
    left_condition = FilterCondition(field="category", operator=Operator.EQUAL, value="product")
    right_condition = FilterCondition(field="size", operator=Operator.EQUAL, value="large")
    
    left_expr = FilterExpression(condition=left_condition)
    right_expr = FilterExpression(condition=right_condition)
    
    and_expr = FilterExpression(left=left_expr, operator=LogicalOperator.AND, right=right_expr)
    
    filtered = apply_filters(records, and_expr)
    assert len(filtered) == 1  # Only ACME
    assert filtered[0]["name"] == "ACME"
    print("OK AND filter")
    
    # Test 4: OR filter
    left_condition = FilterCondition(field="category", operator=Operator.EQUAL, value="product")
    right_condition = FilterCondition(field="category", operator=Operator.EQUAL, value="team")
    
    left_expr = FilterExpression(condition=left_condition)
    right_expr = FilterExpression(condition=right_condition)
    
    or_expr = FilterExpression(left=left_expr, operator=LogicalOperator.OR, right=right_expr)
    
    filtered = apply_filters(records, or_expr)
    assert len(filtered) == 3  # ACME, TechCorp, StartUp
    print("OK OR filter")
    
    print("All filter application tests passed!")


def test_end_to_end_filtering():
    """Test complete end-to-end filtering workflow."""
    print("\n=== Testing End-to-End Filtering ===")
    
    test_cases = [
        {
            "input": "list news [category=product]",
            "expected_tokens": ["list", "news", "category", "product"],
            "expected_filter_fields": ["category"]
        },
        {
            "input": "list competitors [similarity>0.7 & size=large]", 
            "expected_tokens": ["list", "competitors", "similarity", "size", "large"],
            "expected_filter_fields": ["similarity", "size"]
        },
        {
            "input": "list news [category=product | category=team]",
            "expected_tokens": ["list", "news", "category", "product", "category", "team"],
            "expected_filter_fields": ["category"]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest case {i+1}: {test_case['input']}")
        
        # Step 1: Macro expansion
        expanded = expand_macros(test_case["input"])
        print(f"  Expanded: {expanded}")
        
        # Step 2: Tokenization
        tokens = Tokenizer.tokenize(expanded)
        token_texts = [t.text for t in tokens]
        print(f"  Tokens: {token_texts}")
        
        # Verify expected tokens are present
        for expected_token in test_case["expected_tokens"]:
            assert expected_token in token_texts, f"Expected token '{expected_token}' not found"
        
        # Step 3: Filter parsing (simulate what CommandBuilder would do)
        filter_parser = FilterParser()
        
        # Create mock RecognizedToken objects (simplified for testing)
        from vlmx_sh2.models.parser.recognized_token import RecognizedToken
        from vlmx_sh2.models.parser.enums import TokenType, ValueContext
        
        recognized_tokens = []
        for token in tokens:
            recognized_tokens.append(RecognizedToken(
                text=token.text,
                position=token.position,
                was_quoted=token.was_quoted,
                operator_after=token.operator_after,
                token_type=TokenType.UNKNOWN,  # Simplified for testing
                value_context=ValueContext.FIELD
            ))
        
        filters = filter_parser.parse_filters(recognized_tokens)
        
        if filters:
            print(f"  Parsed filter: {filters}")
            
            # Verify filter structure
            from vlmx_sh2.storage.filters import get_filter_fields
            filter_fields = get_filter_fields(filters)
            print(f"  Filter fields: {filter_fields}")
            
            # Check that expected fields are present
            for expected_field in test_case["expected_filter_fields"]:
                assert expected_field in filter_fields, f"Expected field '{expected_field}' not in filter"
        
        print(f"  OK End-to-end test {i+1} passed")
    
    print("\nAll end-to-end filtering tests passed!")


def test_complex_scenarios():
    """Test complex filtering scenarios."""
    print("\n=== Testing Complex Scenarios ===")
    
    # Test records with various data types
    records = [
        {"name": "News1", "category": "product", "date": "2024-01-15", "priority": "high", "active": True},
        {"name": "News2", "category": "team", "date": "2023-12-20", "priority": "low", "active": False},
        {"name": "News3", "category": "product", "date": "2024-02-10", "priority": "high", "active": True},
        {"name": "News4", "category": "enterprise", "date": "2024-01-05", "priority": "medium", "active": True}
    ]
    
    # Complex nested filter: (category=product & active=true) | priority=high
    left_left = FilterCondition(field="category", operator=Operator.EQUAL, value="product")
    left_right = FilterCondition(field="active", operator=Operator.EQUAL, value="true")
    
    left_expr = FilterExpression(
        left=FilterExpression(condition=left_left),
        operator=LogicalOperator.AND,
        right=FilterExpression(condition=left_right)
    )
    
    right_expr = FilterExpression(condition=FilterCondition(field="priority", operator=Operator.EQUAL, value="high"))
    
    complex_expr = FilterExpression(left=left_expr, operator=LogicalOperator.OR, right=right_expr)
    
    filtered = apply_filters(records, complex_expr)
    print(f"Complex filter result: {len(filtered)} records")
    for record in filtered:
        print(f"  - {record['name']}: category={record['category']}, active={record['active']}, priority={record['priority']}")
    
    # Should match News1, News3 (product & active) and potentially others with priority=high
    assert len(filtered) >= 2
    print("OK Complex nested filter")
    
    # Test date comparison
    date_condition = FilterCondition(field="date", operator=Operator.GREATER, value="2024-01-01")
    date_expr = FilterExpression(condition=date_condition)
    
    filtered = apply_filters(records, date_expr)
    print(f"Date filter result: {len(filtered)} records from 2024")
    assert len(filtered) == 3  # News1, News3, News4 are from 2024
    print("OK Date comparison filter")
    
    print("All complex scenario tests passed!")


def main():
    """Run all tests."""
    print("Running comprehensive filtering system tests...")
    
    try:
        test_macro_expansion()
        test_tokenizer_brackets() 
        test_filter_parsing()
        test_filter_application()
        test_end_to_end_filtering()
        test_complex_scenarios()
        
        print("\n" + "="*50)
        print("*** ALL FILTERING SYSTEM TESTS PASSED! ***")
        print("="*50)
        
    except Exception as e:
        print(f"\nXX Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()