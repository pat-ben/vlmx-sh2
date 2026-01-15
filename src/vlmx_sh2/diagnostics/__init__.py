# File: src/vlmx_sh2/diagnostics/__init__.py
"""
Diagnostic system for VLMX shell.

Provides validation issue tracking, suggestion generation, and diagnostic logging
to deliver Nushell-quality error reporting and user feedback.

Components:
- Validator: Unified validator for all parsing stages
- ValidationRule: Model for defining validation rules
- VALIDATION_RULES: Central registry of all validation rules
- SuggestionEngine: Context-aware suggestions for fixing issues
- DiagnosticLogger: Issue tracking and logging (future)
- DiagnosticReporter: Main coordinator for diagnostic output (future)
"""

from .suggestions import SuggestionEngine
from .validator import Validator
from .rules import ValidationRule, VALIDATION_RULES, get_rules_for_stage

__all__ = [
    "SuggestionEngine",
    "Validator",
    "ValidationRule",
    "VALIDATION_RULES",
    "get_rules_for_stage",
]