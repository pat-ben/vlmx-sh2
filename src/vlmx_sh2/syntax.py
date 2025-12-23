# File: D:\Code\vlmx-sh2\src\vlmx_sh2\commands\composition.py

"""
System-level composition rules for VLMX command syntax.

These rules automatically determine the order and structure of commands
based on keyword types, so individual commands don't need to specify order.

COMPOSITION RULES:
1. All word types are optional
2. Command cannot be empty (at least 1 word required)
3. Order: ACTION → MODIFIER → ENTITY → ATTRIBUTES (any order)
4. Composition is automatic based on keyword types

VALUE TYPES:
- ENTITY values: Always strings (entity names like "ACME-SA")
- ATTRIBUTE values: taken from Entity Models. Can be any Python type (str, int, float, date, bool, etc.)
"""

from typing import List, Optional
from vlmx_sh2.enums import WordType


# ==================== WORD ORDER ====================

class WordOrder:
    """
    Defines the automatic ordering of word types in commands.
    Lower numbers come first in the command syntax.
    
    Example: "create holding company ACME-SA --entity=SA --currency=EUR"
             ^^^^^^ ^^^^^^^ ^^^^^^^ ^^^^^^^ ^^^^^^^^^^^ ^^^^^^^^^^^^^^
             ACTION MODIFIER ENTITY  VALUE   ATTRIBUTE   ATTRIBUTE
               1       2       3       3         4           4
    """
    ACTION = 1      # e.g., create, show, delete, update
    MODIFIER = 2    # e.g., holding, operating
    ENTITY = 3      # e.g., company, milestone, revenue
    ATTRIBUTE = 4   # e.g., currency, entity, name, amount (no fixed order within attributes)
    
    @classmethod
    def get_order(cls, word_type: WordType) -> int:
        """
        Get the order priority for a word type.
        
        Args:
            word_type: The WordType enum value
            
        Returns:
            Integer representing order priority (lower = earlier in command)
        """
        mapping = {
            WordType.ACTION: cls.ACTION,
            WordType.MODIFIER: cls.MODIFIER,
            WordType.ENTITY: cls.ENTITY,
            WordType.ATTRIBUTE: cls.ATTRIBUTE,
        }
        return mapping.get(word_type, 999)  # Unknown types go last


# ==================== SYNTAX VALIDATION ====================

class SyntaxRules:
    """
    Validates and enforces command syntax rules.
    Ensures commands follow the correct word ordering.
    """
    
    @staticmethod
    def validate_command_structure(words: List) -> tuple[bool, str]:
        """
        Validate that a command follows composition rules.
        
        Rule 1: All word types are optional
        Rule 2: Command cannot be empty
        Rule 3: Order must be ACTION → MODIFIER → ENTITY → ATTRIBUTES
        
        Args:
            words: List of word objects with 'word_type' attribute
            
        Returns:
            (is_valid, error_message)
            
        Examples:
            >>> # Valid: create company ACME-SA
            >>> words = [action_word, entity_word, value]
            >>> validate_command_structure(words)
            (True, "")
            
            >>> # Invalid: company create ACME-SA (wrong order)
            >>> words = [entity_word, action_word, value]
            >>> validate_command_structure(words)
            (False, "Invalid word order...")
        """
        # Rule 2: Command cannot be empty
        if not words:
            return False, "Command cannot be empty (at least 1 word required)"
        
        # Rule 3: Check word type ordering: ACTION → MODIFIER → ENTITY → ATTRIBUTES
        last_order = 0
        
        for i, word in enumerate(words):
            # Get the order priority for this word type
            current_order = WordOrder.get_order(word.word_type)
            
            # Handle unknown word types
            if current_order == 999:
                return False, f"Unknown word type: {word.word_type}"
            
            # ATTRIBUTES can be in any order among themselves
            # So we skip strict order checking for attributes
            if word.word_type == WordType.ATTRIBUTE:
                # Attributes must come after ACTION, MODIFIER, ENTITY
                if last_order > 0 and last_order < WordOrder.ATTRIBUTE:
                    continue  # This is fine, attributes can follow anything earlier
                elif last_order == 0:
                    # Attribute cannot be first unless it's the only word type
                    has_non_attributes = any(
                        w.word_type != WordType.ATTRIBUTE 
                        for w in words
                    )
                    if has_non_attributes:
                        return False, (
                            f"Attribute '{word.id}' cannot come before ACTION, MODIFIER, or ENTITY words. "
                            f"Expected order: ACTION → MODIFIER → ENTITY → ATTRIBUTES"
                        )
                continue
            
            # For non-attributes, check that order is not decreasing
            if current_order < last_order:
                return False, (
                    f"Invalid word order: '{word.id}' ({word.word_type.value}) "
                    f"cannot come after a word of higher precedence. "
                    f"Expected order: ACTION → MODIFIER → ENTITY → ATTRIBUTES"
                )
            
            last_order = current_order
        
        return True, ""
    
    @staticmethod
    def sort_words_by_type(words: List) -> List:
        """
        Automatically sort words according to composition rules.
        
        Order: ACTION → MODIFIER → ENTITY → ATTRIBUTES (attributes maintain original order)
        
        Args:
            words: List of word objects with 'word_type' attribute
            
        Returns:
            Sorted list of words
            
        Examples:
            >>> # Input: [entity, action, attribute, modifier]
            >>> # Output: [action, modifier, entity, attribute]
            >>> sort_words_by_type(words)
            [action_w, modifier_w, entity_w, attribute_w]
        """
        # Separate words by type
        actions = [w for w in words if w.word_type == WordType.ACTION]
        modifiers = [w for w in words if w.word_type == WordType.MODIFIER]
        entities = [w for w in words if w.word_type == WordType.ENTITY]
        attributes = [w for w in words if w.word_type == WordType.ATTRIBUTE]
        
        # Combine in correct order (attributes maintain their original relative order)
        return actions + modifiers + entities + attributes
    
    @staticmethod
    def get_expected_next_word_types(current_words: List) -> List[WordType]:
        """
        Get the list of word types that can come next in the command.
        
        Args:
            current_words: List of words already in the command
            
        Returns:
            List of WordType values that are valid next
            
        Examples:
            >>> # After "create", can have MODIFIER, ENTITY, or ATTRIBUTE
            >>> get_expected_next_word_types([action_word])
            [WordType.MODIFIER, WordType.ENTITY, WordType.ATTRIBUTE]
            
            >>> # After "create holding", can have ENTITY or ATTRIBUTE
            >>> get_expected_next_word_types([action_word, modifier_word])
            [WordType.ENTITY, WordType.ATTRIBUTE]
        """
        if not current_words:
            # Empty command can start with any word type
            return [WordType.ACTION, WordType.MODIFIER, WordType.ENTITY, WordType.ATTRIBUTE]
        
        # Get the highest order word type we've seen so far (excluding attributes)
        max_order = 0
        for word in current_words:
            if word.word_type != WordType.ATTRIBUTE:
                order = WordOrder.get_order(word.word_type)
                max_order = max(max_order, order)
        
        # Can always add attributes
        valid_types = [WordType.ATTRIBUTE]
        
        # Can add any word type that comes after our current position
        if max_order < WordOrder.ACTION:
            valid_types.append(WordType.ACTION)
        if max_order < WordOrder.MODIFIER:
            valid_types.append(WordType.MODIFIER)
        if max_order < WordOrder.ENTITY:
            valid_types.append(WordType.ENTITY)
        
        return valid_types
    
    @staticmethod
    def get_word_order_hint() -> str:
        """
        Get a human-readable hint about word ordering.
        Used for help messages and error feedback.
        
        Returns:
            String explaining the keyword order rules
        """
        return (
            "Command Composition Rules:\n"
            "  1. All word types are optional\n"
            "  2. Command cannot be empty (at least 1 word required)\n"
            "  3. Order: ACTION → MODIFIER → ENTITY → ATTRIBUTES (any order)\n"
            "\n"
            "Examples:\n"
            "  create company ACME-SA --entity=SA --currency=EUR\n"
            "  ^^^^^^ ^^^^^^^ ^^^^^^^ ^^^^^^^^^^^ ^^^^^^^^^^^^^^\n"
            "  ACTION ENTITY  VALUE   ATTRIBUTE   ATTRIBUTE\n"
            "\n"
            "  create holding company HoldCo --entity=SA\n"
            "  ^^^^^^ ^^^^^^^ ^^^^^^^ ^^^^^^^ ^^^^^^^^^^^^^\n"
            "  ACTION MODIFIER ENTITY VALUE   ATTRIBUTE\n"
            "\n"
            "  add revenue 1250000 --year=2025 --period=Q1\n"
            "  ^^^ ^^^^^^^ ^^^^^^^ ^^^^^^^^^^^ ^^^^^^^^^^^^\n"
            "  ACTION ENTITY VALUE ATTRIBUTE   ATTRIBUTE\n"
        )


# ==================== CONVENIENCE FUNCTIONS ====================

def is_valid_command(words: List) -> bool:
    """
    Quick check if a command structure is valid.
    
    Args:
        words: List of word objects with 'word_type' attribute
        
    Returns:
        True if valid, False otherwise
        
    Example:
        >>> is_valid_command([action_w, entity_w])
        True
        >>> is_valid_command([entity_w, action_w])
        False
    """
    is_valid, _ = SyntaxRules.validate_command_structure(words)
    return is_valid


def get_composition_error(words: List) -> Optional[str]:
    """
    Get the composition error message for invalid commands.
    
    Args:
        words: List of word objects with 'word_type' attribute
        
    Returns:
        Error message if invalid, None if valid
        
    Example:
        >>> get_composition_error([entity_w, action_w])
        "Invalid word order: 'create' (ACTION) cannot come after..."
        >>> get_composition_error([action_w, entity_w])
        None
    """
    is_valid, error_msg = SyntaxRules.validate_command_structure(words)
    return error_msg if not is_valid else None


def sort_words(words: List) -> List:
    """
    Sort words according to composition rules.
    Convenience wrapper for SyntaxRules.sort_words_by_type().
    
    Args:
        words: List of word objects to sort
        
    Returns:
        Sorted list of words
        
    Example:
        >>> sorted_ws = sort_words([entity_w, action_w, attr_w])
        >>> # Returns: [action_w, entity_w, attr_w]
    """
    return SyntaxRules.sort_words_by_type(words)


def get_next_valid_types(current_words: List) -> List[WordType]:
    """
    Get valid word types that can come next.
    Convenience wrapper for SyntaxRules.get_expected_next_word_types().
    
    Args:
        current_words: Words already in the command
        
    Returns:
        List of valid next word types
        
    Example:
        >>> get_next_valid_types([action_w])
        [WordType.MODIFIER, WordType.ENTITY, WordType.ATTRIBUTE]
    """
    return SyntaxRules.get_expected_next_word_types(current_words)