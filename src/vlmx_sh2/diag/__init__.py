# File: src/vlmx_sh2/diagnostics/__init__.py
"""
Diagnostic shell for VLMX shell.

Provides validation issue tracking, suggestion generation, and diagnostic logging
to deliver Nushell-quality error reporting and user feedback.

Components:
- Validator: Unified validator for all parsing stages
- ValidationRule: Model for defining validation rules
- VALIDATION_RULES: Central registry of all validation rules
- SuggestionEngine: Context-aware suggestions for fixing issues
- PositionResolver: Lazy position resolution for error reporting
- DiagnosticFormatter: Rich error message formatting
- DiagnosticLogger: Issue tracking and logging (future)
"""

from .suggestions import SuggestionEngine
from .validator import Validator, TokenLike, AnyToken
from .rules import ValidationRule, VALIDATION_RULES, get_rules_for_stage
from .resolver import PositionResolver
from .formatter import DiagnosticFormatter, OutputFormat

__all__ = [
    "SuggestionEngine",
    "Validator",
    "TokenLike",
    "AnyToken", 
    "ValidationRule",
    "VALIDATION_RULES",
    "get_rules_for_stage",
    "PositionResolver",
    "DiagnosticFormatter",
    "OutputFormat",
]

# TODO: Add DiagnosticLogger for issue history tracking
# TODO: Add DiagnosticReporter for output coordination (format + log + display)