"""
Support system for VLMX shell intelligence.

This module provides the "rendering" layer for the shell's intelligence features,
similar to how Nushell handles typed data and intelligent error reporting.

Components:
- Suggestions: Context-aware command and token suggestions
- Labels: Smart labeling and classification of user input
- Spans: Precise error location and context highlighting
- Error rendering: Detailed, actionable error messages with exact locations

Just like Nu operates on typed data to catch bugs that other shells miss,
this support system ensures users get clear, precise feedback about where
things break and exactly why they break.

The goal is to provide an intelligent, helpful shell experience that guides
users toward correct syntax and meaningful operations.
"""