"""
Enums for parser.

Contains all enum types used throughout the parsing pipeline.
"""

from enum import Enum


class Operator(str, Enum):
    """Operators for field assignments and comparisons"""
    EQUAL = "="
    GREATER = ">"
    LESS = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    NOT_EQUAL = "!="


class QueryKeyword(str, Enum):
    """Query keywords for filtering"""
    AND = "and"
    OR = "or"


class Bracket(str, Enum):
    """Brackets and parentheses"""
    PAREN_OPEN = "("
    PAREN_CLOSE = ")"
    BRACKET_OPEN = "["
    BRACKET_CLOSE = "]"


class TokenClass(str, Enum):
    """Structural classification of tokens (classifier stage)."""
    TEXT = "text"              # Text (quoted or not, quotes stripped if present)
    OPERATOR = "operator"      # =, !=, <, >, <=, >=
    BRACKET = "bracket"        # [, ], (, )


class TokenType(str, Enum):
    """Type classification for parsed tokens (set by recognizer)"""
    WORD = "word"        # Token that matches a Word in the registry
    VALUE = "value"      # Token representing a value (company name, etc.)
    UNKNOWN = "unknown"  # Token that doesn't match any known pattern


class ValueContext(str, Enum):
    """Context classification for VALUE tokens."""
    SCHEMA = "schema"  # Schema name (company name for create/database ops)
    ENTITY = "entity"  # Entity value (reserved for future use)
    FIELD = "field"    # Field/attribute value (currency, vision, etc.)