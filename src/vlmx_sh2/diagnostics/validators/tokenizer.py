# File: src/vlmx_sh2/diagnostics/validators/tokenizer.py
"""
Tokenizer validation rules.

Validates input text at the tokenizer stage, checking for:
- Empty commands
- (Future) Unclosed quotes
- (Future) Mismatched brackets

All validation issues are logged to ValidationContext for diagnostic reporting.
"""

from ...models.validation import ValidationContext
from ...enums import IssueStage


class TokenizerValidator:
    """
    Validates input text at tokenizer stage.
    
    Stateless validator that checks basic text structure before tokenization.
    Uses ValidationContext to log issues without raising exceptions.
    """
    
    @staticmethod
    def validate_empty_command(text: str, context: ValidationContext) -> bool:
        """
        Validate that command text is not empty.
        
        Args:
            text: Raw user input
            context: ValidationContext for error logging
            
        Returns:
            True if valid (not empty), False if invalid (empty)
            
        Logs error to context if command is empty.
        """
        if not text or not text.strip():
            context.add_error(
                stage=IssueStage.TOKENIZER,
                message="Command cannot be empty",
                position=0,
                error_code="vlmx::tokenizer::empty_command",
                suggestion="Try typing a command like 'create company' or 'show metadata'"
            )
            return False
        
        return True