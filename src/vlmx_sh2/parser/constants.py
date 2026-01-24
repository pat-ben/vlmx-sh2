"""
Shared constants for the parser module.

Contains commonly used constants across multiple parsing stages to avoid duplication.
"""

from vlmx_sh2.enums import Bracket, Operator

# Bracket values used by tokenizer and classifier  
BRACKET_VALUES = {bracket.value for bracket in Bracket}

# Operators sorted by length (longest first) for tokenizer pattern matching
OPERATORS_BY_LENGTH = sorted([op.value for op in Operator], key=len, reverse=True)