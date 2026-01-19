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
    
    # TOKEN-LEVEL VALIDATION (Post-classification)
    ValidationRule(
        rule_id="unclosed_quote",
        stage=IssueStage.CLASSIFIER,
        validation_level="token",
        check=lambda token, **kwargs: not _has_unclosed_quote(token),
        error_code="vlmx::classifier::unclosed_quote",
        message="Quote opened but not closed",
        suggestion="Add closing quote to match the opening quote",
        blocking=False  # Non-blocking - collect all errors
    ),
    
    ValidationRule(
        rule_id="mismatched_brackets",
        stage=IssueStage.CLASSIFIER,
        validation_level="token",
        check=lambda token, tokens, **kwargs: _check_bracket_balance_per_token(token, tokens),
        error_code="vlmx::classifier::mismatched_brackets",
        message="Brackets are not balanced",
        suggestion="Ensure each opening bracket '[' or '(' has a matching closing bracket ']' or ')'",
        blocking=False  # Non-blocking
    ),
    
    
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


# =============================================================================
# VALIDATION HELPER FUNCTIONS
# =============================================================================

def _has_unclosed_quote(token) -> bool:
    """
    Check if token has an unclosed quote.
    
    Args:
        token: Token object with .text attribute
        
    Returns:
        True if token has unclosed quote, False otherwise
        
    Examples:
        >>> token = Token(text='"hello')
        >>> _has_unclosed_quote(token)
        True
        
        >>> token = Token(text='"hello"')
        >>> _has_unclosed_quote(token)
        False
    """
    text = token.text
    
    # Must be at least 1 character and start with quote
    if len(text) < 1:
        return False
    
    # Check for unclosed double quotes
    if text.startswith('"') and not text.endswith('"'):
        return True
    
    # Check for unclosed single quotes  
    if text.startswith("'") and not text.endswith("'"):
        return True
    
    return False


def _check_bracket_balance(tokens: List) -> bool:
    """
    Check if brackets are balanced across all tokens.
    
    Args:
        tokens: List of Token objects
        
    Returns:
        True if brackets are balanced, False otherwise
        
    Examples:
        >>> tokens = [Token(text='['), Token(text='test'), Token(text=']')]
        >>> _check_bracket_balance(tokens)
        True
        
        >>> tokens = [Token(text='['), Token(text='test')]  # Missing closing bracket
        >>> _check_bracket_balance(tokens)
        False
    """
    # Stack to track opening brackets
    stack = []
    
    # Mapping of closing to opening brackets
    bracket_pairs = {
        ']': '[',
        ')': '('
    }
    
    for token in tokens:
        text = token.text
        
        if text in ['[', '(']:
            # Opening bracket - push to stack
            stack.append(text)
        elif text in [']', ')']:
            # Closing bracket - check if it matches
            if not stack:
                # Closing bracket without opening
                return False
            
            last_opening = stack.pop()
            expected_opening = bracket_pairs[text]
            
            if last_opening != expected_opening:
                # Mismatched bracket types
                return False
    
    # All brackets should be matched (stack should be empty)
    return len(stack) == 0


def _check_bracket_balance_per_token(token, tokens: List) -> bool:
    """
    Check bracket balance only once per token list, reporting error on first token only.
    
    This avoids duplicate validation errors when called per token by the validator.
    Only reports the error for the first token in the list.
    
    Args:
        token: Current token being validated
        tokens: Complete list of tokens
        
    Returns:
        True if brackets are balanced OR this is not the first token
        False if brackets are unbalanced AND this is the first token
    """
    # Only check balance on the first token to avoid duplicate errors
    if tokens and token == tokens[0]:
        return _check_bracket_balance(tokens)
    
    # For all other tokens, return True to avoid duplicate error reporting
    return True