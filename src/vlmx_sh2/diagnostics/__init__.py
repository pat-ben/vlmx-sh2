# File: src/vlmx_sh2/diagnostics/__init__.py
"""
Diagnostic system for VLMX shell.

Provides validation issue tracking, suggestion generation, and diagnostic logging
to deliver Nushell-quality error reporting and user feedback.

Components:
- SuggestionEngine: Context-aware suggestions for fixing issues
- TokenizerValidator: Validation rules for tokenizer stage
- DiagnosticLogger: Issue tracking and logging (future)
- DiagnosticReporter: Main coordinator for diagnostic output (future)
"""

from .suggestions import SuggestionEngine
from .validators.tokenizer import TokenizerValidator

__all__ = [
    "SuggestionEngine",
    "TokenizerValidator",
]