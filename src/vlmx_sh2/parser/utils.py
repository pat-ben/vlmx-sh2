"""
Utility functions for VLMX DSL parser.

Contains helper functions used throughout the parsing process.
For now, this primarily imports and re-exports the expand_shortcuts
function from the DSL macros module.
"""

from ..dsl.macros import expand_shortcuts

# Re-export the expand_shortcuts function for use by the parser
__all__ = ['expand_shortcuts']