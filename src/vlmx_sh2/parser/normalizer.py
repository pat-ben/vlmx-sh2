"""
PARSING STAGE 0/8: Normalization

Pre-tokenization text processing.
Prepares raw input for tokenization by expanding macros and validating text.

This stage operates on raw strings and performs text-level transformations
before the input is broken into tokens.
"""

from ..words.macros import expand_macros


class Normalizer:
    """
    Text normalization before tokenization.
    
    Responsibilities:
    - Expand command macros (cc → create company)
    - Validate text format (blocking errors)
    - Future: Unicode normalization, whitespace cleanup
    
    This stage ensures the text is in the correct format before
    structural analysis begins.
    """
    
    @staticmethod
    def normalize(input_text: str) -> str:
        """
        Normalize raw input text for parsing.
        
         """
        # Step 1: Expand command macros    
        text = expand_macros(input_text)
        
        # Step 2: Text validation (BLOCKING)        
        Normalizer._validate_text(text)
                
        return text
    

    @staticmethod
    def _validate_text(text: str) -> None:
        """
        Validate text format (blocking validation).
        
        Checks for fundamental text-level issues that prevent parsing:
        - Empty input
        - Excessive length
        - Invalid characters (future)
        
        Args:
            text: Text to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Check 1: Empty input
        if not text or not text.strip():
            raise ValueError("Command cannot be empty")
        
        # Check 2: Maximum length (prevent DoS, memory issues)
        MAX_LENGTH = 10000
        if len(text) > MAX_LENGTH:
            raise ValueError(f"Command exceeds maximum length ({MAX_LENGTH} characters)")
        
        # Future validation checks:
        # - Invalid control characters
        # - Null bytes
        # - Invalid UTF-8 sequences