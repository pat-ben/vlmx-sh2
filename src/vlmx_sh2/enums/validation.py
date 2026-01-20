"""
Validation enums for issue classification.

Defines severity levels and parsing stages for validation diagnostics.
"""

from enum import Enum


class IssueSeverity(str, Enum):
    """Severity level for validation issues."""
    
    ERROR = "error"      # Blocking issue - command cannot execute
    WARNING = "warning"  # Non-blocking issue - command may execute with caveats
    INFO = "info"        # Informational - helpful hints or suggestions


class IssueStage(str, Enum):
    """Parsing stage where validation issue was detected."""
    
    NORMALIZER = "normalizer"      # Stage 0: Text normalization and macro expansion
    TOKENIZER = "tokenizer"        # Stage 1: Text → token blocks
    CLASSIFIER = "classifier"      # Stage 2: Structural classification
    RECOGNIZER = "recognizer"      # Stage 3: Semantic classification
    SPLITTER = "splitter"          # Stage 4: Split command/filter
    FILTER_PARSER = "filter_parser"  # Stage 5: Build filter AST
    BUILDER = "builder"            # Stage 6: Build command
    HANDLER = "handler"            # Post-parsing execution