# File: src/vlmx_sh2/diagnostics/rules.py
"""
Validation rules registry.

Central registry of all validation rules across parsing stages.
Rules are organized by IssueStage enum for easy management.

Each rule defines:
- What to check (validation logic)
- What error to report (message, code, suggestion)
- Which stage it belongs to
"""

from typing import Callable, List
from dataclasses import dataclass
from ..enums import IssueStage


@dataclass
class ValidationRule:
    """
    A single validation rule.
    
    Defines validation logic and error reporting for a specific check.
    Rules are organized by parsing stage (IssueStage enum).
    """
    rule_id: str                    # Unique identifier (e.g., "empty_command")
    stage: IssueStage               # Which stage this rule applies to
    check: Callable[..., bool]      # Validation function - returns True if valid
    error_code: str                 # Structured error code (e.g., "vlmx::tokenizer::empty_command")
    message: str                    # Human-readable error message
    suggestion: str = ""            # Optional suggestion for fixing
    position: int = 0               # Default character position for error


# =============================================================================
# VALIDATION RULES REGISTRY
# =============================================================================

VALIDATION_RULES: List[ValidationRule] = [
    # ==================== TOKENIZER STAGE ====================
    
    ValidationRule(
        rule_id="empty_command",
        stage=IssueStage.TOKENIZER,
        check=lambda text, **kwargs: bool(text and text.strip()),
        error_code="vlmx::tokenizer::empty_command",
        message="Command cannot be empty",
        suggestion="Try typing a command like 'create company' or 'show metadata'",
        position=0
    ),
    
    # Future tokenizer rules will be added here...
    # Example: unclosed_quotes, mismatched_brackets, etc.
    
    
    # ==================== CLASSIFIER STAGE ====================
    
    # Future classifier rules will be added here...
    
    
    # ==================== RECOGNIZER STAGE ====================
    
    # Future recognizer rules will be added here...
    
    
    # ==================== OTHER STAGES ====================
    
    # Future rules for SPLITTER, FILTER_PARSER, BUILDER, HANDLER...
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_rules_for_stage(stage: IssueStage) -> List[ValidationRule]:
    """Get all validation rules for a specific parsing stage."""
    return [rule for rule in VALIDATION_RULES if rule.stage == stage]


def get_rule_by_id(rule_id: str) -> ValidationRule:
    """Get a specific validation rule by its ID."""
    for rule in VALIDATION_RULES:
        if rule.rule_id == rule_id:
            return rule
    raise ValueError(f"Validation rule not found: {rule_id}")