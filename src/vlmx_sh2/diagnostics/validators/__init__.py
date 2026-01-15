# File: src/vlmx_sh2/diagnostics/validators/__init__.py
"""
Validators for parser stages.

Each validator contains stage-specific validation rules that check
for errors, warnings, and info-level issues during parsing.

Validators are stateless and use ValidationContext to log issues.
"""

from .tokenizer import TokenizerValidator

__all__ = [
    "TokenizerValidator",
]