"""
PARSING STAGE 3/7: Semantic Recognition

Performs semantic classification of structurally classified tokens.
Converts ClassifiedToken objects to RecognizedToken objects by:
- Recognizing words from registry (actions, entities, fields, schemas)
- Handling aliases (del → delete, etc.)
- Classifying values based on context (schema name, field values)
- Copying structural information (operators, brackets) from Classifier

"""

from typing import Dict, List, Optional

from vlmx_sh2.core.enums import (
    IssueStage,
    QueryWord,
    RangeWord,
    TokenClass,
    TokenType,
    ValueContext,
)

from ...diag import Validator
from ...core.models.parser import ClassifiedToken, RecognizedToken
from ...core.models.validation import ValidationContext
from ...core.models.words import Word, WordType
from ..words import get_all_words, get_word

# Query keywords (already normalized by Classifier)
# Classifier handles symbol normalization: & → and, | → or
_QUERY_WORDS: Dict[str, QueryWord] = {
    "and": QueryWord.AND,
    "or": QueryWord.OR,
}

# Range keywords (already normalized by Classifier)
# Classifier handles symbol normalization: .. → to
_RANGE_WORDS: Dict[str, RangeWord] = {
    "to": RangeWord.TO,
}

# Lazy-loaded module-level caches
_word_registry: Optional[Dict[str, Word]] = None
_alias_to_word: Optional[Dict[str, str]] = None
_words_by_type: Optional[Dict[WordType, List[Word]]] = None


# =============================================================================
# Public API - Main Entry Points
# =============================================================================


def recognize(
    classified_tokens: List[ClassifiedToken], context: ValidationContext
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
        recognized_token = _recognize_token(
            classified_token, recognized_tokens, i
        )
        recognized_tokens.append(recognized_token)

    # Token-level validation
    # - Validates semantic issues (unknown words, invalid values)
    # - Non-blocking by default (collect ALL errors)
    Validator.validate_tokens(
        IssueStage.RECOGNIZER, context, tokens=recognized_tokens
    )

    return recognized_tokens


def get_words_by_type(word_type: WordType) -> List[Word]:
    """
    Get all words of a specific type.
    """
    words = _get_words_by_type()
    return words.get(word_type, [])


# =============================================================================
# Private Helpers - Lazy Loading
# =============================================================================


def _get_word_registry() -> Dict[str, Word]:
    """Get word registry with lazy loading."""
    global _word_registry
    if _word_registry is None:
        _word_registry = get_all_words()
    return _word_registry


def _get_alias_map() -> Dict[str, str]:
    """Get alias map with lazy loading."""
    global _alias_to_word
    if _alias_to_word is None:
        _alias_to_word = _build_alias_map()
    return _alias_to_word


def _get_words_by_type() -> Dict[WordType, List[Word]]:
    """Get words by type with lazy loading."""
    global _words_by_type
    if _words_by_type is None:
        _words_by_type = _group_words_by_type()
    return _words_by_type


# =============================================================================
# Initialization Helpers
# =============================================================================


def _build_alias_map() -> Dict[str, str]:
    """
    Build mapping from lowercase aliases to canonical word IDs.
    Now handles aliases from ALL word types (ACTION, SCHEMA, ENTITY, FIELD).

    """
    alias_map = {}
    registry = _get_word_registry()
    for word_id, word in registry.items():
        # Add word ID itself
        alias_map[word_id.lower()] = word_id

        # Add aliases from any word type that has them
        if hasattr(word, "aliases") and word.aliases:
            for alias in word.aliases:
                alias_map[alias.lower()] = word_id

    return alias_map


def _group_words_by_type() -> Dict[WordType, List[Word]]:
    """
    Group words by their type for quick access.
    """
    groups = {wt: [] for wt in WordType}
    registry = _get_word_registry()
    for word in registry.values():
        groups[word.word_type].append(word)
    return groups


# =============================================================================
# Token Recognition Dispatch
# =============================================================================


def _recognize_token(
    classified_token: ClassifiedToken,
    recognized_tokens: List[RecognizedToken],
    current_position: int,
) -> RecognizedToken:
    """
    Recognize a single token from classifier output.
    Recognizer only adds semantic meaning to TEXT tokens.
    """
    if classified_token.token_class == TokenClass.TEXT:
        # TEXT tokens need semantic classification
        return _recognize_text_token(
            classified_token, recognized_tokens, current_position
        )
    else:
        # OPERATOR and BRACKET tokens are already complete
        return _create_token(classified_token, TokenType.STRUCTURAL)


def _recognize_text_token(
    classified_token: ClassifiedToken,
    recognized_tokens: List[RecognizedToken],
    current_position: int,
) -> RecognizedToken:
    """
    Perform semantic recognition on TEXT (only) tokens.
    Attempts to classify TEXT tokens as VALUES or WORDS.
    Falls back to UNKNOWN if no classification matches.
    """
    # Priority 1: Check if it's a value (context-dependent)
    value_context = _determine_value_context(
        classified_token, recognized_tokens, current_position
    )

    if value_context:
        return _create_token(
            classified_token, TokenType.VALUE, value_context=value_context
        )

    # Priority 2: Check if it's a query keyword (and/or)
    query_word = _match_query_word(classified_token.text)

    if query_word:
        return _create_token(
            classified_token, TokenType.QUERY, query_word=query_word
        )

    # Priority 3: Check if it's a range keyword (to/..)
    range_word = _match_range_word(classified_token.text)

    if range_word:
        return _create_token(
            classified_token, TokenType.QUERY, range_word=range_word
        )

    # Priority 4: Try word registry lookup
    word = _match_word_in_registry(classified_token.text)

    if word:
        return _create_token(classified_token, TokenType.WORD, word=word)

    # Fallback: Unknown token
    return _create_token(classified_token, TokenType.UNKNOWN)


# =============================================================================
# Recognition Methods - Token Type Matching
# =============================================================================


def _match_word_in_registry(token_text: str) -> Optional[Word]:
    """
    Recognize token as word from registry, handling aliases automatically.
    """
    token_lower = token_text.lower()
    alias_map = _get_alias_map()

    # Try exact match (including aliases)
    if token_lower in alias_map:
        word_id = alias_map[token_lower]
        word = get_word(word_id)
        return word

    # No match
    return None


def _match_query_word(text: str) -> Optional[QueryWord]:
    """
    Check if text is a query keyword (and/or).
    """
    return _QUERY_WORDS.get(text.lower())


def _match_range_word(text: str) -> Optional[RangeWord]:
    """
    Check if text is a range keyword (to/..).
    """
    return _RANGE_WORDS.get(text.lower())


# =============================================================================
# Token Factory - RecognizedToken Construction
# =============================================================================


def _create_token(
    classified_token: ClassifiedToken,
    token_type: TokenType,
    word: Optional[Word] = None,
    value_context: Optional[ValueContext] = None,
    query_word: Optional[QueryWord] = None,
    range_word: Optional[RangeWord] = None,
) -> RecognizedToken:
    """
    Unified factory for creating RecognizedToken objects.

    Args:
        classified_token: Input token from classifier
        token_type: Semantic type (WORD, VALUE, QUERY, STRUCTURAL, UNKNOWN)
        word: Word object (for WORD tokens only)
        value_context: Value context (for VALUE tokens only)
        query_word: Query keyword (for QUERY tokens only)
        range_word: Range keyword (for QUERY tokens only)

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
        query_word=query_word,
        range_word=range_word,
    )


# =============================================================================
# Value Context Classification
# =============================================================================


def _determine_value_context(
    classified_token: ClassifiedToken,
    recognized_tokens: List[RecognizedToken],
    current_position: int,
) -> Optional[ValueContext]:
    """
    Determine if a token is a Schema Name or Field value and what context it has.

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
    """
    # Guard clause: First token cannot be a value
    if current_position == 0:
        return None

    prev_token = recognized_tokens[current_position - 1]

    # Rule 1: Schema name detection
    # Must be quoted and follow a schema or action word
    if _is_schema_name_value(classified_token, prev_token):
        return ValueContext.SCHEMA

    # Rule 2: Field value detection
    # Any token following an operator
    if _is_field_value(prev_token):
        return ValueContext.FIELD

    return None


def _is_schema_name_value(
    token: ClassifiedToken, prev_token: RecognizedToken
) -> bool:
    """Check if token is a schema name value (quoted token after schema/action word)."""
    return (
        bool(token.was_quoted)
        and bool(prev_token.is_word)
        and bool(prev_token.is_schema_word or prev_token.is_action_word)
    )


def _is_field_value(prev_token: RecognizedToken) -> bool:
    """Check if previous token indicates current token should be a field value."""
    return prev_token.token_class == TokenClass.OPERATOR
