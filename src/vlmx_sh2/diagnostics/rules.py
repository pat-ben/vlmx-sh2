# File: src/vlmx_sh2/diagnostics/rules.py
"""
Validation rules registry for two-tier validation architecture.

Central registry of all validation rules across parsing stages.
Rules are organized by IssueStage enum and validation level for easy management.

Two-Tier Validation Philosophy:

1. TEXT-LEVEL VALIDATION (Pre-tokenization):
   - Validates raw input before parsing begins
   - Always blocking (fail fast on fundamental issues) 
   - Position always 0 (no tokens exist yet)
   - Examples: empty command, max length, encoding issues
   - Philosophy: "Fail fast" - can't proceed if we can't read input

2. TOKEN-LEVEL VALIDATION (Post-tokenization):  
   - Validates individual tokens with position metadata
   - Non-blocking by default (collect ALL errors)
   - Position extracted from token metadata
   - Examples: unclosed quotes, invalid syntax, unknown words
   - Philosophy: "Collect all errors" - show user everything wrong at once

Each rule defines:
- What to check (validation logic)
- What error to report (message, code, suggestion) 
- Which stage and validation level it belongs to
- Whether it's blocking (rare for token-level rules)
"""

from typing import List
from ..models.validation import ValidationRule
from ..enums import IssueStage


# =============================================================================
# VALIDATION RULES REGISTRY
# =============================================================================

VALIDATION_RULES: List[ValidationRule] = [
    # ==================== TOKENIZER STAGE ====================
    
    # TEXT-LEVEL VALIDATION (Pre-tokenization)
    ValidationRule(
        rule_id="empty_command",
        stage=IssueStage.TOKENIZER,
        validation_level="text",
        check=lambda text, **kwargs: bool(text and text.strip()),
        error_code="vlmx::tokenizer::empty_command",
        message="Command cannot be empty",
        suggestion="Try typing a command like 'create company' or 'show metadata'",
        position=0,
        blocking=True  # Text-level validation is always blocking
    ),
    
    # Example text-level rules (not yet implemented):
    # 
    # ValidationRule(
    #     rule_id="max_length_exceeded",
    #     stage=IssueStage.TOKENIZER,
    #     validation_level="text",
    #     check=lambda text, **kwargs: len(text) <= 10000,
    #     error_code="vlmx::input::max_length",
    #     message="Command exceeds maximum length (10,000 characters)",
    #     suggestion="Break your command into smaller parts",
    #     blocking=True  # Text-level validation is always blocking
    # ),
    #
    # ValidationRule(
    #     rule_id="invalid_encoding",
    #     stage=IssueStage.TOKENIZER,
    #     validation_level="text", 
    #     check=lambda text, **kwargs: all(ord(c) < 127 for c in text),
    #     error_code="vlmx::input::invalid_encoding",
    #     message="Command contains non-ASCII characters",
    #     suggestion="Use only ASCII characters in commands",
    #     blocking=True  # Text-level validation is always blocking
    # ),
    
    # TOKEN-LEVEL VALIDATION (Post-tokenization)
    # Example token-level rules (not yet implemented):
    #
    # ValidationRule(
    #     rule_id="unclosed_quote",
    #     stage=IssueStage.TOKENIZER,
    #     validation_level="token",
    #     check=lambda token, **kwargs: not (
    #         token.text.startswith('"') and not token.text.endswith('"')
    #     ),
    #     error_code="vlmx::tokenizer::unclosed_quote",
    #     message="Quote opened but not closed",
    #     suggestion="Add closing quote",
    #     blocking=False  # Token-level validation is non-blocking by default
    # ),
    # 
    # ValidationRule(
    #     rule_id="mismatched_brackets",
    #     stage=IssueStage.TOKENIZER,
    #     validation_level="token",
    #     check=lambda token, tokens, **kwargs: _check_balanced_brackets(tokens),
    #     error_code="vlmx::tokenizer::mismatched_brackets",
    #     message="Opening bracket without closing bracket",
    #     suggestion="Add closing bracket ]",
    #     blocking=False  # Token-level validation is non-blocking by default
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
    """Get all validation rules for a specific parsing stage (both text and token level)."""
    return [rule for rule in VALIDATION_RULES if rule.stage == stage]


def get_text_rules_for_stage(stage: IssueStage) -> List[ValidationRule]:
    """Get text-level validation rules for a specific parsing stage."""
    return [rule for rule in VALIDATION_RULES 
            if rule.stage == stage and rule.validation_level == "text"]


def get_token_rules_for_stage(stage: IssueStage) -> List[ValidationRule]:
    """Get token-level validation rules for a specific parsing stage."""
    return [rule for rule in VALIDATION_RULES 
            if rule.stage == stage and rule.validation_level == "token"]


def get_rule_by_id(rule_id: str) -> ValidationRule:
    """Get a specific validation rule by its ID."""
    for rule in VALIDATION_RULES:
        if rule.rule_id == rule_id:
            return rule
    raise ValueError(f"Validation rule not found: {rule_id}")