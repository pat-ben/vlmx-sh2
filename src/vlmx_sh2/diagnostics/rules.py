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
from ..models.words import WordType
from ..enums import IssueStage, TokenType, ValueContext, TokenClass


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
    
    # TOKEN-LEVEL VALIDATION (Post-recognition)
    ValidationRule(
        rule_id="unknown_word",
        stage=IssueStage.RECOGNIZER,
        validation_level="token",
        check=lambda token, **kwargs: not (
            token.token_type == TokenType.UNKNOWN and 
            getattr(token, 'token_class', None) == TokenClass.TEXT
        ),
        error_code="vlmx::recognizer::unknown_word",
        message=lambda token, **kwargs: f"Unrecognized word: '{token.text}'",
        suggestion=lambda token, **kwargs: _get_unknown_word_suggestion(token, **kwargs),
        blocking=False  # Non-blocking - collect all errors
    ),
    
    ValidationRule(
        rule_id="orphaned_schema_value",
        stage=IssueStage.RECOGNIZER,
        validation_level="token",
        check=lambda token, tokens, **kwargs: not _is_orphaned_schema_value(token, tokens),
        error_code="vlmx::recognizer::orphaned_schema_value",
        message="Quoted value without action or schema word before it",
        suggestion="Add an action (create, delete) or schema word (company, fund) before the quoted value",
        blocking=True  # Blocking - unclear what to do with orphaned value
    ),

    ValidationRule(
        rule_id="orphaned_field_value",
        stage=IssueStage.RECOGNIZER,
        validation_level="token",
        check=lambda token, tokens, **kwargs: not _is_orphaned_field_value(token, tokens),
        error_code="vlmx::recognizer::orphaned_field_value",
        message="Value after operator but no field name before it",
        suggestion="Add a field name before the operator (e.g., 'currency=...' or 'vision=...')",
        blocking=True  # Blocking - unclear what field this value belongs to
    ),

    ValidationRule(
        rule_id="low_confidence_word",
        stage=IssueStage.RECOGNIZER,
        validation_level="token",
        check=lambda token, **kwargs: token.confidence >= 50.0 or token.token_type == TokenType.UNKNOWN,
        error_code="vlmx::recognizer::low_confidence",
        message=lambda token, **kwargs: f"Low confidence recognizing '{token.text}' as {token.word.id if token.word else 'value'}",
        suggestion="Consider being more specific or checking spelling",
        blocking=False  # Non-blocking - informational
    ),

    ValidationRule(
        rule_id="value_without_context",
        stage=IssueStage.RECOGNIZER,
        validation_level="token",
        check=lambda token, **kwargs: not (token.token_type == TokenType.VALUE and token.value_context is None),
        error_code="vlmx::recognizer::value_no_context",
        message="Value token classified without proper context (internal parser issue)",
        suggestion="This indicates a parser bug - please report with the command you used",
        blocking=False  # Non-blocking - but indicates parser issue
    ),
    
    
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
    
    Works with both Token (pre-classification) and ClassifiedToken (post-classification) objects.
    For ClassifiedToken: If was_quoted=True, quotes were successfully matched and stripped.
    For Token: Check if text has unmatched quotes.
    
    Args:
        token: Token or ClassifiedToken object with .text attribute
        
    Returns:
        True if token has unclosed quote, False otherwise
        
    Examples:
        >>> token = Token(text='"hello')
        >>> _has_unclosed_quote(token)
        True
        
        >>> classified_token = ClassifiedToken(text='hello', token_class=TokenClass.TEXT, was_quoted=True)
        >>> _has_unclosed_quote(classified_token)
        False  # Successfully matched quotes were stripped
    """
    # If it was classified with was_quoted=True, quotes were successfully matched and stripped
    if hasattr(token, 'was_quoted') and token.was_quoted:
        return False  # Quotes were properly closed and stripped
    
    # Check if it looks like an unclosed quote in the text
    text = token.text
    if len(text) < 2:
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
    
    Works with both Token (pre-classification) and ClassifiedToken (post-classification) objects.
    Only considers tokens classified as BRACKET or tokens with bracket text.
    
    Args:
        tokens: List of Token or ClassifiedToken objects
        
    Returns:
        True if brackets are balanced, False otherwise
        
    Examples:
        >>> tokens = [Token(text='['), Token(text='test'), Token(text=']')]
        >>> _check_bracket_balance(tokens)
        True
        
        >>> classified = [ClassifiedToken(text='[', token_class=TokenClass.BRACKET), 
        ...               ClassifiedToken(text='test', token_class=TokenClass.TEXT)]
        >>> _check_bracket_balance(classified)
        False  # Missing closing bracket
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
        
        # For ClassifiedToken, only process if it's actually a bracket
        if hasattr(token, 'token_class'):
            from vlmx_sh2.enums import TokenClass
            if token.token_class != TokenClass.BRACKET:
                continue  # Skip non-bracket classified tokens
        
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


def _is_orphaned_schema_value(token, tokens: List) -> bool:
    """
    Check if a schema value (quoted value with SCHEMA context) is orphaned.
    
    A schema value is orphaned if it appears without an action or schema word before it.
    This catches errors like: "ACME" currency=EUR (missing action/schema)
    
    Args:
        token: Current RecognizedToken being validated
        tokens: Complete list of RecognizedToken objects
        
    Returns:
        True if token is an orphaned schema value, False otherwise
        
    Examples:
        >>> # Good: create company "ACME" 
        >>> tokens = [action_token, schema_token, value_token]
        >>> _is_orphaned_schema_value(value_token, tokens)
        False
        
        >>> # Bad: "ACME" currency=EUR
        >>> tokens = [value_token, field_token, ...]
        >>> _is_orphaned_schema_value(value_token, tokens)
        True  # No action/schema before quoted value
    """
    # Only check schema values
    if not (token.token_type == TokenType.VALUE and 
            token.value_context == ValueContext.SCHEMA):
        return False  # Not a schema value, not orphaned
    
    # Find current token position
    try:
        current_index = tokens.index(token)
    except ValueError:
        return False  # Token not found in list
    
    # If it's the first token, it's definitely orphaned
    if current_index == 0:
        return True
    
    # Check the previous token
    prev_token = tokens[current_index - 1]
    
    # Schema values should be preceded by action or schema words
    if prev_token.token_type == TokenType.WORD:
        if (prev_token.word_type == WordType.ACTION or 
            prev_token.word_type == WordType.SCHEMA):
            return False  # Not orphaned - has proper action/schema word
    
    # No valid action/schema word found before this schema value
    return True


# =============================================================================
# RECOGNIZER VALIDATION HELPERS
# =============================================================================

def _get_unknown_word_suggestion(token, **kwargs) -> str:
    """
    Generate suggestion for unknown word token.
    
    Uses SuggestionEngine to provide context-aware suggestions.
    Falls back to generic help if no good suggestions available.
    
    Args:
        token: RecognizedToken with token_type=UNKNOWN
        **kwargs: Additional context (may include 'tokens' for full context)
        
    Returns:
        Suggestion string
    """
    # Get suggestion engine (create instance if needed)
    # Note: Could be passed in kwargs for efficiency
    suggestion_engine = kwargs.get('suggestion_engine')
    if not suggestion_engine:
        from ..diagnostics.suggestions import SuggestionEngine
        suggestion_engine = SuggestionEngine()
    
    # Generate suggestions for this token
    suggestions = suggestion_engine.get_token_suggestions(token.text)
    
    if suggestions:
        # Return top suggestion with alternatives
        if len(suggestions) > 1:
            return f"Did you mean '{suggestions[0]}'? Other options: {', '.join(suggestions[1:3])}"
        else:
            return f"Did you mean '{suggestions[0]}'?"
    else:
        # No good suggestions
        return "Check spelling or use 'help' to see available commands"


def _is_orphaned_field_value(token, tokens: List) -> bool:
    """
    Check if token is a field value after operator but without field name.
    
    Field values MUST follow pattern: FieldWord OPERATOR VALUE
    
    Valid examples:
    - currency=EUR
    - vision="Our vision"
    
    Invalid examples:
    - =EUR (missing field name before operator)
    - currency EUR (missing operator)
    
    Args:
        token: Current token to check
        tokens: All tokens in the list
        
    Returns:
        True if token is orphaned field value, False otherwise
    """
    # Only check VALUE tokens with FIELD context
    if token.token_type != TokenType.VALUE or token.value_context != ValueContext.FIELD:
        return False
    
    # Find this token's position
    try:
        token_index = token.token_index
    except AttributeError:
        try:
            token_index = tokens.index(token)
        except ValueError:
            return False
    
    # Need at least 2 tokens before this one (field + operator)
    if token_index < 2:
        return True  # Not enough tokens before - orphaned
    
    # Check pattern: should be FieldWord OPERATOR VALUE
    operator_token = tokens[token_index - 1]
    field_token = tokens[token_index - 2]
    
    # Previous token should be OPERATOR
    if not (hasattr(operator_token, 'token_class') and 
            operator_token.token_class == TokenClass.OPERATOR):
        return True  # Not after operator - orphaned
    
    # Token before operator should be FieldWord
    if not (hasattr(field_token, 'is_field_word') and field_token.is_field_word):
        return True  # No field name before operator - orphaned
    
    return False  # Has proper context