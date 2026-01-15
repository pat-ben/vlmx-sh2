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
    """
    
    @staticmethod
    def validate(
        stage: IssueStage,
        context: ValidationContext,
        **inputs: Any
    ) -> bool:
        """
        Run all validation rules for a given stage.
        
        Args:
            stage: Which parsing stage to validate (uses IssueStage enum)
            context: ValidationContext for logging issues
            **inputs: Inputs required by validation rules (e.g., text, tokens)
            
        Returns:
            True if all validations pass, False if any fail
            
        Example:
            >>> context = ValidationContext()
            >>> Validator.validate(IssueStage.TOKENIZER, context, text="create company")
            True
            
            >>> context = ValidationContext()
            >>> Validator.validate(IssueStage.TOKENIZER, context, text="")
            False  # Error logged to context
        """
        rules = get_rules_for_stage(stage)
        all_valid = True
        
        for rule in rules:
            try:
                # Run the validation check
                is_valid = rule.check(**inputs)
                
                if not is_valid:
                    # Log error to context
                    context.add_error(
                        stage=stage,
                        message=rule.message,
                        position=rule.position,
                        error_code=rule.error_code,
                        suggestion=rule.suggestion
                    )
                    all_valid = False
                    
            except Exception as e:
                # Catch any validation errors and log them
                context.add_error(
                    stage=stage,
                    message=f"Validation rule '{rule.rule_id}' failed: {str(e)}",
                    position=0,
                    error_code=f"vlmx::{stage.value}::validation_error"
                )
                all_valid = False
        
        return all_valid