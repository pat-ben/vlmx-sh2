"""
PARSING STAGE 4/6: Interpretation

Post-recognition intelligence layer.
Interprets user intent and corrects/infers missing information.

This stage operates on recognized tokens and makes the DSL "smart" by:
- Correcting typos with fuzzy matching
- Inferring missing words from context
- Making the command interface more forgiving
"""

from typing import List, Optional, Tuple
from ..models.parser import RecognizedToken, InterpretedToken
from ..models.context import Context
from ..enums.parser import TokenType, Operator
from ..enums.core import ContextLevel
from ..models.words import WordType, FieldWord, EntityWord, ActionWord, Word


class Interpreter:
    """
    Intelligence layer for interpreting user intent.
    
    Operates on recognized tokens to make the DSL more intelligent:
    - Fuzzy matching: Corrects typos and spelling mistakes
    - Expression inference: Adds missing action/entity words in ORG context
    
    This stage bridges the gap between what users type and what
    the system needs to execute commands successfully.
    """
    
    # Lazy-loaded class-level word registry cache
    _word_registry: Optional[dict] = None
    
    @classmethod
    def _get_word_registry(cls) -> dict:
        """Get word registry, loading it lazily if needed."""
        if cls._word_registry is None:
            from ..words.registry import WORD_REGISTRY
            cls._word_registry = WORD_REGISTRY
        return cls._word_registry
    
    # =============================================================================
    # Public API - Main Entry Point
    # =============================================================================
    
    @classmethod
    def interpret(
        cls, 
        recognized_tokens: List[RecognizedToken],
        context: Context
    ) -> List[InterpretedToken]:
        """
        Interpret recognized tokens with intelligence.
        
        Applies fuzzy matching and expression inference for intelligent parsing.
        
        Processing order:
        1. Fuzzy matching (correct typos in UNKNOWN tokens)
        2. Expression inference (inject missing words in ORG context)
        
        Args:
            recognized_tokens: Tokens from recognizer stage
            
        Returns:
            InterpretedToken list with correction/inference metadata
            
        Examples:
            >>> # Expression inference
            >>> interpret(["currency", "=", "EUR"])  # At ORG level
            ["add", "organization", "currency", "=", "EUR"]
            
            >>> # Fuzzy matching
            >>> interpret(["compny", "name", "=", "ACME"])
            ["company", "name", "=", "ACME"]  # Fixed typo
       
        """
        # Convert to InterpretedToken (preserves all fields, adds new defaults)
        interpreted_tokens = [
            InterpretedToken(**token.model_dump()) 
            for token in recognized_tokens
        ]
        
        # Apply fuzzy matching to correct typos in UNKNOWN tokens
        interpreted_tokens = cls._correct_typos(interpreted_tokens)
        
        # Apply expression inference to add missing words
        interpreted_tokens = cls._inject_missing_words(interpreted_tokens, context)
        return interpreted_tokens
    
    # =============================================================================
    # Core Processing - Typo Correction & Word Injection
    # =============================================================================
    
    @classmethod
    def _correct_typos(
        cls, 
        tokens: List[InterpretedToken]
    ) -> List[InterpretedToken]:
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
            word_registry = cls._get_word_registry()
            for word_id in word_registry.keys():
                # Skip if length difference is too large (optimization)
                if abs(len(token.text) - len(word_id)) > 1:
                    continue
                    
                # Calculate case-insensitive Levenshtein distance
                distance = cls._levenshtein_distance(token_text_lower, word_id.lower())
                
                # If exactly 1 typo, correct it
                if distance == 1:
                    # Get the Word object from registry
                    word_obj = word_registry.get(word_id)
                    if word_obj:
                        # Store original before correction
                        token.original_text = token.text
                        token.was_corrected = True
                        
                        # Apply correction
                        token.text = word_id
                        token.token_type = TokenType.WORD
                        token.word = word_obj
                        break  # Take first match
        
        return tokens
    
    @classmethod
    def _inject_missing_words(
        cls, 
        tokens: List[InterpretedToken],
        context: Context
    ) -> List[InterpretedToken]:
        """
        Infer missing words based on patterns and context.
        
        Analyzes tokens to detect missing ActionWord and EntityWord, then injects
        them based on field patterns and operator context. Only operates in ORG
        context level.
        
        Context-aware rules:
        - At ORG level only: "field=value" → "add entity field=value"
        - Field lookup: Uses field.entity_models[0] to find corresponding entity
        - Action inference: field=value → "add", field= → "delete"
        
        Args:
            tokens: Recognized tokens
            
        Returns:
            Tokens with inferred words injected at the beginning
        """
        # 1. Check context — only ORG level
        if context.level != ContextLevel.ORG:
            return tokens
        
        # 2. Analyze tokens — what do we have?
        has_field, has_entity, has_action = cls._analyze_token_types(tokens)
        first_field_word = cls._find_first_field_word(tokens)
        
        # 3. Nothing to infer if no field word
        if not has_field or first_field_word is None:
            return tokens
        
        # 4. Build list of words to inject
        words_to_inject = []
        
        # 4a. Infer EntityWord if missing
        if not has_entity:
            entity_word = cls._infer_entity_from_field(first_field_word)
            if entity_word:
                words_to_inject.append(entity_word)
        
        # 4b. Infer ActionWord if missing
        if not has_action:
            action_word = cls._infer_action_from_operator(tokens)
            if action_word:
                words_to_inject.insert(0, action_word)  # Action goes first
        
        # 5. Create tokens and prepend
        if words_to_inject:
            inferred_tokens = [cls._create_inferred_token(word) for word in words_to_inject]
            return inferred_tokens + tokens
        
        return tokens
    
    # =============================================================================
    # Analysis Helpers - Token Inspection
    # =============================================================================
    
    @classmethod
    def _analyze_token_types(cls, tokens: List[InterpretedToken]) -> Tuple[bool, bool, bool]:
        """
        Analyze tokens to determine what word types are present.
        
        Args:
            tokens: List of recognized tokens to analyze
            
        Returns:
            Tuple of (has_field, has_entity, has_action)
        """
        has_field = False
        has_entity = False
        has_action = False
        
        for token in tokens:
            if token.token_type != TokenType.WORD or not token.word:
                continue
            word_type = token.word.word_type
            if word_type == WordType.FIELD:
                has_field = True
            elif word_type == WordType.ENTITY:
                has_entity = True
            elif word_type == WordType.ACTION:
                has_action = True
        
        return has_field, has_entity, has_action
    
    @classmethod
    def _find_first_field_word(cls, tokens: List[InterpretedToken]) -> Optional[FieldWord]:
        """
        Find the first FieldWord in the token list.
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            First FieldWord found, or None if none exist
        """
        for token in tokens:
            if token.token_type != TokenType.WORD or not token.word:
                continue
            if token.word.word_type == WordType.FIELD:
                return token.word
        return None
    
    # =============================================================================
    # Inference Helpers - Word Resolution
    # =============================================================================
    
    @classmethod
    def _infer_entity_from_field(cls, field_word: FieldWord) -> Optional[EntityWord]:
        """
        Infer EntityWord from a FieldWord using its entity_models.
        
        Args:
            field_word: FieldWord to infer entity from
            
        Returns:
            Corresponding EntityWord, or None if not found
        """
        if not field_word.entity_models:
            return None
            
        # Get the first entity model class this field belongs to
        target_entity_model = field_word.entity_models[0]
        
        # Find matching EntityWord in registry
        word_registry = cls._get_word_registry()
        for word in word_registry.values():
            if (word.word_type == WordType.ENTITY and 
                hasattr(word, 'entity_model') and
                word.entity_model == target_entity_model):
                return word
        return None
    
    @classmethod
    def _infer_action_from_operator(cls, tokens: List[InterpretedToken]) -> Optional[ActionWord]:
        """
        Infer ActionWord from operator patterns.
        
        Logic:
        - field = value → infer "add"
        - field = (no value) → infer "delete"
        
        Args:
            tokens: List of recognized tokens
            
        Returns:
            Inferred ActionWord, or None if cannot determine
        """
        # Find EQUALS operator
        equals_index = None
        for i, token in enumerate(tokens):
            if (token.token_type == TokenType.STRUCTURAL and 
                hasattr(token, 'operator') and
                token.operator == Operator.EQUAL):
                equals_index = i
                break
        
        if equals_index is None:
            return None
        
        # Check if there's a value after the equals
        has_value_after = (equals_index + 1 < len(tokens) and 
                          tokens[equals_index + 1].token_type == TokenType.VALUE)
        
        word_registry = cls._get_word_registry()
        if has_value_after:
            # field = value → infer "add"
            return word_registry.get("add")
        else:
            # field = (no value) → infer "delete"  
            return word_registry.get("delete")
    
    # =============================================================================
    # Token Creation
    # =============================================================================
    
    @classmethod
    def _create_inferred_token(cls, word: Word) -> InterpretedToken:
        """
        Create an InterpretedToken for an inferred word.
        
        Args:
            word: Word object to create token for
            
        Returns:
            InterpretedToken marked as inferred
        """
        return InterpretedToken(
            text=word.id,
            token_type=TokenType.WORD,
            word=word,
            was_inferred=True  # Mark as inferred
        )
    
    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    @staticmethod
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
            return cls._levenshtein_distance(s2, s1)
        
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