# File: D:\Code\vlmx-sh2\src\vlmx_sh2\commands\composition.py

"""
System-level composition rules for VLMX command syntax.

These rules automatically determine the order and structure of commands
based on keyword types, so individual commands don't need to specify order.

COMPOSITION RULES:
1. All keyword types are optional
2. Command cannot be empty (at least 1 keyword required)
3. Order: ACTION → MODIFIER → ENTITY → ATTRIBUTES (any order)
4. Composition is automatic based on keyword types

VALUE TYPES:
- ENTITY values: Always strings (entity names like "ACME-SA")
- ATTRIBUTE values: Can be any Python type (str, int, float, date, bool, etc.)
"""

from typing import Any, List, Optional, Type
from vlmx_sh2.enums import KeywordType


# ==================== KEYWORD TYPE ORDER ====================

class KeywordTypeOrder:
    """
    Defines the automatic ordering of keyword types in commands.
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
    def get_order(cls, keyword_type: KeywordType) -> int:
        """
        Get the order priority for a keyword type.
        
        Args:
            keyword_type: The KeywordType enum value
            
        Returns:
            Integer representing order priority (lower = earlier in command)
        """
        mapping = {
            KeywordType.ACTION: cls.ACTION,
            KeywordType.MODIFIER: cls.MODIFIER,
            KeywordType.ENTITY: cls.ENTITY,
            KeywordType.ATTRIBUTE: cls.ATTRIBUTE,
        }
        return mapping.get(keyword_type, 999)  # Unknown types go last


# ==================== COMPOSITION VALIDATION ====================

class CompositionRules:
    """
    Validates and enforces command composition rules.
    Ensures commands follow the correct keyword ordering.
    """
    
    @staticmethod
    def validate_command_structure(keywords: List) -> tuple[bool, str]:
        """
        Validate that a command follows composition rules.
        
        Rule 1: All keyword types are optional
        Rule 2: Command cannot be empty
        Rule 3: Order must be ACTION → MODIFIER → ENTITY → ATTRIBUTES
        
        Args:
            keywords: List of keyword objects with 'keyword_type' attribute
            
        Returns:
            (is_valid, error_message)
            
        Examples:
            >>> # Valid: create company ACME-SA
            >>> keywords = [action_keyword, entity_keyword, value]
            >>> validate_command_structure(keywords)
            (True, "")
            
            >>> # Invalid: company create ACME-SA (wrong order)
            >>> keywords = [entity_keyword, action_keyword, value]
            >>> validate_command_structure(keywords)
            (False, "Invalid keyword order...")
        """
        # Rule 2: Command cannot be empty
        if not keywords:
            return False, "Command cannot be empty (at least 1 keyword required)"
        
        # Rule 3: Check keyword type ordering: ACTION → MODIFIER → ENTITY → ATTRIBUTES
        last_order = 0
        
        for i, keyword in enumerate(keywords):
            # Get the order priority for this keyword type
            current_order = KeywordTypeOrder.get_order(keyword.keyword_type)
            
            # Handle unknown keyword types
            if current_order == 999:
                return False, f"Unknown keyword type: {keyword.keyword_type}"
            
            # ATTRIBUTES can be in any order among themselves
            # So we skip strict order checking for attributes
            if keyword.keyword_type == KeywordType.ATTRIBUTE:
                # Attributes must come after ACTION, MODIFIER, ENTITY
                if last_order > 0 and last_order < KeywordTypeOrder.ATTRIBUTE:
                    continue  # This is fine, attributes can follow anything earlier
                elif last_order == 0:
                    # Attribute cannot be first unless it's the only keyword type
                    has_non_attributes = any(
                        k.keyword_type != KeywordType.ATTRIBUTE 
                        for k in keywords
                    )
                    if has_non_attributes:
                        return False, (
                            f"Attribute '{keyword.id}' cannot come before ACTION, MODIFIER, or ENTITY keywords. "
                            f"Expected order: ACTION → MODIFIER → ENTITY → ATTRIBUTES"
                        )
                continue
            
            # For non-attributes, check that order is not decreasing
            if current_order < last_order:
                return False, (
                    f"Invalid keyword order: '{keyword.id}' ({keyword.keyword_type.value}) "
                    f"cannot come after a keyword of higher precedence. "
                    f"Expected order: ACTION → MODIFIER → ENTITY → ATTRIBUTES"
                )
            
            last_order = current_order
        
        return True, ""
    
    @staticmethod
    def sort_keywords_by_type(keywords: List) -> List:
        """
        Automatically sort keywords according to composition rules.
        
        Order: ACTION → MODIFIER → ENTITY → ATTRIBUTES (attributes maintain original order)
        
        Args:
            keywords: List of keyword objects with 'keyword_type' attribute
            
        Returns:
            Sorted list of keywords
            
        Examples:
            >>> # Input: [entity, action, attribute, modifier]
            >>> # Output: [action, modifier, entity, attribute]
            >>> sort_keywords_by_type(keywords)
            [action_kw, modifier_kw, entity_kw, attribute_kw]
        """
        # Separate keywords by type
        actions = [k for k in keywords if k.keyword_type == KeywordType.ACTION]
        modifiers = [k for k in keywords if k.keyword_type == KeywordType.MODIFIER]
        entities = [k for k in keywords if k.keyword_type == KeywordType.ENTITY]
        attributes = [k for k in keywords if k.keyword_type == KeywordType.ATTRIBUTE]
        
        # Combine in correct order (attributes maintain their original relative order)
        return actions + modifiers + entities + attributes
    
    @staticmethod
    def get_expected_next_keyword_types(current_keywords: List) -> List[KeywordType]:
        """
        Get the list of keyword types that can come next in the command.
        
        Args:
            current_keywords: List of keywords already in the command
            
        Returns:
            List of KeywordType values that are valid next
            
        Examples:
            >>> # After "create", can have MODIFIER, ENTITY, or ATTRIBUTE
            >>> get_expected_next_keyword_types([action_keyword])
            [KeywordType.MODIFIER, KeywordType.ENTITY, KeywordType.ATTRIBUTE]
            
            >>> # After "create holding", can have ENTITY or ATTRIBUTE
            >>> get_expected_next_keyword_types([action_keyword, modifier_keyword])
            [KeywordType.ENTITY, KeywordType.ATTRIBUTE]
        """
        if not current_keywords:
            # Empty command can start with any keyword type
            return [KeywordType.ACTION, KeywordType.MODIFIER, KeywordType.ENTITY, KeywordType.ATTRIBUTE]
        
        # Get the highest order keyword type we've seen so far (excluding attributes)
        max_order = 0
        for keyword in current_keywords:
            if keyword.keyword_type != KeywordType.ATTRIBUTE:
                order = KeywordTypeOrder.get_order(keyword.keyword_type)
                max_order = max(max_order, order)
        
        # Can always add attributes
        valid_types = [KeywordType.ATTRIBUTE]
        
        # Can add any keyword type that comes after our current position
        if max_order < KeywordTypeOrder.ACTION:
            valid_types.append(KeywordType.ACTION)
        if max_order < KeywordTypeOrder.MODIFIER:
            valid_types.append(KeywordType.MODIFIER)
        if max_order < KeywordTypeOrder.ENTITY:
            valid_types.append(KeywordType.ENTITY)
        
        return valid_types
    
    @staticmethod
    def get_keyword_order_hint() -> str:
        """
        Get a human-readable hint about keyword ordering.
        Used for help messages and error feedback.
        
        Returns:
            String explaining the keyword order rules
        """
        return (
            "Command Composition Rules:\n"
            "  1. All keyword types are optional\n"
            "  2. Command cannot be empty (at least 1 keyword required)\n"
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

def is_valid_command(keywords: List) -> bool:
    """
    Quick check if a command structure is valid.
    
    Args:
        keywords: List of keyword objects with 'keyword_type' attribute
        
    Returns:
        True if valid, False otherwise
        
    Example:
        >>> is_valid_command([action_kw, entity_kw])
        True
        >>> is_valid_command([entity_kw, action_kw])
        False
    """
    is_valid, _ = CompositionRules.validate_command_structure(keywords)
    return is_valid


def get_composition_error(keywords: List) -> Optional[str]:
    """
    Get the composition error message for invalid commands.
    
    Args:
        keywords: List of keyword objects with 'keyword_type' attribute
        
    Returns:
        Error message if invalid, None if valid
        
    Example:
        >>> get_composition_error([entity_kw, action_kw])
        "Invalid keyword order: 'create' (ACTION) cannot come after..."
        >>> get_composition_error([action_kw, entity_kw])
        None
    """
    is_valid, error_msg = CompositionRules.validate_command_structure(keywords)
    return error_msg if not is_valid else None


def sort_keywords(keywords: List) -> List:
    """
    Sort keywords according to composition rules.
    Convenience wrapper for CompositionRules.sort_keywords_by_type().
    
    Args:
        keywords: List of keyword objects to sort
        
    Returns:
        Sorted list of keywords
        
    Example:
        >>> sorted_kws = sort_keywords([entity_kw, action_kw, attr_kw])
        >>> # Returns: [action_kw, entity_kw, attr_kw]
    """
    return CompositionRules.sort_keywords_by_type(keywords)


def get_next_valid_types(current_keywords: List) -> List[KeywordType]:
    """
    Get valid keyword types that can come next.
    Convenience wrapper for CompositionRules.get_expected_next_keyword_types().
    
    Args:
        current_keywords: Keywords already in the command
        
    Returns:
        List of valid next keyword types
        
    Example:
        >>> get_next_valid_types([action_kw])
        [KeywordType.MODIFIER, KeywordType.ENTITY, KeywordType.ATTRIBUTE]
    """
    return CompositionRules.get_expected_next_keyword_types(current_keywords)