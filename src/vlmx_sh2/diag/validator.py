# File: src/vlmx_sh2/diagnostics/validator.py
"""
Two-tier validator for comprehensive diagnostics.

Supports both text-level (pre-tokenization) and token-level (post-tokenization)
validation with fine-grained position tracking.
"""

from typing import Any, List, Union, Protocol, TypeVar, TypedDict, TYPE_CHECKING
from ..core.models.validation import ValidationContext
from ..core.models.parser.token import Token
from ..core.models.parser.classification import ClassifiedToken
from ..core.models.parser.recognition import RecognizedToken
from ..core.enums import IssueStage
from .rules import get_text_rules_for_stage, get_token_rules_for_stage

if TYPE_CHECKING:
    from .suggestions import SuggestionEngine
    from ..core.models.context import Context
    from ..core.models.validation.rule import ValidationRule


class ValidationInputs(TypedDict, total=False):
    """Common validation input parameters."""
    text: str
    tokens: List[Union[Token, ClassifiedToken, RecognizedToken]]
    suggestion_engine: 'SuggestionEngine'
    context: 'Context'


class TokenLike(Protocol):
    """Protocol for any token-like object that has a text attribute."""
    text: str


# Type alias for any token type used in the pipeline
AnyToken = Union[Token, ClassifiedToken, RecognizedToken]

# TypeVar for bounded token types
TokenType = TypeVar('TokenType', bound=TokenLike)


class Validator:
    """
    Two-tier validator supporting comprehensive diagnostic reporting.
    
    Validation Architecture:
    
    1. Text-Level Validation (Pre-tokenization):
       - Validates raw text input before any parsing
       - Always blocking (fail fast on fundamental issues)
       - Position always 0 (no tokens exist yet)
       - Examples: empty command, max length, encoding issues
    
    2. Token-Level Validation (Post-tokenization):
       - Validates individual tokens with position metadata
       - Non-blocking by default (collect ALL errors)
       - Position extracted from token metadata
       - Examples: unclosed quotes, invalid syntax, unknown words
    
    VALIDATION PHILOSOPHY:
    - Text-level: "Fail fast" - can't proceed if we can't read input
    - Token-level: "Collect all errors" - show user everything wrong at once
    - Always run ALL validation rules to collect comprehensive diagnostics
    """
    
    @staticmethod
    def validate_text(
        stage: IssueStage,
        context: ValidationContext,
        text: str,
        **kwargs: Any
    ) -> bool:
        """
        Run text-level validation rules for a given stage.
        
        Text-level validation runs BEFORE tokenization on raw input.
        All text-level rules are blocking (fail fast philosophy).
        
        Args:
            stage: Which parsing stage to validate
            context: ValidationContext for logging issues
            text: Raw input text to validate
            **kwargs: Additional inputs for validation rules
            
        Returns:
            True if no blocking errors found (processing can continue)
            False if any blocking error found (processing must stop)
            
        Example:
            >>> context = ValidationContext()
            >>> Validator.validate_text(IssueStage.TOKENIZER, context, text="create company")
            True
            
            >>> context = ValidationContext()
            >>> Validator.validate_text(IssueStage.TOKENIZER, context, text="")
            False  # BLOCKING error (empty command) logged to context
        """
        rules = get_text_rules_for_stage(stage)
        has_blocking_error = False
        
        for rule in rules:
            try:
                # Run the validation check with text input
                is_valid = rule.check(text=text, **kwargs)
                
                if not is_valid:
                    # Log error to context without position information
                    context.add_error(
                        stage=stage,
                        message=rule.get_message(text=text, **kwargs),
                        error_code=rule.error_code,
                        suggestion=rule.get_suggestion(text=text, **kwargs)
                    )
                    
                    # Text-level rules are always blocking, but continue checking
                    # all rules to collect ALL errors
                    if rule.blocking:
                        has_blocking_error = True
                    
            except Exception as e:
                # Validation rule itself failed - treat as blocking
                context.add_error(
                    stage=stage,
                    message=f"Text validation rule '{rule.rule_id}' failed: {str(e)}",
                    error_code=f"vlmx::{stage.value}::text_validation_error"
                )
                has_blocking_error = True
        
        # Return False immediately on first failure (text-level is fail fast)
        return not has_blocking_error
    
    @staticmethod
    def _get_or_create_suggestion_engine(**kwargs: Any) -> 'SuggestionEngine':
        """
        Get suggestion engine from kwargs or create a new one.
        
        Args:
            **kwargs: May contain 'suggestion_engine' key
            
        Returns:
            SuggestionEngine instance
        """
        suggestion_engine = kwargs.get('suggestion_engine')
        if not suggestion_engine:
            from .suggestions import SuggestionEngine
            suggestion_engine = SuggestionEngine()
        return suggestion_engine
    
    @staticmethod
    def _build_error_context(
        rule: 'ValidationRule',
        token: TokenLike,
        position: int,
        **kwargs: Any
    ) -> dict:
        """
        Build error context dictionary for validation failures.
        
        Args:
            rule: The validation rule that failed
            token: The token that failed validation
            position: Token position in the command
            **kwargs: Additional context for error messages
            
        Returns:
            Dictionary with error context data
        """
        return {
            'token': token,
            'position': position,
            **kwargs
        }
    
    @staticmethod
    def validate_tokens(
        stage: IssueStage,
        context: ValidationContext,
        tokens: List[TokenType],
        **kwargs: Any
    ) -> bool:
        """
        Run token-level validation rules for a given stage.
        
        Token-level validation runs AFTER tokenization on any token type
        (Token, ClassifiedToken, or RecognizedToken). Most token-level rules 
        are non-blocking (collect all errors philosophy).
        
        Args:
            stage: Which parsing stage to validate
            context: ValidationContext for logging issues
            tokens: List of tokens to validate (any token type)
            **kwargs: Additional inputs for validation rules
            
        Returns:
            True if no blocking errors found (processing can continue)
            False if any blocking error found (processing must stop)
            
        Example:
            >>> context = ValidationContext()
            >>> tokens = [Token(text="create"), Token(text="company")]
            >>> Validator.validate_tokens(IssueStage.TOKENIZER, context, tokens=tokens)
            True
        """
        # Create suggestion engine once for this validation pass
        # This avoids recreating it for each unknown token
        suggestion_engine = Validator._get_or_create_suggestion_engine(**kwargs)
        kwargs['suggestion_engine'] = suggestion_engine
        
        rules = get_token_rules_for_stage(stage)
        has_blocking_error = False
        
        for rule in rules:
            try:
                # For token-level rules, we may validate individual tokens or all tokens
                # The rule's check function determines how to use the tokens
                for token in tokens:
                    is_valid = rule.check(token=token, tokens=tokens, **kwargs)
                    
                    if not is_valid:
                        # Log error using token text for position resolution
                        context.add_error_from_token(
                            token=token,
                            stage=stage,
                            message=rule.get_message(token=token, tokens=tokens, **kwargs),
                            error_code=rule.error_code,
                            suggestion=rule.get_suggestion(token=token, tokens=tokens, **kwargs)
                        )
                        
                        # Check if this is a rare blocking token-level error
                        if rule.blocking:
                            has_blocking_error = True
                        # Continue checking other tokens and rules to collect ALL errors
                        
            except Exception as e:
                # Validation rule itself failed - treat as blocking
                context.add_error(
                    stage=stage,
                    message=f"Token validation rule '{rule.rule_id}' failed: {str(e)}",
                    error_code=f"vlmx::{stage.value}::token_validation_error"
                )
                has_blocking_error = True
        
        # Return False only if a rare blocking token error was found
        return not has_blocking_error
    
