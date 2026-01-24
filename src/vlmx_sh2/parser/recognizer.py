"""
PARSING STAGE 3/6: Semantic Recognition

Performs semantic classification of structurally classified tokens.
Converts ClassifiedToken objects to RecognizedToken objects by:
- Recognizing words from registry (actions, entities, fields, schemas)
- Handling aliases (del → delete, rm → delete, etc.)
- Classifying values based on context (schema names, field values)
- Copying structural information (operators, brackets) from Classifier

Does NOT handle command/filter splitting (that's Splitter's job).
"""

from typing import Dict, List, Optional
from ..models.parser import ClassifiedToken, RecognizedToken
from ..models.validation import ValidationContext
from ..models.words import Word, WordType
from ..words import get_all_words, get_word
from ..diagnostics import Validator
from vlmx_sh2.enums import TokenClass, TokenType, ValueContext, IssueStage, QueryWord


class Recognizer:
    """
    PARSING STAGE 3/6: Semantic Recognition
    
    Adds semantic meaning to TEXT tokens from Classifier.
    OPERATOR/BRACKET tokens are passed through as STRUCTURAL tokens
    (they were already fully classified by the Classifier).
    
    Responsibilities:
    - TEXT → WORD (if in registry)
    - TEXT → VALUE (if in value context)  
    - TEXT → QUERY (if query keyword)
    - TEXT → UNKNOWN (if not recognized)
    - OPERATOR/BRACKET → STRUCTURAL (pass through)
    """
    
    # Query keywords (already normalized by Classifier)
    # Classifier handles symbol normalization: & → and, | → or
    _QUERY_WORDS: Dict[str, QueryWord] = {
        "and": QueryWord.AND,
        "or": QueryWord.OR,
    }
    
    # Lazy-loaded class-level cache
    _word_registry: Optional[Dict[str, Word]] = None
    _alias_to_word: Optional[Dict[str, str]] = None
    _words_by_type: Optional[Dict[WordType, List[Word]]] = None
    
    @classmethod
    def _get_word_registry(cls) -> Dict[str, Word]:
        """Get word registry with lazy loading."""
        if cls._word_registry is None:
            cls._word_registry = get_all_words()
        return cls._word_registry
    
    @classmethod
    def _get_alias_map(cls) -> Dict[str, str]:
        """Get alias map with lazy loading."""
        if cls._alias_to_word is None:
            cls._alias_to_word = cls._build_alias_map()
        return cls._alias_to_word
    
    @classmethod
    def _get_words_by_type(cls) -> Dict[WordType, List[Word]]:
        """Get words by type with lazy loading."""
        if cls._words_by_type is None:
            cls._words_by_type = cls._group_words_by_type()
        return cls._words_by_type
    
    # =============================================================================
    # Public API - Main Entry Point
    # =============================================================================
    
    @classmethod
    def recognize(
        cls, 
        classified_tokens: List[ClassifiedToken], 
        context: ValidationContext
    ) -> List[RecognizedToken]:
        """
        Recognize words and classify values from classified tokens.
        
        Example transformation:
            Input:  "create company ACME currency=EUR"
            
            Classified tokens:
                [ClassifiedToken(text="create", token_class=TEXT),
                 ClassifiedToken(text="company", token_class=TEXT),
                 ClassifiedToken(text="ACME", token_class=TEXT, was_quoted=False),
                 ClassifiedToken(text="=", token_class=OPERATOR, operator=EQUALS),
                 ClassifiedToken(text="EUR", token_class=TEXT)]
            
            Recognized tokens:
                [RecognizedToken(text="create", token_type=WORD, word=ActionWord(...)),
                 RecognizedToken(text="company", token_type=WORD, word=SchemaWord(...)),
                 RecognizedToken(text="ACME", token_type=VALUE, value_context=SCHEMA),
                 RecognizedToken(text="=", token_type=STRUCTURAL, operator=EQUALS),
                 RecognizedToken(text="EUR", token_type=VALUE, value_context=FIELD)]
        
        Processing:
        1. For TEXT tokens: Try word recognition, then value classification
        2. For OPERATOR/BRACKET tokens: Copy structural info as-is
        3. Provide suggestions for UNKNOWN tokens
        
        Args:
            classified_tokens: List of ClassifiedToken from classifier
            context: ValidationContext for error reporting
            
        Returns:
            List of RecognizedToken objects with semantic classification
        """
        recognized_tokens = []
        
        for i, classified_token in enumerate(classified_tokens):
            recognized_token = cls._recognize_single_token(
                classified_token, 
                recognized_tokens, 
                i
            )
            recognized_tokens.append(recognized_token)
        
        # Token-level validation
        # - Validates semantic issues (unknown words, invalid values)
        # - Non-blocking by default (collect ALL errors)
        Validator.validate_tokens(IssueStage.RECOGNIZER, context, tokens=recognized_tokens)
        
        return recognized_tokens
    
    # =============================================================================
    # Initialization Helpers
    # =============================================================================
    
    @classmethod
    def _build_alias_map(cls) -> Dict[str, str]:
        """
        Build mapping from lowercase aliases to canonical word IDs.
        
        Now handles aliases from ALL word types (ACTION, SCHEMA, ENTITY, FIELD).
        
        Example: {
            "delete": "delete", "del": "delete", "rm": "delete",    # ActionWord
            "co": "company",                                        # SchemaWord
            "org": "organization",                                  # EntityWord
        }
        """
        alias_map = {}
        word_registry = cls._get_word_registry()
        for word_id, word in word_registry.items():
            # Add word ID itself
            alias_map[word_id.lower()] = word_id
            
            # Add aliases from any word type that has them
            if hasattr(word, 'aliases') and word.aliases:
                for alias in word.aliases:
                    alias_map[alias.lower()] = word_id
        
        return alias_map
    
    @classmethod
    def _group_words_by_type(cls) -> Dict[WordType, List[Word]]:
        """
        Group words by their type for quick access.
        
        Returns:
            Dictionary mapping WordType → List of Words
        """
        groups = {wt: [] for wt in WordType}
        word_registry = cls._get_word_registry()
        for word in word_registry.values():
            groups[word.word_type].append(word)
        return groups
    
    # =============================================================================
    # Token Recognition Dispatch
    # =============================================================================
    
    @classmethod
    def _recognize_single_token(
        cls,
        classified_token: ClassifiedToken,
        recognized_tokens: List[RecognizedToken],
        current_position: int
    ) -> RecognizedToken:
        """
        Recognize a single token from classifier output.
        
        Classifier has already done structural classification (TEXT/OPERATOR/BRACKET).
        Recognizer only adds semantic meaning to TEXT tokens.
        
        Args:
            classified_token: Token from classifier
            recognized_tokens: Previous tokens for context
            current_position: Index in token array
            
        Returns:
            RecognizedToken with semantic classification
        """
        if classified_token.token_class == TokenClass.TEXT:
            # TEXT tokens need semantic classification
            return cls._recognize_text_token(classified_token, recognized_tokens, current_position)
        else:
            # OPERATOR and BRACKET tokens are already complete
            return cls._create_token(classified_token, TokenType.STRUCTURAL)
    
    @classmethod
    def _recognize_text_token(
        cls,
        classified_token: ClassifiedToken,
        recognized_tokens: List[RecognizedToken],
        current_position: int
    ) -> RecognizedToken:
        """
        Perform semantic recognition on TEXT tokens.
        
        Attempts to classify TEXT tokens as VALUES or WORDS.
        Falls back to UNKNOWN if no classification matches.
        
        Args:
            classified_token: TEXT token from classifier
            recognized_tokens: Previous tokens for context
            current_position: Index in token array
            
        Returns:
            RecognizedToken with semantic classification
        """
        # Priority 1: Check if it's a value (context-dependent)
        value_context = cls._determine_value_context(
            classified_token, 
            recognized_tokens, 
            current_position
        )
        
        if value_context:
            return cls._create_token(classified_token, TokenType.VALUE, value_context=value_context)
        
        # Priority 2: Check if it's a query keyword (and/or)
        query_word = cls._match_query_word(classified_token.text)
        
        if query_word:
            return cls._create_token(classified_token, TokenType.QUERY, query_word=query_word)
        
        # Priority 3: Try word registry lookup
        word = cls._match_word_in_registry(classified_token.text)
        
        if word:
            return cls._create_token(classified_token, TokenType.WORD, word=word)
        
        # Fallback: Unknown token
        return cls._create_token(classified_token, TokenType.UNKNOWN)
    
    # =============================================================================
    # Recognition Methods - Token Type Matching
    # =============================================================================
    
    @classmethod
    def _match_word_in_registry(cls, token_text: str) -> Optional[Word]:
        """
        Recognize token as word from registry, handling aliases automatically.
        
        Args:
            token_text: Text to recognize
            
        Returns:
            Word object if matched, None otherwise
        """
        token_lower = token_text.lower()
        alias_map = cls._get_alias_map()
        
        # Try exact match (including aliases)
        if token_lower in alias_map:
            word_id = alias_map[token_lower]
            word = get_word(word_id)
            return word
        
        # No match
        return None
    
    @classmethod
    def _match_query_word(cls, text: str) -> Optional[QueryWord]:
        """
        Check if text is a query keyword (and/or).
        
        The Classifier has already normalized symbols to words:
        - & → and
        - | → or
        
        So we only check for the word forms.
        
        Args:
            text: Token text to check (already normalized by Classifier)
            
        Returns:
            QueryKeyword enum value if matched, None otherwise
        """
        return self._QUERY_WORDS.get(text.lower())
    
    
    # =============================================================================
    # Token Factory - RecognizedToken Construction
    # =============================================================================
    
    @classmethod
    def _create_token(
        cls,
        classified_token: ClassifiedToken,
        token_type: TokenType,
        word: Optional[Word] = None,
        value_context: Optional[ValueContext] = None,
        query_word: Optional[QueryWord] = None
    ) -> RecognizedToken:
        """
        Unified factory for creating RecognizedToken objects.
        
        Args:
            classified_token: Input token from classifier
            token_type: Semantic type (WORD, VALUE, QUERY, STRUCTURAL, UNKNOWN)
            word: Word object (for WORD tokens only)
            value_context: Value context (for VALUE tokens only)
            query_word: Query keyword (for QUERY tokens only)
            
        Returns:
            RecognizedToken with appropriate fields populated
        """
        return RecognizedToken(
            text=classified_token.text,
            token_class=classified_token.token_class,
            was_quoted=bool(classified_token.was_quoted),
            operator=classified_token.operator,
            bracket=classified_token.bracket,
            token_type=token_type,
            word=word,
            value_context=value_context,
            query_word=query_word
        )
    
    # =============================================================================
    # Utility Methods
    # =============================================================================
    
    @classmethod
    def get_words_by_type(cls, word_type: WordType) -> List[Word]:
        """
        Get all words of a specific type.
        
        Args:
            word_type: Type of words to retrieve
            
        Returns:
            List of words of the specified type
        """
        words_by_type = cls._get_words_by_type()
        return words_by_type.get(word_type, [])
    
    # =============================================================================
    # Value Context Classification (merged from ValueContextClassifier)
    # =============================================================================
    
    @classmethod
    def _determine_value_context(
        cls,
        classified_token: ClassifiedToken,
        recognized_tokens: List[RecognizedToken],
        current_position: int
    ) -> Optional[ValueContext]:
        """
        Determine if a token is a value and what context it has.
        
        Rules:
        1. Schema name: Quoted token after schema/action word
           Examples: company "ACME", delete "ACME"
        2. Field value: Token after operator (quoted or not)
           Examples: currency=EUR, vision="Our vision"
           
        Examples of token sequences:
            Input: "currency=EUR"
            Tokens: ["currency", "=", "EUR"]
            Classifications:
                - "currency": WORD (FieldWord)
                - "=": STRUCTURAL (OPERATOR)
                - "EUR": VALUE (FIELD context) ← detected by this rule
        
        Args:
            classified_token: Current token being classified
            recognized_tokens: Previously recognized tokens
            current_position: Position in token array
            
        Returns:
            ValueContext if token is a value, None otherwise
        """
        # Guard clause: First token cannot be a value
        if current_position == 0:
            return None
        
        prev_token = recognized_tokens[current_position - 1]
        
        # Rule 1: Schema name detection
        # Must be quoted and follow a schema or action word
        if cls._is_schema_name_value(classified_token, prev_token):
            return ValueContext.SCHEMA
        
        # Rule 2: Field value detection  
        # Any token following an operator
        if cls._is_field_value(prev_token):
            return ValueContext.FIELD
        
        return None
    
    @classmethod
    def _is_schema_name_value(cls, token: ClassifiedToken, prev_token: RecognizedToken) -> bool:
        """Check if token is a schema name value (quoted token after schema/action word)."""
        return (bool(token.was_quoted) and 
                bool(prev_token.is_word) and 
                bool(prev_token.is_schema_word or prev_token.is_action_word))
    
    @classmethod
    def _is_field_value(cls, prev_token: RecognizedToken) -> bool:
        """Check if previous token indicates current token should be a field value."""
        return prev_token.token_class == TokenClass.OPERATOR