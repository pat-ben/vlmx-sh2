"""
PARSING STAGE 4/8: Interpretation

Post-recognition intelligence layer.
Interprets user intent and corrects/infers missing information.

This stage operates on recognized tokens and makes the DSL "smart" by:
- Correcting typos with fuzzy matching
- Inferring missing words from context
- Making the command interface more forgiving
"""

from typing import List
from ..models.parser import RecognizedToken
from ..models.validation import ValidationContext
from ..enums.parser import TokenType
from ..words import get_word


def _levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    
    Uses dynamic programming approach to find minimum edit distance.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Integer distance (number of single-character edits needed)
    """
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


class Interpreter:
    """
    Intelligence layer for interpreting user intent.
    
    Operates on recognized tokens to make the DSL more intelligent:
    - Fuzzy matching: Corrects typos and spelling mistakes
    - Expression inference: Adds missing words based on context
    
    This stage bridges the gap between what users type and what
    the system needs to execute commands successfully.
    
    CURRENT STATUS: Partial implementation
    Implemented:
    - Phase 1: Fuzzy matching (correct typos with Levenshtein distance)
    Future phases will add:
    - Phase 2: Expression inference (add missing action/entity words)
    """
    
    def __init__(self, word_registry: dict, context: ValidationContext):
        """
        Initialize interpreter with word registry and context.
        
        Args:
            word_registry: Complete word registry for lookups
            context: Validation context with current context level (SYS/ORG/APP)
        """
        self.word_registry = word_registry
        self.context = context
    
    def interpret(
        self, 
        recognized_tokens: List[RecognizedToken]
    ) -> List[RecognizedToken]:
        """
        Interpret recognized tokens with intelligence.
        
        Applies fuzzy matching to correct typos in UNKNOWN tokens.
        
        Processing order:
        1. Fuzzy matching (correct typos in UNKNOWN tokens)
        2. Expression inference (inject missing words based on context) - FUTURE
        
        Args:
            recognized_tokens: Tokens from recognizer stage
            
        Returns:
            Interpreted tokens (potentially modified with corrections/additions)
            
        Examples (future):
            >>> # Expression inference
            >>> interpret(["currency", "=", "EUR"])  # At ORG level
            ["add", "organization", "currency", "=", "EUR"]
            
            >>> # Fuzzy matching
            >>> interpret(["compny", "name", "=", "ACME"])
            ["company", "name", "=", "ACME"]  # Fixed typo
       
        """
        # Apply fuzzy matching to correct typos in UNKNOWN tokens
        interpreted_tokens = self._apply_fuzzy_matching(recognized_tokens)
        
        # FUTURE: Add expression inference
        # interpreted_tokens = self._infer_expressions(interpreted_tokens)
        return interpreted_tokens
    
    def _infer_expressions(
        self, 
        tokens: List[RecognizedToken]
    ) -> List[RecognizedToken]:
        """
        Infer missing words based on patterns and context.
        
        PLACEHOLDER: Future implementation will detect patterns like:
        - field=value without action → infer "add" or "update" based on context
        - entity without action → infer "create" or "show" based on context
        - Bare values → infer entity and action
        
        Context-aware rules:
        - At SYS level: "field=value" → "create company field=value"
        - At ORG level: "field=value" → "add organization field=value"
        - At APP level: Different inference rules
        
        Args:
            tokens: Recognized tokens
            
        Returns:
            Tokens with inferred words injected
        """
        # FUTURE: Implement expression inference
        # See design document for inference rules and patterns
        return tokens
    
    def _apply_fuzzy_matching(
        self, 
        tokens: List[RecognizedToken]
    ) -> List[RecognizedToken]:
        """
        Apply fuzzy matching to UNKNOWN tokens.
        
        Corrects typos in UNKNOWN tokens by matching against the word registry
        using Levenshtein distance. Only applies to tokens > 3 characters with
        exactly 1 character difference (distance == 1).
        
        Rules:
        - Apply to UNKNOWN tokens only
        - Skip words ≤ 3 characters 
        - Tolerate exactly 1 typo (Levenshtein distance == 1)
        - Case insensitive matching
        - Match against word_registry.keys() only
        
        Args:
            tokens: Recognized tokens
            
        Returns:
            Tokens with fuzzy-matched corrections applied
        """
        for token in tokens:
            # Skip non-UNKNOWN tokens
            if token.token_type != TokenType.UNKNOWN:
                continue
                
            # Skip short words (≤ 3 characters)
            if len(token.text) <= 3:
                continue
            
            token_text_lower = token.text.lower()
            
            # Check all words in registry for exact distance of 1
            for word_id in self.word_registry.keys():
                # Skip if length difference is too large (optimization)
                if abs(len(token.text) - len(word_id)) > 1:
                    continue
                    
                # Calculate case-insensitive Levenshtein distance
                distance = _levenshtein_distance(token_text_lower, word_id.lower())
                
                # If exactly 1 typo, correct it
                if distance == 1:
                    # Get the Word object from registry
                    word_obj = get_word(word_id)
                    if word_obj:
                        # Update token with correction
                        token.text = word_id
                        token.token_type = TokenType.WORD
                        token.word = word_obj
                        break  # Take first match
        
        return tokens


# =============================================================================
# Future Sub-Components (Not Implemented Yet)
# =============================================================================

class ExpressionInferencer:
    """
    FUTURE: Infers missing words based on patterns and context.
    
    Will analyze token patterns and inject missing words:
    - Missing action words (create, add, show, delete)
    - Missing entity words (company, organization, metadata)
    - Missing schema context
    
    Uses context level (SYS/ORG/APP) to make smart inferences.
    """
    pass


