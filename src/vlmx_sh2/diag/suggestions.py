
"""
Centralized suggestion engine for diagnostics.

Provides intelligent suggestions for fixing validation issues,
including token-level and command-level suggestions.
"""

from typing import List
from ..core.models.parser import ParseResult, TokenType


class SuggestionEngine:
    """
    Centralized suggestion generation for parser components.
    
    Handles both token-level suggestions (for unrecognized words) and
    command-level suggestions (for incomplete or invalid commands).
    """
    
    def get_token_suggestions(self, token_text: str) -> List[str]:
        """
        Get suggestions for unrecognized tokens.
        
        Args:
            token_text: The unrecognized token text
            
        Returns:
            List of up to 3 suggestions
        """
        suggestions = []
        
        # Fast suggestion logic based on first character
        if token_text:
            first_char = token_text[0].lower()
            
            # Common action suggestions by first letter
            action_suggestions = {
                'c': ['create', 'cd'],
                'a': ['add'],
                'u': ['update'],
                's': ['show'],
                'd': ['delete'],
                'l': ['list'],
                'f': ['fill']
            }
            if first_char in action_suggestions:
                suggestions.extend(action_suggestions[first_char])
            
            # Common entity suggestions by length and pattern
            entity_suggestions = ['company', 'brand', 'metadata', 'fund']
            for entity in entity_suggestions:
                if len(token_text) >= 2 and entity.startswith(token_text[:2].lower()):
                    suggestions.append(entity)
        
        return suggestions[:3]  # Limit to top 3
    
    def get_command_suggestions(self, result: ParseResult) -> List[str]:
        """
        Generate helpful suggestions based on parse result and command analysis.
        
        Args:
            result: The parse result to analyze
            
        Returns:
            List of helpful command-level suggestions
        """
        suggestions = []
        
        # Check for token-level suggestions
        for token in result.tokens:
            if token.token_type == TokenType.UNKNOWN and token.suggestions:
                suggestions.append(f"Did you mean '{token.suggestions[0]}' instead of '{token.text}'?")
        
        # Check command-level issues
        if not result.is_valid:
            # No action word found
            action_tokens = [t for t in result.tokens if t.is_action_word]
            if not action_tokens:
                suggestions.append("Consider adding an action word (e.g., 'create', 'add', 'update', 'show', 'delete')")
            
            # Action found but no target (when required for non-standalone actions)
            elif result.command and result.command.action and not result.command.action.standalone:
                if not result.command.target:
                    suggestions.append("Consider adding a target word (e.g., 'company', 'brand', 'metadata')")
        
        # Suggest field values if command looks complete but minimal
        if result.is_valid and result.command:
            if result.command.action and not result.command.field_values:
                action_id = result.command.action.id
                if action_id in ['create', 'add']:
                    suggestions.append("Consider adding field values like entity=SA currency=EUR")
                elif action_id in ['update']:
                    suggestions.append("Consider adding field values like name=value or key=value")
        
        return suggestions