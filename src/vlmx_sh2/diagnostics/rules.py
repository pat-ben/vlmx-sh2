# File: src/vlmx_sh2/diagnostics/rules.py
"""
Validation rules registry.

Central registry of all validation rules across parsing stages.
Rules are organized by IssueStage enum for easy management.

Each rule defines:
- What to check (validation logic)
- What error to report (message, code, suggestion)
- Which stage it belongs to
- Whether it's blocking (stops stage) or non-blocking (logs but continues)

BLOCKING vs NON-BLOCKING:
- blocking=True: Fatal error that prevents stage from continuing
  Example: Empty command (can't tokenize nothing)
  
- blocking=False: Error logged but stage can continue processing
  Example: Unclosed quote (can still extract tokens we have)
  
Most rules should be non-blocking to collect ALL errors in one pass.
Only mark as blocking if the stage truly cannot proceed.
"""

from typing import List
from ..models.validation import ValidationRule
from ..enums import IssueStage


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
        position=0,
        blocking=True  # Empty command is BLOCKING - can't tokenize nothing
    ),
    
    # Future tokenizer rules (examples - not yet implemented):
    # 
    # ValidationRule(
    #     rule_id="unclosed_quote",
    #     stage=IssueStage.TOKENIZER,
    #     check=...,
    #     error_code="vlmx::tokenizer::unclosed_quote",
    #     message="Quote opened but not closed",
    #     suggestion="Add closing quote",
    #     blocking=False  # NON-BLOCKING - can still extract tokens
    # ),
    # 
    # ValidationRule(
    #     rule_id="mismatched_brackets",
    #     stage=IssueStage.TOKENIZER,
    #     check=...,
    #     error_code="vlmx::tokenizer::mismatched_brackets",
    #     message="Opening bracket without closing bracket",
    #     suggestion="Add closing bracket ]",
    #     blocking=False  # NON-BLOCKING - can still extract tokens
    # ),
    
    
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