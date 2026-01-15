# File: src/vlmx_sh2/diagnostics/validator.py
"""
Unified validator for all parsing stages.

Runs validation rules from the rules registry for any given stage.
This replaces individual stage-specific validator classes.
"""

from typing import Any
from ..models.validation import ValidationContext
from ..enums import IssueStage
from .rules import get_rules_for_stage


class Validator:
    """
    Unified validator that runs stage-specific validation rules.
    
    Instead of separate validator classes (TokenizerValidator, ClassifierValidator, etc.),
    this single validator runs rules from the centralized rules registry based on
    the IssueStage enum.
    
    VALIDATION PHILOSOPHY:
    - Most validation errors are NON-BLOCKING: Log the error but continue parsing
    - Few validation errors are BLOCKING: Must stop because processing cannot continue
    - Always run ALL validation rules to collect ALL errors (even if blocking error found)
    - Return False only if BLOCKING error found
    
    This allows us to show users ALL errors in their command at once, not just the
    first error encountered.
    
    Example:
        Input: "creat compny name=ACME"
        Non-blocking approach:
          - Finds "creat" is unknown → logs error, continues
          - Finds "compny" is unknown → logs error, continues
          - Finds "name" is invalid field → logs error, continues
          - Returns all 3 errors to user
        
        Blocking approach (old):
          - Finds "creat" is unknown → stops immediately
          - User never learns about "compny" or "name" errors
    """
    
    @staticmethod
    def validate(
        stage: IssueStage,
        context: ValidationContext,
        **inputs: Any
    ) -> bool:
        """
        Run all validation rules for a given stage.
        
        IMPORTANT: This method runs ALL rules (to collect all errors), but only
        returns False if a BLOCKING error is found. Non-blocking errors are logged
        to the context but don't stop processing.
        
        Args:
            stage: Which parsing stage to validate
            context: ValidationContext for logging issues
            **inputs: Inputs required by validation rules
            
        Returns:
            True if no BLOCKING errors found (processing can continue)
            False if BLOCKING error found (processing must stop)
            
        Example:
            >>> context = ValidationContext()
            >>> Validator.validate(IssueStage.TOKENIZER, context, text="create company")
            True
            
            >>> context = ValidationContext()
            >>> Validator.validate(IssueStage.TOKENIZER, context, text="")
            False  # BLOCKING error (empty command) logged to context
        """
        rules = get_rules_for_stage(stage)
        has_blocking_error = False
        
        for rule in rules:
            try:
                # Run the validation check
                is_valid = rule.check(**inputs)
                
                if not is_valid:
                    # Log error to context (always log, regardless of blocking status)
                    context.add_error(
                        stage=stage,
                        message=rule.message,
                        position=rule.position,
                        error_code=rule.error_code,
                        suggestion=rule.suggestion
                    )
                    
                    # Check if this is a blocking error
                    if rule.blocking:
                        has_blocking_error = True
                    # Note: We DON'T break here - continue checking other rules
                    # to collect ALL errors, even if we found a blocking one
                    
            except Exception as e:
                # Validation rule itself failed - treat as blocking
                context.add_error(
                    stage=stage,
                    message=f"Validation rule '{rule.rule_id}' failed: {str(e)}",
                    position=0,
                    error_code=f"vlmx::{stage.value}::validation_error"
                )
                has_blocking_error = True
        
        # Return True if NO blocking errors (can continue)
        # Return False if ANY blocking error (must stop)
        return not has_blocking_error