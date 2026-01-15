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
    
    TOKENIZER = "tokenizer"      # Stage 1: Text → token blocks
    RECOGNIZER = "recognizer"    # Stage 2: Tokens → recognized tokens
    SPLITTER = "splitter"        # Stage 3: Split command/filter tokens
    FILTER = "filter"            # Stage 4: Build filter AST
    BUILDER = "builder"          # Stage 5: Build command object
    HANDLER = "handler"        # Execution stage (post-parsing)