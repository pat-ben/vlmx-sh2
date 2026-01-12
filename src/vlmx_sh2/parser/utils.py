"""
Utility functions for parser.

Contains helper functions used throughout the parsing process.
For now, this primarily imports and re-exports the expand_shortcuts
function from the DSL macros module.
"""

from ..words.macros import expand_macros

# Re-export the expand_shortcuts function for use by the parser
__all__ = ['expand_macros']